import io
import logging
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api.middleware import RouterLoggingMiddleware
from api.logger import configure_logger
from api.utils import (
    UploadSizeLimitError,
    UploadValidationError,
    stage_multipart_uploads,
    validate_staged_workspace,
)
from api.tempdir import get_writable_temp_dir
from lib.transform.collections import build_collections, searching_and_assigning
from lib.transform.json_collections import build_collections_from_json
from lib.transform.outputs import save_objects_to_json
from api.model import HealthResponse


configure_logger()
app = FastAPI(title="HSDS Transformer API", version="0.1.0")
APP_START_MONOTONIC = time.monotonic()
MAX_MULTIPART_UPLOAD_BYTES = 50 * 1024 * 1024

origins = [
"http://localhost:5173",
"https://hsds.sitblueprint.com"
]

# Adding CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Specify allowed origins
    allow_credentials=True, # Allow cookies and credentials
    allow_methods=["*"], # Allow all HTTP methods
    allow_headers=["*"], # Allow all headers
)

app.add_middleware(RouterLoggingMiddleware, logger=logging.getLogger("hsds.api"))

@app.get(
    "/health",
    summary="Service health check",
    description="Lightweight liveness endpoint for load balancers and orchestrators",
    response_model=HealthResponse,
)
async def health(response: Response) -> HealthResponse:
    response.headers["Cache-Control"] = "no-store"
    return HealthResponse(
        status="ok",
        service=app.title,
        version=app.version,
        timestamp_utc=datetime.now(timezone.utc),
        uptime_seconds=round(time.monotonic() - APP_START_MONOTONIC, 3),
    )


@app.post(
    "/transform",
    status_code=201,
    summary="Transform custom dataset into HSDS format",
    description=(
        "Accepts a zip file containing input data and mapping files. "
        "Use input_format to specify whether the input is csv (default) or json. "
        "Unzips, runs the transformer (build_collections → searching_and_assigning), and returns a zip of the transformed JSON files"
    ),
    response_class=StreamingResponse,
)
async def transform(
    zip_file: UploadFile = File(
        ..., description="Zip file containing input data and mapping files"
    ),
    input_format: str = Form(
        default="csv", description="Input data format: 'csv' or 'json'"
    ),
) -> StreamingResponse:
    # Validate input_format
    input_format = input_format.lower()
    if input_format not in ("csv", "json"):
        raise HTTPException(
            status_code=422,
            detail="input_format must be 'csv' or 'json'",
        )
    # Input validation: require a non-empty .zip file
    if not zip_file.filename or not zip_file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=422, detail="Must provide a zip file")
    content = await zip_file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Zip file is empty")
    try:
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            if not zf.namelist():
                raise HTTPException(
                    status_code=422, detail="Zip file contains no files"
                )
    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail="Invalid zip file")

    try:
        temp_root = get_writable_temp_dir()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Unzip into a temp directory
    with tempfile.TemporaryDirectory(dir=temp_root, prefix="hsds-input-") as input_dir:
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            zf.extractall(input_dir)

        # Handle case where zip creates a single top-level folder
        extracted_items = list(Path(input_dir).iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            input_dir = str(extracted_items[0])

        if not any(Path(input_dir).iterdir()):
            raise HTTPException(
                status_code=422, detail="Zip file extracts to an empty folder"
            )

        # Run the transformer: build collections, then link parents/children
        try:
            if input_format == "json":
                results = build_collections_from_json(input_dir)
            else:
                results = build_collections(input_dir)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        results = searching_and_assigning(results)

        # Write each object to JSON files in another temp dir, then zip and return
        with tempfile.TemporaryDirectory(dir=temp_root, prefix="hsds-output-") as output_dir:
            save_objects_to_json(results, output_dir)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out_zip:
                for p in Path(output_dir).rglob("*"):
                    if p.is_file():
                        arcname = p.relative_to(output_dir)
                        out_zip.write(p, arcname)
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=transformed.zip"},
            )


@app.post(
    "/transform/stream",
    status_code=201,
    summary="Stage streamed JSON uploads for transform",
    description=(
        "Accepts multipart uploads with repeated files parts, stages them in a "
        "request-scoped workspace, validates upload constraints, and hands off "
        "the staged input directory to the JSON collection build path placeholder."
    ),
    response_class=JSONResponse,
)
async def transform_stream(
    files: list[UploadFile] = File(
        ..., description="Repeated files parts containing source JSON and *_mapping.json"
    )
) -> JSONResponse:
    workspace_dir = Path(tempfile.mkdtemp(prefix="hsds-stream-"))
    input_dir = workspace_dir / "input"

    try:
        summary = await stage_multipart_uploads(
            files=files,
            input_dir=input_dir,
            max_upload_bytes=MAX_MULTIPART_UPLOAD_BYTES,
        )
        validate_staged_workspace(summary)

        # TODO(issue #117): Call the JSON collection build path with str(input_dir).

        return JSONResponse(
            status_code=201,
            content={
                "detail": "Upload staged successfully.",
                "staged": {
                    "total_files": summary.total_files,
                    "source_files": summary.source_file_count,
                    "mapping_files": summary.mapping_file_count,
                    "total_bytes": summary.total_bytes,
                },
            },
        )
    except UploadSizeLimitError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except UploadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

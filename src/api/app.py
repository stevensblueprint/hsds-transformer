import io
import logging
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError

from api.middleware import RouterLoggingMiddleware
from api.logger import configure_logger
from lib.collections import build_collections, searching_and_assigning
from lib.outputs import save_objects_to_json


configure_logger()
app = FastAPI(title="HSDS Transformer API", version="0.1.0")
app.add_middleware(RouterLoggingMiddleware, logger=logging.getLogger("hsds.api"))


@app.post(
    "/transform",
    status_code=201,
    summary="Transform custom dataset into HSDS format",
    description=(
        "Accepts a zip file containing input CSVs and *_mapping.csv files "
        "Unzips, runs the transformer (build_collections → searching_and_assigning), and returns a zip of the transformed JSON files"
    ),
    response_class=StreamingResponse,
)
async def transform(zip_file: UploadFile = File(..., description="Zip file containing input and mapping CSVs")) -> StreamingResponse:
    # Input validation: require a non-empty .zip file
    if not zip_file.filename or not zip_file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=422, detail="Must provide a zip file")
    content = await zip_file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Zip file is empty")
    try:
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            if not zf.namelist():
                raise HTTPException(status_code=422, detail="Zip file contains no files")
    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail="Invalid zip file")

    # Unzip into a temp directory
    with tempfile.TemporaryDirectory() as input_dir:
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            zf.extractall(input_dir)

        # Handle case where zip creates a single top-level folder
        extracted_items = list(Path(input_dir).iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            input_dir = str(extracted_items[0])
   
        if not any(Path(input_dir).iterdir()):
            raise HTTPException(status_code=422, detail="Zip file extracts to an empty folder")

        # Run the transformer: build collections, then link parents/children
        try:
            results = build_collections(input_dir)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        results = searching_and_assigning(results)

        # Write each object to JSON files in another temp dir, then zip and return 
        with tempfile.TemporaryDirectory() as output_dir:
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

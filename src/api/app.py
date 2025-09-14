from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import List
import logging
from api.middleware import RouterLoggingMiddleware
from api.logger import configure_logger
from lib.models import Organization


configure_logger()
app = FastAPI(title="HSDS Transformer API", version="0.1.0")
app.add_middleware(RouterLoggingMiddleware, logger=logging.getLogger("hsds.api"))


@app.post(
    "/transform",
    status_code=201,
    summary="Transform custom dataset into HSDS format",
    response_model=List[Organization],
)
async def transform() -> List[Organization]:
    return [
        Organization(id="org-123", name="Acme Corp", description="A fictional company")
    ]


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

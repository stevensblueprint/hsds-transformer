import logging
import time
import json
from typing import Tuple, Callable, MutableMapping, Any, Dict
from uuid import uuid4
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


def router_logging_middleware_factory(
    app: ASGIApp, *, logger: logging.Logger
) -> ASGIApp:
    return RouterLoggingMiddleware(app, logger=logger)


class RouterLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, logger: logging.Logger) -> None:
        self._logger = logger
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id: str = str(uuid4())
        logging_dict: Dict[str, Any] = {
            "X-API-REQUEST-ID": request_id,
        }

        response, response_dict = await self._log_response(
            call_next, request, request_id
        )
        request_dict = await self._log_request(request)

        logging_dict["request"] = request_dict
        logging_dict["response"] = response_dict
        self._logger.info(logging_dict)
        return response

    async def _log_request(self, request: Request) -> Dict[str, Any]:
        path = request.url.path
        if request.query_params:
            path += f"?{request.query_params}"

        request_logging: Dict[str, Any] = {
            "method": request.method,
            "path": path,
            "ip": request.client.host if request.client else "unknown",
            "body": None,
        }
        # Do not read the request body here; it would consume the stream and break
        # file uploads and StreamingResponse (e.g. zip download).
        return request_logging

    async def _log_response(
    self, call_next: Callable, request: Request, request_id: str
    ) -> Tuple[Response, MutableMapping[str, Any]]:
        start_time = time.perf_counter()
        response = await self._execute_request(call_next, request, request_id)
        finish_time = time.perf_counter()
        execution_time = (finish_time - start_time) * 1000

        # tries to parse content length
        content_type = response.headers.get("content-type")
        content_length_header = response.headers.get("content-length")

        content_length = None
        if content_length_header is not None:
            try:
                content_length = int(content_length_header)
            except ValueError:
                content_length = None # header exists but is weird, ignore

        # base metadata that we log
        response_logging: Dict[str, Any] = {
            "status": "succeeded" if response.status_code < 400 else "failed",
            "status_code": response.status_code,
            "duration_ms": round(execution_time, 2),
            "content_type": content_type,
            "content_length": content_length,
            "request_id": request_id,
        }

        # normalize content type
        lowered_content_type = content_type.lower() if content_type else ""
        
        # detects binary streaming response (we will not consume these)
        is_binary_response = (
            "application/zip" in lowered_content_type
            or "application/octet-stream" in lowered_content_type
            or "application/pdf" in lowered_content_type
        )

        # we dont read as it will consume
        if is_binary_response:
            return response, response_logging

        # for normal (non binrary) responses, we can safely log
        if hasattr(response, "body") and response.body is not None:
            try:
                parsed = json.loads(response.body.decode()) # trys to parse JSON
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                parsed = response.body.decode(errors="ignore") # failback to decode what we can

            response_logging["body"] = parsed

        return response, response_logging

    async def _execute_request(
        self, call_next: Callable, request: Request, request_id: str
    ) -> Response:
        try:
            response: Response = await call_next(request)
            response.headers["X-API-REQUEST-ID"] = request_id
            return response
        except Exception as e:
            self._logger.exception(
                {
                    "path": request.url.path,
                    "method": request.method,
                    "reason": str(e),
                }
            )
            raise e

import logging
import time
import json
from typing import Tuple, Callable, MutableMapping, Any, Dict
from uuid import uuid4
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message, ASGIApp
from .utils import AsyncIteratorWrapper


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

        response_logging: Dict[str, Any] = {
            "status": "succeeded" if response.status_code < 400 else "failed",
            "status_code": response.status_code,
            "duration_ms": round(execution_time, 2),
        }

        body_chunks = [section async for section in response.__dict__["body_iterator"]]
        response.__setattr__("body_iterator", AsyncIteratorWrapper(body_chunks))

        try:
            parsed = json.loads(body_chunks[0].decode())
        except (IndexError, json.JSONDecodeError, UnicodeDecodeError):
            parsed = (
                b"".join(body_chunks).decode(errors="ignore") if body_chunks else ""
            )

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

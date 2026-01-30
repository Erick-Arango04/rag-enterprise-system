import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.utils.logging import get_logger, log_request_start, log_request_success

logger = get_logger(__name__)


class HTTPLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic HTTP request/response logging."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        log_request_start(
            logger,
            event="http_request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
        )

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        log_request_success(
            logger,
            event="http_request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            processing_time_ms=round(duration_ms, 2),
        )

        return response

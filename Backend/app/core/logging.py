"""
app/core/logging.py
Structured JSON logger — every request logs timestamp, method, path,
status_code, duration_ms, and optional claim_id / user_id.
"""
import json
import logging
import sys
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    """Formats each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra fields passed via logger.info("msg", extra={...})
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "message", "module", "msecs", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName",
            ):
                log_entry[key] = value
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Plain-text formatter (used when LOG_FORMAT=text)
# ---------------------------------------------------------------------------
TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _configure_root_logger() -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(TEXT_FORMAT))

    root.handlers.clear()
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Get a named logger — use in every module."""
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request/response with timing and context."""

    _logger = get_logger("api.request")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response: Response | None = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            self._logger.error(
                "Unhandled exception",
                exc_info=exc,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log_extra: dict = {
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "query_params": str(request.query_params) or None,
            }
            # Pull claim_id from path if present (e.g. /api/v1/claims/{claim_id})
            path_params = getattr(request, "path_params", {})
            if "claim_id" in path_params:
                log_extra["claim_id"] = path_params["claim_id"]
            if "user_id" in path_params:
                log_extra["user_id"] = path_params["user_id"]

            level = logging.WARNING if status_code >= 400 else logging.INFO
            self._logger.log(
                level,
                f"{request.method} {request.url.path} → {status_code}",
                extra=log_extra,
            )

        return response

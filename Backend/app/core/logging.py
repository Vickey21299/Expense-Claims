"""
app/core/logging.py
Structured logging factory — all modules should use `get_logger(__name__)`.
"""
import logging
import sys


_STANDARD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName", "message",
}


class StructuredFormatter(logging.Formatter):
    """Formatter that automatically appends any extra attributes passed in logging calls."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra_items = {
            k: v for k, v in record.__dict__.items()
            if k not in _STANDARD_ATTRS and not k.startswith("_")
        }
        if extra_items:
            extra_str = " ".join(f"{k}={v!r}" for k, v in extra_items.items())
            base = f"{base} | {extra_str}"
        return base


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with consistent format and structured extra field printing."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            StructuredFormatter(
                "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.propagate = False
    return logger


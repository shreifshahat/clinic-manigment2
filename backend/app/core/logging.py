"""Structured logging with redaction.

Rules:
* One JSON object per line (easy to ship to a log collector).
* Patient names, phone numbers and **medical content are never logged**.
  Identifiers (uuids) and counts are enough to investigate a problem.
* Every log line carries the ``request_id`` so support tickets can be traced.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "diagnosis",
    "treatment",
    "notes",
    "chief_complaint",
    "full_name",
    "name",
    "phone",
    "national_id",
    "secret",
    "service_role_key",
    "api_key",
}

_RESERVED = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


def redact(value: Any, _depth: int = 0) -> Any:
    """Recursively replace sensitive values with a fixed marker."""
    if _depth > 6:
        return "<truncated>"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in _SENSITIVE_KEYS:
                out[key] = "<redacted>"
            else:
                out[key] = redact(item, _depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(item, _depth + 1) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = redact(value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # uvicorn's own access log would duplicate the app log; keep it at WARNING.
    for name in ("uvicorn.access",):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

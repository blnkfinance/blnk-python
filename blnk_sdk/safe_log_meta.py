"""Log-metadata redaction: scrubs API keys and other secrets before values
reach a logger."""

from __future__ import annotations

import re
from typing import Any, Dict, List

SENSITIVE_KEYS = frozenset(
    {
        "apikey",
        "api_key",
        "x-blnk-key",
        "authorization",
        "cookie",
        "password",
        "secret",
        "token",
    }
)

_X_BLNK_KEY_RE = re.compile(r"X-Blnk-Key:\s*[^\s,;]+", re.IGNORECASE)
_BEARER_RE = re.compile(r"Bearer\s+[^\s,;]+", re.IGNORECASE)
_API_KEY_RE = re.compile(
    r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)[^\"'\s,}]+", re.IGNORECASE
)


def redact_sensitive_string(value: str) -> str:
    value = _X_BLNK_KEY_RE.sub("X-Blnk-Key: [REDACTED]", value)
    value = _BEARER_RE.sub("Bearer [REDACTED]", value)
    value = _API_KEY_RE.sub(r"\g<1>[REDACTED]", value)
    return value


def redact_sensitive_log_value(value: Any) -> Any:
    if value is None:
        return value
    if isinstance(value, str):
        return redact_sensitive_string(value)
    if isinstance(value, BaseException):
        # Exceptions are reduced to {name, message}; tracebacks and any
        # extra attributes are dropped.
        return {
            "name": type(value).__name__,
            "message": redact_sensitive_string(str(value)),
        }
    if isinstance(value, (list, tuple)):
        return [redact_sensitive_log_value(item) for item in value]
    if isinstance(value, dict):
        return redact_sensitive_log_meta(value)
    return value


def redact_sensitive_log_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a NEW dict, key order preserved; never mutates input."""
    redacted: Dict[str, Any] = {}
    for key, value in meta.items():
        lowered = key.lower() if isinstance(key, str) else key
        if lowered in SENSITIVE_KEYS:
            redacted[key] = "[REDACTED]"
            continue
        if lowered == "headers":
            redacted[key] = redact_sensitive_log_meta(value)
            continue
        redacted[key] = redact_sensitive_log_value(value)
    return redacted


def safe_log_meta(*meta: Any) -> List[Any]:
    return [redact_sensitive_log_value(item) for item in meta]

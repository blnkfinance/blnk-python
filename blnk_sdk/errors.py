"""Error model and SDK exception types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


class BlnkTimeoutError(Exception):
    """Raised by transports when a per-attempt timeout elapses.

    Transports MUST raise this (and only this) for request timeouts. The core
    client maps it to a synthetic 408 response and NEVER retries it, and
    ``is_retryable_transport_error`` excludes exactly this type.
    """


class BlnkServiceError(RuntimeError):
    """Raised by Blnk._get_service for unregistered service names.

    Message: ``Service {name} is not registered`` (no trailing period).
    """


class BlnkErrorCode:
    """Stable Core ``error_detail.code`` values called out for SDK 1.4.0 /
    Core 0.15.3. Compare ``response.error.code`` — do not branch on message
    text.

    See https://docs.blnkfinance.com/advanced/error-codes
    """

    TXN_INVALID_AMOUNT = "TXN_INVALID_AMOUNT"
    GEN_CONFLICT = "GEN_CONFLICT"
    # Request failed validation before processing. On Core 0.15.3 this
    # includes negative amount/precision and source equal to destination.
    TXN_VALIDATION_ERROR = "TXN_VALIDATION_ERROR"


@dataclass
class BlnkApiErrorDetail:
    """Structured API error attached to ApiResponse.error."""

    code: str
    message: str
    details: Any = None

    def to_dict(self) -> dict:
        out: dict = {"code": self.code, "message": self.message}
        # `details` is omitted entirely when not provided.
        if self.details is not None:
            out["details"] = self.details
        return out


def parse_blnk_api_error_body(body: Any) -> Optional[BlnkApiErrorDetail]:
    """Parse a structured error out of an error-response body.

    Checks run in this order:

    1. A body that is not a dict or list (strings, numbers, None) yields None;
       a null payload is rejected before any field checks.
    2. A truthy ``error_detail`` mapping with string ``code`` AND string
       ``message`` yields BlnkApiErrorDetail(code, message, details).
    3. A non-empty string ``error`` yields BlnkApiErrorDetail("UNKNOWN", error).
    4. Otherwise None.
    """
    if body is None or not isinstance(body, (dict, list)):
        return None
    if isinstance(body, list):
        # Lists are accepted by the type check above but carry no named
        # fields, so they can never produce a structured error.
        return None

    error_detail = body.get("error_detail")
    if error_detail and isinstance(error_detail, dict):
        code = error_detail.get("code")
        message = error_detail.get("message")
        if isinstance(code, str) and isinstance(message, str):
            return BlnkApiErrorDetail(
                code=code, message=message, details=error_detail.get("details")
            )

    error = body.get("error")
    if isinstance(error, str) and len(error) > 0:
        return BlnkApiErrorDetail(code="UNKNOWN", message=error)

    return None

"""HTTP response helpers: response formatting and JSON body reading."""

from __future__ import annotations

import json
from typing import Any, Optional

from .api_response import ApiResponse
from .errors import BlnkApiErrorDetail


def format_response(
    status: int,
    message: str,
    data: Any,
    error: Optional[BlnkApiErrorDetail] = None,
) -> ApiResponse:
    """Build an ApiResponse. `error` is attached only when truthy; otherwise
    the field is left unset."""
    if error:
        return ApiResponse(status=status, message=message, data=data, error=error)
    return ApiResponse(status=status, message=message, data=data)


def read_response_json_body(response: Any) -> Any:
    """Reads a transport response body as JSON, None for empty bodies.

    Text-first: if the response has a CALLABLE `text` -> read; blank/whitespace
    -> None; else json.loads (parse errors PROPAGATE to the caller — the core
    client catches them only on the non-ok path). Otherwise a callable `json`
    is used as fallback; otherwise None.
    """
    text_fn = getattr(response, "text", None)
    if callable(text_fn):
        text = text_fn()
        if text.strip() == "":
            return None
        return json.loads(text)

    json_fn = getattr(response, "json", None)
    if callable(json_fn):
        return json_fn()

    return None

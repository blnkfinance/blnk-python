"""Helper for decoding a multipart/streaming request body captured by a fake
transport into a string."""

from __future__ import annotations

from typing import Any


def read_stream_body(body: Any) -> str:
    if hasattr(body, "read") and callable(body.read):
        data = body.read()
    else:
        data = body
    if isinstance(data, (bytes, bytearray)):
        return bytes(data).decode("utf-8")
    return str(data)

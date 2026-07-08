"""Multipart form-data request bodies.

MultipartBody is the SDK's single multipart type. The core client detects a
MultipartBody `data` argument, uses its own headers (content-type with
boundary — they win over everything else), never sets the JSON content-type,
and never retries multipart requests.
"""

from __future__ import annotations

import mimetypes
import os
import random
from typing import Any, Dict, List, Optional, Tuple

_CRLF = b"\r\n"


def _random_boundary() -> str:
    # Boundary format: 26 dashes followed by 24 random digits.
    digits = "".join(random.choice("0123456789") for _ in range(24))
    return "-" * 26 + digits


class MultipartBody:
    """Ordered multipart/form-data builder.

    append(name, value, filename=None, content_type=None):
      - str value                -> plain text part (no Content-Type line);
      - bytes value              -> file part (Content-Type inferred from
                                    filename, default application/octet-stream);
      - file-like (has .read())  -> file part; filename defaults to the
                                    basename of its `.name` when available.

    get_headers() returns {"content-type": "multipart/form-data; boundary=…"}.
    read() returns the encoded bytes; the result is cached so the body can be
    re-read after the transport has consumed it.
    """

    def __init__(self) -> None:
        self.boundary = _random_boundary()
        self._parts: List[Tuple[str, Any, Optional[str], Optional[str]]] = []
        self._encoded: Optional[bytes] = None

    def append(
        self,
        name: str,
        value: Any,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> None:
        self._parts.append((name, value, filename, content_type))
        self._encoded = None

    def get_headers(self) -> Dict[str, str]:
        return {"content-type": f"multipart/form-data; boundary={self.boundary}"}

    # ------------------------------------------------------------------ #

    def _encode_part(
        self,
        name: str,
        value: Any,
        filename: Optional[str],
        content_type: Optional[str],
    ) -> bytes:
        is_file_like = hasattr(value, "read") and callable(value.read)

        if is_file_like and filename is None:
            stream_name = getattr(value, "name", None)
            if isinstance(stream_name, str) and stream_name:
                filename = os.path.basename(stream_name)

        disposition = f'Content-Disposition: form-data; name="{name}"'
        if filename is not None:
            disposition += f'; filename="{filename}"'

        header = disposition.encode("utf-8") + _CRLF
        if filename is not None or is_file_like or isinstance(value, (bytes, bytearray)):
            if content_type is None:
                guessed = mimetypes.guess_type(filename or "")[0]
                content_type = guessed or "application/octet-stream"
            header += f"Content-Type: {content_type}".encode("utf-8") + _CRLF
        elif content_type is not None:
            header += f"Content-Type: {content_type}".encode("utf-8") + _CRLF
        header += _CRLF

        if is_file_like:
            payload = value.read()
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
        elif isinstance(value, (bytes, bytearray)):
            payload = bytes(value)
        else:
            payload = str(value).encode("utf-8")

        return header + payload + _CRLF

    def read(self) -> bytes:
        if self._encoded is None:
            boundary_line = f"--{self.boundary}".encode("utf-8") + _CRLF
            chunks = []
            for name, value, filename, content_type in self._parts:
                chunks.append(boundary_line)
                chunks.append(self._encode_part(name, value, filename, content_type))
            chunks.append(f"--{self.boundary}--".encode("utf-8") + _CRLF)
            self._encoded = b"".join(chunks)
        return self._encoded


def is_multipart_body(data: Any) -> bool:
    """True when `data` is the SDK's multipart body type."""
    return isinstance(data, MultipartBody)

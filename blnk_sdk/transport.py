"""HTTP transport seam.

A transport is a callable `(url: str, init: TransportRequest) -> response` where the
response object exposes:

- `ok: bool`
- `status: int`
- `status_text: str`  (requests: `response.reason`; test doubles set it
  explicitly)
- optionally a CALLABLE `text()` returning the raw body string, and/or a
  CALLABLE `json()` returning the parsed body (read_response_json_body prefers
  `text` and falls back to `json` — both response styles are supported).

Timeouts MUST surface as blnk_sdk.errors.BlnkTimeoutError: the core client
maps it to a synthetic 408 and never retries it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

import requests

from .errors import BlnkTimeoutError
from .multipart import is_multipart_body


@dataclass
class TransportRequest:
    """Per-attempt request description handed to the transport.

    `timeout_ms` is the configured per-attempt timeout in milliseconds; the
    transport is responsible for enforcing it.
    """

    method: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    timeout_ms: Optional[Union[int, float]] = None


class RequestsTransportResponse:
    """Adapts requests.Response to the transport response protocol."""

    def __init__(self, response: requests.Response) -> None:
        self._response = response
        self.ok = response.ok
        self.status = response.status_code
        self.status_text = response.reason or ""
        self.headers = response.headers
        self.url = response.url

    def text(self) -> str:
        return self._response.text

    def json(self) -> Any:
        return self._response.json()


class RequestsTransport:
    """The default transport: a requests.Session with a per-request timeout
    (milliseconds converted to seconds).

    Note: timeout values are deliberately passed through without validation —
    a non-positive timeout is handed to requests as-is rather than being
    rejected or clamped.
    """

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self._session = session or requests.Session()

    def __call__(self, url: str, init: TransportRequest) -> RequestsTransportResponse:
        body = init.body
        if is_multipart_body(body):
            data: Any = body.read()
        elif isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = body

        timeout_s = None if init.timeout_ms is None else init.timeout_ms / 1000.0
        try:
            response = self._session.request(
                method=init.method,
                url=url,
                headers=init.headers,
                data=data,
                timeout=timeout_s,
            )
        except requests.exceptions.Timeout as exc:
            raise BlnkTimeoutError(str(exc)) from exc
        return RequestsTransportResponse(response)

    def close(self) -> None:
        self._session.close()

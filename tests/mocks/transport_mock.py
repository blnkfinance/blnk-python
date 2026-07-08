"""Fake HTTP transport stubs for unit tests.

A transport is a callable `(url, init) -> response`; the response exposes
ok/status/status_text and, optionally, callable text()/json() accessors.
Stubs may provide both accessors or only json(), so every response-body
fallback path in the SDK gets exercised."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

_MISSING = object()


class MockResponse:
    """Attribute bag; `text`/`json` are set as callables only when provided so
    the SDK's response-body fallback paths can be exercised individually."""

    def __init__(self, **attrs: Any) -> None:
        self.__dict__.update(attrs)


def make_response(
    ok: bool,
    status: int,
    status_text: str,
    json_body: Any = _MISSING,
    text_body: Any = _MISSING,
    json_raises: Optional[BaseException] = None,
    headers: Optional[Dict[str, str]] = None,
    url: str = "",
) -> MockResponse:
    attrs: Dict[str, Any] = {
        "ok": ok,
        "status": status,
        "status_text": status_text,
        "headers": dict(headers or {}),
        "url": url,
        "redirected": False,
        "type": "basic",
        "body": None,
        "body_used": False,
    }
    if text_body is not _MISSING:
        attrs["text"] = lambda: text_body
    if json_raises is not None:
        def _raise() -> Any:
            raise json_raises
        attrs["json"] = _raise
    elif json_body is not _MISSING:
        attrs["json"] = lambda: json_body
    return MockResponse(**attrs)


def transport_mock(url: str, init: Any) -> MockResponse:
    """Always-200 stub. Echoes the request headers back as the response
    headers and reflects the request url; tests assert on both."""
    return make_response(
        ok=True,
        status=200,
        status_text="OK",
        json_body={"message": "Success"},
        text_body='{"message":"Success"}',
        headers=dict(getattr(init, "headers", None) or {}),
        url=str(url),
    )


def transport_fail_mock(url: str, init: Any) -> MockResponse:
    """Always-500 stub. Note: status_text is `Failed` (not the canonical
    reason phrase) and the body carries neither `error` nor `error_detail`;
    tests depend on this exact shape."""
    return make_response(
        ok=False,
        status=500,
        status_text="Failed",
        json_body={"message": "Failed"},
        text_body='{"message":"Failed"}',
        headers=dict(getattr(init, "headers", None) or {}),
        url=str(url),
    )

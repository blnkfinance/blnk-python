"""Unit tests for `read_response_json_body` (2 cases)."""

from __future__ import annotations

from types import SimpleNamespace

from blnk_sdk.http_client import read_response_json_body


def test_returns_null_for_empty_bodies() -> None:
    response = SimpleNamespace(text=lambda: "")
    assert read_response_json_body(response) is None


def test_parses_non_empty_json_bodies() -> None:
    response = SimpleNamespace(text=lambda: '{"message":"deleted"}')
    assert read_response_json_body(response) == {"message": "deleted"}

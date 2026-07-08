"""Unit tests for `handle_error` log redaction (1 case)."""

from __future__ import annotations

from blnk_sdk.http_client import format_response
from blnk_sdk.logger import handle_error


def test_redacts_sensitive_values_before_logging() -> None:
    logged: list = []

    class RecordingLogger:
        def info(self, message, *meta):
            return None

        def error(self, message, *meta):
            logged.append((message, list(meta)))

    result = handle_error(
        Exception("failed with X-Blnk-Key: blnk_secret"),
        RecordingLogger(),
        format_response,
        "create",
    )

    message, meta = logged[0]
    assert message == "create"
    assert meta == [
        {"name": "Exception", "message": "failed with X-Blnk-Key: [REDACTED]"}
    ]
    # handle_error returns (500, <raw error message>, None) — unredacted.
    assert result.status == 500
    assert result.message == "failed with X-Blnk-Key: blnk_secret"
    assert result.data is None

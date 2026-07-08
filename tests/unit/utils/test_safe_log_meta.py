"""Unit tests for the safe-log-meta redaction helpers (4 cases).

Exceptions redact to {"name": type(exc).__name__, "message": ...}, so a
bare `Exception` redacts with the name "Exception".
"""

from __future__ import annotations

from blnk_sdk.safe_log_meta import (
    redact_sensitive_log_meta,
    redact_sensitive_log_value,
    redact_sensitive_string,
    safe_log_meta,
)


def test_redacts_auth_header_values_in_strings() -> None:
    value = "Request failed with X-Blnk-Key: blnk_local_dev_secret"
    assert (
        redact_sensitive_string(value)
        == "Request failed with X-Blnk-Key: [REDACTED]"
    )


def test_redacts_sensitive_object_keys() -> None:
    redacted = redact_sensitive_log_meta(
        {
            "endpoint": "health",
            "apiKey": "blnk_secret",
            "headers": {
                "X-Blnk-Key": "blnk_secret",
                "content-type": "application/json",
            },
        }
    )

    assert redacted["apiKey"] == "[REDACTED]"
    assert redacted["headers"] == {
        "X-Blnk-Key": "[REDACTED]",
        "content-type": "application/json",
    }


def test_redacts_error_objects_to_name_and_message_only() -> None:
    redacted = redact_sensitive_log_value(
        Exception("connection failed with X-Blnk-Key: blnk_secret")
    )

    assert redacted == {
        "name": "Exception",
        "message": "connection failed with X-Blnk-Key: [REDACTED]",
    }


def test_safe_log_meta_sanitizes_mixed_metadata() -> None:
    (error_meta,) = safe_log_meta(
        {
            "endpoint": "transactions",
            "error": Exception("network error"),
            "authorization": "Bearer abc123",
        }
    )

    # Key-level redaction wins before string regexes: authorization becomes
    # "[REDACTED]", not "Bearer [REDACTED]".
    assert error_meta == {
        "endpoint": "transactions",
        "error": {"name": "Exception", "message": "network error"},
        "authorization": "[REDACTED]",
    }

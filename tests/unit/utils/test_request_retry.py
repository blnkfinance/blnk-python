"""Unit tests for the request-retry helpers (6 cases)."""

from __future__ import annotations

from blnk_sdk.errors import BlnkTimeoutError
from blnk_sdk.request_retry import (
    is_retryable_transport_error,
    is_retryable_http_method,
    is_retryable_http_status,
    normalize_retry_count,
    normalize_retry_delay_ms,
    retry_delay_for_attempt,
)


def test_is_retryable_http_method() -> None:
    assert is_retryable_http_method("GET")
    assert not is_retryable_http_method("POST")
    assert not is_retryable_http_method("PUT")
    assert not is_retryable_http_method("DELETE")


def test_is_retryable_http_status() -> None:
    assert not is_retryable_http_status(404)
    assert is_retryable_http_status(500)
    assert is_retryable_http_status(503)


def test_is_retryable_transport_error() -> None:
    # Timeouts (BlnkTimeoutError) are deliberately not retryable; low-level
    # connection failures are.
    assert not is_retryable_transport_error(BlnkTimeoutError("aborted"))
    assert is_retryable_transport_error(TypeError("connection failed"))


def test_retry_delay_for_attempt_uses_linear_backoff() -> None:
    assert retry_delay_for_attempt(1, 2000) == 2000
    assert retry_delay_for_attempt(2, 2000) == 4000


def test_normalize_retry_count_clamps_invalid_values_to_1() -> None:
    assert normalize_retry_count(None) == 1
    assert normalize_retry_count(0) == 1
    assert normalize_retry_count(-1) == 1
    assert normalize_retry_count(float("nan")) == 1
    assert normalize_retry_count(float("inf")) == 1
    assert normalize_retry_count(float("-inf")) == 1
    assert normalize_retry_count(2.9) == 2
    assert normalize_retry_count(3) == 3


def test_normalize_retry_delay_ms_clamps_invalid_values_to_default() -> None:
    assert normalize_retry_delay_ms(None) == 2000
    assert normalize_retry_delay_ms(-1) == 2000
    assert normalize_retry_delay_ms(float("nan")) == 2000
    assert normalize_retry_delay_ms(float("inf")) == 2000
    assert normalize_retry_delay_ms(float("-inf")) == 2000
    assert normalize_retry_delay_ms(500) == 500

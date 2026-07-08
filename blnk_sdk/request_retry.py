"""Retry policy helpers used by the core client."""

from __future__ import annotations

import math
import time
from typing import Any, Optional, Union

from .constants import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY_MS
from .errors import BlnkTimeoutError

Number = Union[int, float]


def sleep_ms(ms: Number) -> None:
    time.sleep(ms / 1000.0)


def is_retryable_http_method(method: str) -> bool:
    return method == "GET"


def is_retryable_http_status(status: int) -> bool:
    return status >= 500


def normalize_retry_count(retry_count: Optional[Number]) -> int:
    """None, non-finite (NaN/±Inf), or < 1 -> the default of 1; otherwise
    floor(value)."""
    if retry_count is None:
        return DEFAULT_RETRY_COUNT
    value = float(retry_count)
    if not math.isfinite(value) or value < 1:
        return DEFAULT_RETRY_COUNT
    return math.floor(value)


def normalize_retry_delay_ms(retry_delay_ms: Optional[Number]) -> Number:
    """None, non-finite, or < 0 -> the default of 2000; otherwise the value is
    returned UNCHANGED (floats kept; 0 is legal — zero-delay retries)."""
    if retry_delay_ms is None:
        return DEFAULT_RETRY_DELAY_MS
    value = float(retry_delay_ms)
    if not math.isfinite(value) or value < 0:
        return DEFAULT_RETRY_DELAY_MS
    return retry_delay_ms


def is_retryable_transport_error(error: Any) -> bool:
    """False for non-exception values and for BlnkTimeoutError (timeouts are
    never retried); True for every other exception."""
    if not isinstance(error, Exception):
        return False
    if isinstance(error, BlnkTimeoutError):
        return False
    return True


def retry_delay_for_attempt(attempt: int, base_delay_ms: Number) -> Number:
    """Linear backoff, no jitter, no cap: base * attempt."""
    return base_delay_ms * attempt

"""Shared helpers for the integration and e2e suites.

Helpers only — zero test cases. Deliberately not named test_*.py so pytest
never collects it as a test module."""

from __future__ import annotations

import os
import random
import time

BASE_URL = "http://localhost:5001/"

# Local Core dev key; override with BLNK_API_KEY when running integration tests.
BLNK_API_KEY = os.environ.get("BLNK_API_KEY", "blnk-local-dev-secret-change-me")


def generate_random_numbers_with_prefix(prefix: str, count: int) -> str:
    digits = "".join(str(random.randint(0, 9)) for _ in range(count))
    return f"{prefix}-{digits}"


def sleep_seconds(seconds: float) -> None:
    time.sleep(seconds)

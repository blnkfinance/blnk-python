"""Unit tests for System.health: request shape and thrown-error handling.

One mock logger is created at module scope and deliberately shared; the
third_party_request fixture provides a fresh successful 200 mock request
per test. The error case builds its own failing mock, which raises
Exception("Network error occurred") — the request call IS recorded
before raising, and the error handler yields the 500 response.
"""

from __future__ import annotations

import pytest

from blnk_sdk.http_client import format_response
from blnk_sdk.services.system import System
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest

MOCK_LOGGER = create_mock_logger()  # deliberately shared by the whole suite


@pytest.fixture
def third_party_request():
    """Provide a fresh successful mock request (200 OK) per test."""
    return create_mock_blnk_request(True, None, 200)


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_health_calls_get_health(third_party_request) -> None:
    """health calls GET /health"""
    captured_request = CapturingRequest(third_party_request)
    system = System(captured_request, MOCK_LOGGER, format_response)

    response = system.health()

    assert _args(captured_request) == [("health", None, "GET")]
    assert response.status == 200


def test_health_handles_thrown_errors() -> None:
    """health handles thrown errors"""
    error_request = create_mock_blnk_request(False, "Network error occurred")
    captured_request = CapturingRequest(error_request)
    system = System(captured_request, MOCK_LOGGER, format_response)

    response = system.health()

    # the call is recorded even though the mock threw
    assert _args(captured_request) == [("health", None, "GET")]
    assert response.status == 500
    assert response.message == "Network error occurred"

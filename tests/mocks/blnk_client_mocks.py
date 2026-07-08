"""Standard mocks shared by the service-level unit tests."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.client import BlnkClientOptions

from .capture import CapturingCallable, CapturingRequest, capture_fn  # re-export
from .mock_transactions import MockTransaction

__all__ = [
    "CapturingCallable",
    "CapturingRequest",
    "LEDGER_ID",
    "capture_fn",
    "create_mock_blnk_client_options",
    "create_mock_blnk_request",
    "create_mock_logger",
    "create_mock_services",
]

LEDGER_ID = "123456"


class MockLogger:
    """Test logger that records every call in `.calls` for assertions.

    All three levels — including `error` and `debug` — print to stdout with
    a `Mock Info: ` / `Mock Error: ` / `Mock Debug: ` prefix; tests that
    capture output rely on these exact prefixes.
    """

    def __init__(self) -> None:
        self.calls: List[tuple] = []

    def info(self, message: str, *meta: Any) -> None:
        self.calls.append(("info", message, list(meta)))
        print(f"Mock Info: {message}", *meta)

    def error(self, message: str, *meta: Any) -> None:
        self.calls.append(("error", message, list(meta)))
        print(f"Mock Error: {message}", *meta)

    def debug(self, message: str, *meta: Any) -> None:
        self.calls.append(("debug", message, list(meta)))
        print(f"Mock Debug: {message}", *meta)


def create_mock_logger() -> MockLogger:
    return MockLogger()


def create_mock_blnk_client_options() -> BlnkClientOptions:
    """Builds client options without retry_count/retry_delay_ms so the
    retry defaults apply."""
    return BlnkClientOptions(
        base_url="http://mock-api.com",
        timeout=5000,
        logger=create_mock_logger(),
    )


def create_mock_services() -> Dict[str, type]:
    """Registers stub services for the core client tests.

    All three names deliberately map to the same stub class, and no other
    service name is registered; tests depend on both facts.
    """
    return {
        "Ledgers": MockTransaction,
        "LedgerBalances": MockTransaction,
        "Transactions": MockTransaction,
    }


def _mock_api_response(data: Any, status: int = 200, message: str = "Success") -> ApiResponse:
    return ApiResponse(status=status, message=message, data=data)


def create_mock_blnk_request(
    success: bool,
    throw_error: Optional[str] = None,
    status: int = 200,
) -> Callable[..., ApiResponse]:
    """Standard mock for the client's request callable.

    - throw_error is not None -> raises Exception(throw_error).
    - success -> echoes the request data merged with ledger_id "123456",
      message "Success", with the given status.
    - else -> (500, "Internal Server Error", None).
    """

    def request(
        endpoint: str,
        data: Any,
        method: str,
        header_options: Optional[Dict[str, str]] = None,
    ) -> ApiResponse:
        if throw_error is not None:
            raise Exception(throw_error)
        if success:
            base = dict(data) if isinstance(data, dict) else {}
            to_dict = getattr(data, "to_dict", None)
            if not isinstance(data, dict) and callable(to_dict):
                base = to_dict()
            mock_data = {**base, "ledger_id": LEDGER_ID}
            return _mock_api_response(mock_data, status)
        return _mock_api_response(None, 500, "Internal Server Error")

    return request

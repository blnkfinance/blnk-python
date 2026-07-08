"""Unit tests for the Reconciliation service: matching-rule creation,
file uploads (from a path and from an open stream), and reconciliation
runs.

FILE_PATH resolves to the file.csv fixture committed at the project
root. Uploads are captured with the MultipartBody object as the data
argument.
"""

from __future__ import annotations

from pathlib import Path

from blnk_sdk.http_client import format_response
from blnk_sdk.multipart import MultipartBody
from blnk_sdk.services.reconciliation import Reconciliation
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest

FILE_PATH = str(Path(__file__).resolve().parents[3] / "file.csv")


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


# --------------------------------------------------------------------- #
# Group 1 — `Reconciliation`
# --------------------------------------------------------------------- #


def test_create_matching_rule() -> None:
    """Create Matching Rule"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)
    data = {
        "criteria": [
            {
                "field": "amount",
                "operator": "equals",
                "allowable_drift": 0.01,
            },
        ],
        "description": "Test Matching Rule",
        "name": "Test Matching Rule",
    }

    response = reconciliation.create_matching_rule(data)

    assert _args(captured_request) == [
        ("reconciliation/matching-rules", data, "POST"),
    ]
    assert response.status == 201


def test_should_upload_file_successfully_when_given_a_valid_file_path() -> None:
    """should upload file successfully when given a valid file path"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.upload(FILE_PATH, "Stripe")

    # the captured data argument must be the multipart body
    assert isinstance(captured_request.calls[0][1], MultipartBody)
    assert response.status == 201


def test_should_handle_error_gracefully_when_given_an_invalid_file_path() -> None:
    """should handle error gracefully when given an invalid file path"""
    mock_logger = create_mock_logger()
    file_path = "./no_file.csv"
    # The mock would raise if called, but it is never reached: upload's own
    # file-existence guard produces the response locally. Note: a missing
    # local file yields a 404 (not 400) without any HTTP call being made.
    third_party_request = create_mock_blnk_request(
        False, f"File does not exist at path: {file_path}", 404
    )
    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.upload(file_path, "Stripe")

    assert response.status == 404


def test_should_upload_file_successfully_when_given_a_valid_readstream() -> None:
    """should upload file successfully when given a valid Readstream"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    with open(FILE_PATH, "rb") as read_stream:
        response = reconciliation.upload(read_stream, "Stripe")

    # the captured data argument must be the multipart body
    assert isinstance(captured_request.calls[0][1], MultipartBody)
    assert response.status == 201


# --------------------------------------------------------------------- #
# Group 2 — `Run Reconciliation`
# --------------------------------------------------------------------- #


def test_start_reconciliation() -> None:
    """Start Reconciliation"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)
    data = {
        "upload_id": "0987654321",
        "matching_rule_ids": ["1233455555"],
        "dry_run": False,
        "strategy": "one_to_many",
        "grouping_criteria": "amount",
    }

    response = reconciliation.run(data)

    assert _args(captured_request) == [("reconciliation/start", data, "POST")]
    assert response.status == 200


def test_should_handle_thrown_errors_gracefully() -> None:
    """should handle thrown errors gracefully"""
    mock_logger = create_mock_logger()
    # raises Exception("An error occurred") when called -> handle_error path.
    third_party_request = create_mock_blnk_request(False, "An error occurred", 500)
    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)
    data = {
        "upload_id": "0987654321",
        "matching_rule_ids": ["1233455555"],
        "dry_run": False,
        "strategy": "one_to_many",
        "grouping_criteria": "amount",
    }

    response = reconciliation.run(data)

    assert response.status == 500

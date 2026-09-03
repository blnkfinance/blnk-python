"""Unit tests for `parse_blnk_api_error_body` (3 cases)."""

from __future__ import annotations

from blnk_sdk.errors import (
    BlnkApiErrorDetail,
    BlnkErrorCode,
    parse_blnk_api_error_body,
)


def test_parses_error_detail_from_core_api_responses() -> None:
    parsed = parse_blnk_api_error_body(
        {
            "error": "ledger not found",
            "error_detail": {
                "code": "LGR_NOT_FOUND",
                "message": "ledger not found",
                "details": {"ledger_id": "ldg_missing"},
            },
        }
    )

    assert parsed == BlnkApiErrorDetail(
        code="LGR_NOT_FOUND",
        message="ledger not found",
        details={"ledger_id": "ldg_missing"},
    )


def test_falls_back_to_legacy_error_string() -> None:
    parsed = parse_blnk_api_error_body({"error": "invalid request"})
    assert parsed == BlnkApiErrorDetail(code="UNKNOWN", message="invalid request")


def test_returns_null_for_non_object_bodies() -> None:
    assert parse_blnk_api_error_body(None) is None
    assert parse_blnk_api_error_body("oops") is None


def test_surfaces_core_0_15_3_codes_callers_should_recognize() -> None:
    cases = [
        {
            "code": BlnkErrorCode.TXN_INVALID_AMOUNT,
            "message": "precise_amount must be positive",
        },
        {
            "code": BlnkErrorCode.TXN_VALIDATION_ERROR,
            "message": "source and destination cannot be the same",
        },
        {
            "code": BlnkErrorCode.GEN_CONFLICT,
            "message": "internal balance already exists",
        },
    ]
    for case in cases:
        parsed = parse_blnk_api_error_body(
            {"error_detail": {"code": case["code"], "message": case["message"]}}
        )
        assert parsed == BlnkApiErrorDetail(
            code=case["code"], message=case["message"]
        )

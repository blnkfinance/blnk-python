"""Unit tests for `parse_blnk_api_error_body` and `BlnkErrorCode`."""

from __future__ import annotations

from blnk_sdk.errors import (
    BlnkApiErrorDetail,
    BlnkErrorCode,
    parse_blnk_api_error_body,
)

KNOWN_PREFIXES = frozenset(
    {
        "GEN",
        "AUTH",
        "APIKEY",
        "TXN",
        "BAL",
        "LGR",
        "ACC",
        "IDT",
        "RECON",
        "META",
        "HOOK",
        "QUEUE",
        "SRCH",
        "ADMIN",
    }
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


def test_surfaces_txn_already_refunded_from_core_0_15_4_duplicate_refund() -> None:
    parsed = parse_blnk_api_error_body(
        {
            "error": "transaction txn_1 has already been refunded",
            "error_detail": {
                "code": BlnkErrorCode.TXN_ALREADY_REFUNDED,
                "message": "transaction txn_1 has already been refunded",
                "details": {"transaction_id": "txn_1"},
            },
        }
    )

    assert parsed == BlnkApiErrorDetail(
        code=BlnkErrorCode.TXN_ALREADY_REFUNDED,
        message="transaction txn_1 has already been refunded",
        details={"transaction_id": "txn_1"},
    )


def test_surfaces_bal_not_found_when_transaction_names_missing_balance() -> None:
    parsed = parse_blnk_api_error_body(
        {
            "error": "balance bln_missing not found",
            "error_detail": {
                "code": BlnkErrorCode.BAL_NOT_FOUND,
                "message": "balance bln_missing not found",
            },
        }
    )

    assert parsed == BlnkApiErrorDetail(
        code=BlnkErrorCode.BAL_NOT_FOUND,
        message="balance bln_missing not found",
    )


def test_error_code_constants_are_self_named_unique_and_prefixed() -> None:
    seen: set[str] = set()
    count = 0
    for name, value in vars(BlnkErrorCode).items():
        if name.startswith("_") or not isinstance(value, str):
            continue
        count += 1
        assert name == value, f"constant name and value must match: {name}"
        assert value not in seen, f"duplicate error code {value}"
        seen.add(value)
        prefix = value.split("_", 1)[0]
        assert prefix in KNOWN_PREFIXES, f"unknown Core prefix on {value}"
    assert count == 79, "expected the full Core 0.15.4 catalogue"


def test_core_0_15_4_codes_are_present() -> None:
    assert BlnkErrorCode.TXN_ALREADY_REFUNDED == "TXN_ALREADY_REFUNDED"
    assert BlnkErrorCode.BAL_NOT_FOUND == "BAL_NOT_FOUND"
    assert BlnkErrorCode.TXN_VALIDATION_ERROR == "TXN_VALIDATION_ERROR"
    assert BlnkErrorCode.GEN_CONFLICT == "GEN_CONFLICT"


def test_pre_1_5_0_constants_are_unchanged() -> None:
    assert BlnkErrorCode.TXN_INVALID_AMOUNT == "TXN_INVALID_AMOUNT"
    assert BlnkErrorCode.GEN_CONFLICT == "GEN_CONFLICT"
    assert BlnkErrorCode.TXN_VALIDATION_ERROR == "TXN_VALIDATION_ERROR"

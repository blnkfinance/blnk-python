"""Unit tests for validate_list_options."""

from __future__ import annotations

from blnk_sdk.types.list_options import ListOptions
from blnk_sdk.validators.list_validators import validate_list_options


def test_accepts_empty_options() -> None:
    """accepts empty options"""
    assert validate_list_options({}) is None


def test_accepts_boundary_values() -> None:
    """accepts limit 1 and offset 0, the smallest values Core allows"""
    assert validate_list_options(ListOptions(limit=1, offset=0).to_dict()) is None


def test_rejects_null_payload() -> None:
    """rejects null payload"""
    assert (
        validate_list_options(None)
        == "Data must be a valid object of type ListOptions"
    )


def test_rejects_limit_below_one() -> None:
    """rejects limit below 1"""
    assert validate_list_options(ListOptions(limit=0).to_dict()) == (
        "limit must be at least 1"
    )


def test_rejects_non_integer_limit() -> None:
    """rejects non-integer limit"""
    assert (
        validate_list_options({"limit": 2.5})
        == "limit must be an integer if provided"
    )
    assert (
        validate_list_options({"limit": None})
        == "limit must be an integer if provided"
    )


def test_rejects_negative_offset() -> None:
    """rejects negative offset"""
    assert validate_list_options(ListOptions(offset=-5).to_dict()) == (
        "offset must be at least 0"
    )


def test_rejects_non_integer_offset() -> None:
    """rejects non-integer offset"""
    assert (
        validate_list_options({"offset": "0"})
        == "offset must be an integer if provided"
    )


def test_limit_checked_first() -> None:
    """limit is checked before offset"""
    assert (
        validate_list_options(ListOptions(limit=0, offset=-1).to_dict())
        == "limit must be at least 1"
    )


def test_rejects_unknown_keys() -> None:
    """rejects unknown dictionary keys so typos are not silently dropped"""
    assert (
        validate_list_options({"limt": 50}) == "unsupported list option: limt"
    )
    assert (
        validate_list_options({"limit": 10, "page": 2})
        == "unsupported list option: page"
    )


def test_unknown_keys_checked_after_limit() -> None:
    """limit errors still surface before unknown-key errors"""
    assert (
        validate_list_options({"limit": 0, "limt": 50})
        == "limit must be at least 1"
    )

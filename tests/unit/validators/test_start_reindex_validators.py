"""Unit tests for `validate_start_reindex_request` —
`start reindex validators` (3 cases).
"""

from __future__ import annotations

from blnk_sdk.validators.search_validators import validate_start_reindex_request


def test_validate_start_reindex_request_accepts_empty_options() -> None:
    """ValidateStartReindexRequest accepts empty options"""
    assert validate_start_reindex_request({}) is None


def test_validate_start_reindex_request_accepts_positive_batch_size() -> None:
    """ValidateStartReindexRequest accepts positive batch_size"""
    assert validate_start_reindex_request({"batch_size": 1000}) is None


def test_validate_start_reindex_request_rejects_non_integer_batch_size() -> None:
    """ValidateStartReindexRequest rejects non-integer batch_size"""
    assert (
        validate_start_reindex_request({"batch_size": 1.5})
        == "batch_size must be a positive integer if provided"
    )

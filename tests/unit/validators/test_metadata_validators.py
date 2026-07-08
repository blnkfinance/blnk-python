"""Unit tests for `validate_update_metadata_data`
(`ValidateUpdateMetadataData`, 4 cases).

Rejections are asserted against the exact full message
`meta_data must be a valid object`.
"""

from __future__ import annotations

from blnk_sdk.validators.metadata_validators import validate_update_metadata_data

VALID_DATA = {"meta_data": {"project_owner": "Acme LLC"}}


def test_accepts_valid_payload() -> None:
    """accepts valid payload"""
    assert validate_update_metadata_data("ldg_123", VALID_DATA) is None


def test_rejects_empty_id() -> None:
    """rejects empty id"""
    assert validate_update_metadata_data("", VALID_DATA) == "id is required"


def test_rejects_missing_meta_data() -> None:
    """rejects missing meta_data"""
    assert (
        validate_update_metadata_data("ldg_123", {})
        == "meta_data must be a valid object"
    )


def test_rejects_non_object_meta_data() -> None:
    """rejects non-object meta_data"""
    assert (
        validate_update_metadata_data("ldg_123", {"meta_data": "invalid"})
        == "meta_data must be a valid object"
    )

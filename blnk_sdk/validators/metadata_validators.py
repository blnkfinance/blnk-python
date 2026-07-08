"""Validators for metadata requests.

Returns the exact error message string on failure, None when valid; the
first failing check wins.
"""

from __future__ import annotations

from typing import Any, Optional

from ..string_utils import is_valid_string
from ..types import DTO
from .common import is_valid_meta_data

__all__ = ["validate_update_metadata_data"]


def validate_update_metadata_data(id: Any, data: Any) -> Optional[str]:
    """Validates arguments for Metadata.update."""
    if not is_valid_string(id) or id == "":
        return "id is required"

    # Structured-payload gate: dicts and lists both pass; DTOs pass via
    # their dict view; falsy values and str/number/bool fail.
    d: Any = data
    if not isinstance(d, (dict, list)):
        if isinstance(d, DTO):
            d = d.to_dict()
        else:
            return "Data must be a valid object of type UpdateMetadataData"

    # meta_data is required here: an absent key fails (a list payload has no
    # named fields, so it fails too); a key present with None fails;
    # str/number/bool fail; both {} and [] pass.
    if (
        not isinstance(d, dict)
        or "meta_data" not in d
        or not is_valid_meta_data(d["meta_data"])
    ):
        return "meta_data must be a valid object"

    return None

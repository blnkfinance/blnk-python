"""Unit tests for `SearchIdentityResponse` —
`SearchIdentityResponse API shape` (1 case).

NOTE the NEGATIVE `dob` (-62135596800 = year 0001) — Typesense timestamps are
Unix-seconds numbers, never date objects.
"""

from __future__ import annotations

from blnk_sdk.string_utils import is_valid_number
from blnk_sdk.types.search import (
    SearchHit,
    SearchIdentityDocument,
    SearchIdentityResponse,
    SearchRequestParams,
)


def test_identity_document_includes_indexed_fields() -> None:
    """identity document includes indexed fields"""
    response = SearchIdentityResponse(
        found=1,
        out_of=13,
        page=1,
        request_params=SearchRequestParams(
            collection_name="identities",
            q="*",
            per_page=1,
        ),
        search_time_ms=5,
        hits=[
            SearchHit(
                document=SearchIdentityDocument(
                    id="idt_fbf6a26c-82c6-46fb-9237-8fbba55a23c0",
                    identity_id="idt_fbf6a26c-82c6-46fb-9237-8fbba55a23c0",
                    identity_type="organization",
                    created_at=1781225782,
                    dob=-62135596800,
                    meta_data={},
                ),
                highlights=[],
            )
        ],
    )

    assert is_valid_number(response.hits[0].document.created_at)
    assert response.hits[0].document.identity_id.startswith("idt_") is True

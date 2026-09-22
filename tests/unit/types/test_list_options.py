"""Unit tests for ListOptions: field map and query-string rendering."""

from __future__ import annotations

from blnk_sdk.types.list_options import ListOptions, list_options_query_string


def test_unset_fields_absent() -> None:
    """unset fields have no key in the map"""
    assert ListOptions().to_dict() == {}
    assert ListOptions(limit=5).to_dict() == {"limit": 5}


def test_empty_query_string() -> None:
    """toQueryString is empty when nothing is set"""
    assert ListOptions().to_query_string() == ""
    assert list_options_query_string({}) == ""


def test_renders_in_insertion_order() -> None:
    """toQueryString renders fields in the order they were set"""
    assert ListOptions(limit=10, offset=30).to_query_string() == "?limit=10&offset=30"
    assert list_options_query_string({"limit": 10, "offset": 30}) == "?limit=10&offset=30"
    assert list_options_query_string({"offset": 30, "limit": 10}) == "?offset=30&limit=10"


def test_last_write_wins() -> None:
    """setting a field twice keeps the last value"""
    options = ListOptions(limit=3)
    options.limit = 7
    assert options.to_query_string() == "?limit=7"

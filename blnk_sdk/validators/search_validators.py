"""Validators for search requests.

Validators return `str | None` — None means valid; a non-None value is the
exact error message callers surface (including the double-quoted literals
and the phrasing differences between the range checks). Check order is part
of the SDK's behavior: the first failing check wins. Validators accept both
raw dicts (the canonical dict view) and DTO dataclasses (normalized via
to_dict(); None fields become absent keys, i.e. "not provided").

Optional-field guards are key-presence checks: an absent key is skipped,
while a key explicitly present with None counts as "provided" and fails the
type/integer check.
"""

from __future__ import annotations

import math
from typing import Any, List, Optional

from ..coercion import is_truthy
from ..types import DTO
from .common import is_valid_meta_data

SEARCH_COLLECTIONS: List[str] = [
    "ledgers",
    "transactions",
    "balances",
    "identities",
]

MAX_PER_PAGE = 250

FILTER_OPERATORS: List[str] = [
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "between",
    "like",
    "ilike",
    "isnull",
    "isnotnull",
]

VALUELESS_OPERATORS: List[str] = ["isnull", "isnotnull"]
VALUES_ARRAY_OPERATORS: List[str] = ["in", "between"]

MAX_FILTER_LIMIT = 100


def _dict_view(data: Any) -> Any:
    """Canonical validator input is the dict view."""
    if isinstance(data, DTO):
        return data.to_dict()
    return data


def _is_integral_number(value: Any) -> bool:
    """True only for finite numbers with no fractional part. Strings,
    booleans, None, NaN and infinities all fail (bools are excluded
    explicitly because Python bools are ints)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value) and value.is_integer()
    return False


def _is_filter_logical_operator(value: Any) -> bool:
    """Exact match against the two logical operators."""
    return value == "and" or value == "or"


def _is_filter_sort_order(value: Any) -> bool:
    """Exact match against the two sort orders."""
    return value == "asc" or value == "desc"


def validate_search_collection(service: Any) -> Optional[str]:
    """Validates a search collection name.

    Membership is an exact, case-sensitive check against the four collection
    literals; the message does not echo the offending value.
    """
    if service not in SEARCH_COLLECTIONS:
        return "collection must be ledgers, transactions, balances, or identities"
    return None


def validate_multi_search_params(data: Any) -> Optional[str]:
    """Validates a multi-search body: `searches` must be a non-empty list,
    and each entry needs a valid `collection` plus params that pass
    `validate_search_params`. Messages are prefixed `searches[i]`."""
    data = _dict_view(data)

    if not is_truthy(data) or not is_valid_meta_data(data):
        return "Multi-search params must be a valid object"

    searches = data.get("searches") if isinstance(data, dict) else None
    if not isinstance(searches, list) or len(searches) == 0:
        return "searches must be a non-empty array"

    for index in range(len(searches)):
        raw = _dict_view(searches[index])
        if not is_truthy(raw) or not is_valid_meta_data(raw) or not isinstance(raw, dict):
            return f"searches[{index}] must be a valid object"

        entry = dict(raw)
        collection = entry.pop("collection", None)
        if not isinstance(collection, str) or validate_search_collection(collection) is not None:
            return (
                f"searches[{index}].collection must be ledgers, transactions, "
                "balances, or identities"
            )

        params_error = validate_search_params(entry)
        if params_error:
            return f"searches[{index}]: {params_error}"

    return None


def validate_search_params(data: Any) -> Optional[str]:
    """Validates search parameters.

    Checks run in the order q, page, per_page, query_by, filter_by, sort_by;
    the first failure wins.
    """
    data = _dict_view(data)

    # Structured-payload gate: falsy values and truthy non-objects
    # (str/number/True) are rejected; lists pass here, then fail the q check.
    if not is_truthy(data) or not is_valid_meta_data(data):
        return "Search params must be a valid object"

    # One message (with double quotes around q) covers a missing, wrong-type,
    # empty or whitespace-only q.
    q = data.get("q") if isinstance(data, dict) else None
    if not isinstance(q, str) or q.strip() == "":
        return 'Field "q" must be filled'

    # The remaining optional fields are checked only when their key is
    # present. (Only dicts can reach this point: any other object fails the
    # q check.)
    if "page" in data:
        page = data["page"]
        if not _is_integral_number(page) or page < 1:
            return "page must be a positive integer if provided"

    if "per_page" in data:
        per_page = data["per_page"]
        if not _is_integral_number(per_page) or per_page < 1 or per_page > MAX_PER_PAGE:
            return "per_page must be an integer between 1 and 250 if provided"

    if "query_by" in data and not isinstance(data["query_by"], str):
        return "query_by must be a string if provided"

    if "filter_by" in data and not isinstance(data["filter_by"], str):
        return "filter_by must be a string if provided"

    if "sort_by" in data and not isinstance(data["sort_by"], str):
        return "sort_by must be a string if provided"

    return None


def _validate_filter_condition(filter: Any, index: int) -> Optional[str]:
    """Validates one filter condition. `index` is the 0-based position and
    interpolates into the messages as a plain integer. (The parameter name
    `filter` intentionally shadows the builtin locally.)"""
    filter = _dict_view(filter)

    if not is_truthy(filter) or not is_valid_meta_data(filter):
        return f"filters[{index}] must be a valid object"

    field = filter.get("field") if isinstance(filter, dict) else None
    if not isinstance(field, str) or field.strip() == "":
        return f"filters[{index}].field must be a non-empty string"

    operator = filter.get("operator")
    if not isinstance(operator, str) or operator not in FILTER_OPERATORS:
        return f"filters[{index}].operator must be a supported filter operator"

    # `in` and `between` share one rule — values must be a non-empty array
    # (between does not require exactly two entries). Once satisfied the
    # function returns immediately: `value` is never inspected for these
    # operators.
    if operator in VALUES_ARRAY_OPERATORS:
        values = filter.get("values")
        if not isinstance(values, list) or len(values) == 0:
            return (
                f"filters[{index}].values must be a non-empty array "
                f'for operator "{operator}"'
            )
        return None

    if operator in VALUELESS_OPERATORS:
        return None

    # Presence check, not truthiness: 0, "", False and NaN are all accepted
    # values; only an absent key or an explicit None fail.
    if filter.get("value") is None:
        return f'filters[{index}].value is required for operator "{operator}"'

    return None


def validate_filter_params(data: Any) -> Optional[str]:
    """Validates filter parameters.

    Per-condition errors (in order) win over all top-level optional-field
    errors. An empty `filters` list is valid.
    """
    data = _dict_view(data)

    # Structured-payload gate: lists pass here, then fail the filters check
    # below (a list has no `filters` field).
    if not is_truthy(data) or not is_valid_meta_data(data):
        return "Filter params must be a valid object"

    filters = data.get("filters") if isinstance(data, dict) else None
    if not isinstance(filters, list):
        return "filters must be an array"

    for index in range(len(filters)):
        filter_error = _validate_filter_condition(filters[index], index)
        if filter_error:
            return filter_error

    # (Only dicts can reach this point: any other object fails the filters
    # check above.) Optional fields are checked only when their key is
    # present.
    if "logical_operator" in data:
        logical_operator = data["logical_operator"]
        if not isinstance(logical_operator, str) or not _is_filter_logical_operator(
            logical_operator
        ):
            return 'logical_operator must be "and" or "or" if provided'

    if "sort_by" in data and not isinstance(data["sort_by"], str):
        return "sort_by must be a string if provided"

    if "sort_order" in data:
        sort_order = data["sort_order"]
        if not isinstance(sort_order, str) or not _is_filter_sort_order(sort_order):
            return 'sort_order must be "asc" or "desc" if provided'

    if "include_count" in data and not isinstance(data["include_count"], bool):
        return "include_count must be a boolean if provided"

    if "limit" in data:
        limit = data["limit"]
        if not _is_integral_number(limit) or limit < 1 or limit > MAX_FILTER_LIMIT:
            return "limit must be an integer between 1 and 100 if provided"

    if "offset" in data:
        offset = data["offset"]
        # `offset: 0` is VALID (non-negative, not positive).
        if not _is_integral_number(offset) or offset < 0:
            return "offset must be a non-negative integer if provided"

    return None


def validate_start_reindex_request(data: Any) -> Optional[str]:
    """Validates reindex options. `Search.start_reindex` only runs this when
    options are provided."""
    data = _dict_view(data)

    if not is_truthy(data) or not is_valid_meta_data(data):
        return "Reindex options must be a valid object"

    # Non-dict objects that pass the guard above (e.g. lists) have no
    # `batch_size` field, so the check is skipped for them.
    if isinstance(data, dict) and "batch_size" in data:
        batch_size = data["batch_size"]
        if not _is_integral_number(batch_size) or batch_size < 1:
            return "batch_size must be a positive integer if provided"

    return None

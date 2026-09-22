"""The Search service — full-text search and filtering across collections.

Endpoint strings have NO leading slash (the client concatenates onto base_url,
which is guaranteed to end with "/"). No header_options are ever passed
(3-arg request calls). Path interpolation performs NO URL-encoding — only the
four literal collection names ever reach the path in practice (the collection
is validated first).

Both `search` and `filter` validate the collection BEFORE the params — when
both are invalid the collection message wins. The two path shapes differ
intentionally: `search` posts to `search/{collection}` (prefix style) while
`filter` posts to `{collection}/filter` (suffix style). Do not "normalize"
either. `multi_search` posts to `multi-search` (no collection in the path).
Errors surface under the names "search", "filter", "multiSearch",
"startReindex", and "getReindexStatus" — logs and callers depend on these
exact strings.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ..logger import handle_error
from ..validators.search_validators import (
    validate_filter_params,
    validate_multi_search_params,
    validate_search_collection,
    validate_search_params,
    validate_start_reindex_request,
)


def _serialize(data: Any) -> Any:
    """DTOs are serialized to wire dicts before the request; raw dicts are
    forwarded by reference — the caller's object passes through unmodified."""
    if not isinstance(data, dict):
        to_dict = getattr(data, "to_dict", None)
        if callable(to_dict):
            return to_dict()
    return data


class Search:
    def __init__(
        self,
        request: Callable[..., Any],
        logger: Any,
        format_response: Callable[..., Any],
    ) -> None:
        self._request = request
        self._logger = logger
        self._format_response = format_response

    def search(self, data: Any, collection: str) -> Any:
        """POST search/{collection} — validates the collection, then the
        params; `data` is forwarded unmodified (no renames, no transforms,
        no defaulting)."""
        try:
            collection_error = validate_search_collection(collection)
            if collection_error:
                return self._format_response(400, collection_error, None)

            payload = _serialize(data)
            params_error = validate_search_params(payload)
            if params_error:
                return self._format_response(400, params_error, None)

            return self._request(f"search/{collection}", payload, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "search")

    def multi_search(self, data: Any) -> Any:
        """POST multi-search — several single-collection searches in one
        round trip. The body is validated, then forwarded unmodified.
        `data` may be a dict or a `MultiSearchParams` DTO."""
        try:
            payload = _serialize(data)
            params_error = validate_multi_search_params(payload)
            if params_error:
                return self._format_response(400, params_error, None)

            return self._request("multi-search", payload, "POST")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "multiSearch"
            )

    def filter(self, data: Any, collection: str) -> Any:
        """POST {collection}/filter — NOTE the path shape: collection FIRST,
        unlike `search`. `data` is forwarded unmodified. (The name shadows
        the builtin `filter` only as a method name — intentional.)"""
        try:
            collection_error = validate_search_collection(collection)
            if collection_error:
                return self._format_response(400, collection_error, None)

            payload = _serialize(data)
            params_error = validate_filter_params(payload)
            if params_error:
                return self._format_response(400, params_error, None)

            return self._request(f"{collection}/filter", payload, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "filter")

    def start_reindex(self, options: Optional[Any] = None) -> Any:
        """POST search/reindex.

        `options=None` means "not provided" — the validator is skipped
        entirely. Unlike every other endpoint method, the body is REBUILT:
        `{batch_size: ...}` when a batch_size key is present, else `{}`; any
        other property on `options` is silently dropped (and never
        validated). The empty-dict body `{}` IS sent as a JSON body, unlike
        `get_reindex_status`, which sends no body at all.
        """
        try:
            opts = _serialize(options) if options is not None else None
            if opts is not None:
                params_error = validate_start_reindex_request(opts)
                if params_error:
                    return self._format_response(400, params_error, None)

            # Rebuild the body: only batch_size survives, and only when the
            # key is present.
            if isinstance(opts, dict) and "batch_size" in opts:
                body: dict = {"batch_size": opts["batch_size"]}
            else:
                body = {}

            return self._request("search/reindex", body, "POST")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "startReindex"
            )

    def get_reindex_status(self) -> Any:
        """GET search/reindex — no request body at all. GETs are retryable
        per core-client rules; the POSTs in this module never retry."""
        try:
            return self._request("search/reindex", None, "GET")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "getReindexStatus"
            )

"""Percent-encoding and validation for URL path segments and query values.

Every caller-supplied value that becomes part of a request path must go
through `path_segment` (or `endpoint_path`), so an id like "../backup" or
"%2e%2e/secret" cannot change which endpoint the client's API key is sent
to. `percent_encode` alone is not enough for paths: it keeps "." unescaped,
so "." and ".." survive it as dot segments.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote, unquote

from .errors import InvalidPathSegmentError

# Every character is percent-encoded except the unreserved set:
# A-Z a-z 0-9 - _ . ! ~ * ' ( )
_SAFE = "-_.!~*'()"


def percent_encode(value: str) -> str:
    return quote(str(value), safe=_SAFE)


def append_query_param(endpoint: str, name: str, value: str) -> str:
    """Append one encoded query pair to an endpoint that may already have a
    query string. Uses `&` when `?` is already present, otherwise `?`."""
    pair = f"{percent_encode(name)}={percent_encode(value)}"
    separator = "&" if "?" in endpoint else "?"
    return f"{endpoint}{separator}{pair}"


_FORBIDDEN_SEGMENT_CHARS = "/\\?#%"


def _as_text(value: Any) -> str:
    """Strings pass through; integers (not bools) are formatted; anything
    else is rejected rather than stringified into the path."""
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    raise InvalidPathSegmentError(
        f"invalid path segment: expected a string, got {type(value).__name__}"
    )


def _check_not_dot_or_empty(value: str) -> None:
    if value == "":
        raise InvalidPathSegmentError("invalid path segment: value is empty")
    if value in (".", ".."):
        raise InvalidPathSegmentError(f"invalid path segment {value!r}")


def _check_no_control_chars(value: str) -> None:
    for char in value:
        if ord(char) < 0x20 or ord(char) == 0x7F:
            raise InvalidPathSegmentError(
                f"invalid path segment {value!r}: "
                "must not contain control characters"
            )


def path_segment(value: Any) -> str:
    """Return `value` percent-encoded for use as ONE path segment.

    Raises InvalidPathSegmentError when the value is not a string (or
    int), is empty, is a dot segment ("." or ".."), or contains a character that
    would add a segment, start a query or fragment, or carry an encoding a
    server might decode into one of those (/ \\ ? # %), or a control
    character.
    """
    value = _as_text(value)
    _check_not_dot_or_empty(value)
    if any(char in _FORBIDDEN_SEGMENT_CHARS for char in value):
        raise InvalidPathSegmentError(
            f"invalid path segment {value!r}: must not contain / \\ ? # or %"
        )
    _check_no_control_chars(value)
    return percent_encode(value)


def free_form_path_segment(value: Any) -> str:
    """Like `path_segment`, for free-form values such as transaction
    references: "/", "%", "?", "#" and "\\" are percent-encoded rather than
    rejected. Still rejected: empty values, control characters, and any
    value that has a "." or ".." segment once FULLY percent-decoded — so
    "..", "../x", "%2e%2e%2fsecret" and "%252e%252e" are all refused, even
    behind a proxy and server that each decode once."""
    value = _as_text(value)
    _check_not_dot_or_empty(value)
    _check_no_control_chars(value)
    if has_dot_segment(value):
        raise InvalidPathSegmentError(
            f"invalid path segment {value!r}: "
            "must not contain '.' or '..' segments, encoded or not"
        )
    return percent_encode(value)


def indicator_path_segment(value: Any) -> str:
    """Path segment for balance indicators and currencies.

    Core's `balances/indicator/:indicator/currency/:currency` route matches
    on the DECODED path, so an indicator with "/" (even as "%2F") can never
    be looked up there — Core answers 404 — and it is rejected here with a
    400 instead. Every other character Core accepts at creation ("%", "?",
    "#", "\\", ...) is percent-encoded and reaches Core intact. Otherwise
    the same rules as `free_form_path_segment`."""
    value = _as_text(value)
    if "/" in value:
        raise InvalidPathSegmentError(
            f"invalid path segment {value!r}: must not contain /"
        )
    return free_form_path_segment(value)


def endpoint_path(template: str, *segments: Any) -> str:
    """Fill each `{}` in `template` with a validated, escaped path segment
    (see `path_segment`). Raises InvalidPathSegmentError on the first bad
    segment."""
    return template.format(*(path_segment(segment) for segment in segments))


_MAX_DECODE_ROUNDS = 8


def _fully_decoded(path: str) -> Optional[str]:
    """Percent-decode `path` until it stops changing. None when it is still
    changing after _MAX_DECODE_ROUNDS (treated as unsafe by callers)."""
    for _ in range(_MAX_DECODE_ROUNDS):
        decoded = unquote(path)
        if decoded == path:
            return path
        path = decoded
    return None


def has_dot_segment(path: str) -> bool:
    """True when `path`, percent-decoded until stable, contains a "." or
    ".." segment.

    Decoding repeatedly means "%2e%2e" and the double-encoded "%252e%252e"
    are caught the same way as "..", so a proxy and an upstream server that
    each decode once still cannot resolve a hidden dot segment. Both "/"
    and "\\" count as separators, since some servers treat them alike. A
    path that has not stabilised after several rounds counts as unsafe."""
    decoded = _fully_decoded(path)
    if decoded is None:
        return True
    decoded = decoded.replace("\\", "/")
    return any(segment in (".", "..") for segment in decoded.split("/"))

"""Percent-encoding and validation for URL path segments and query values.

Every caller-supplied value that becomes part of a request path must go
through `path_segment` (or `endpoint_path`), so an id like "../backup" or
"%2e%2e/secret" cannot change which endpoint the client's API key is sent
to. `percent_encode` alone is not enough for paths: it keeps "." unescaped,
so "." and ".." survive it as dot segments.
"""

from __future__ import annotations

from typing import Any
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
    int), is
    empty, is a dot segment ("." or ".."), or contains a character that
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
    references: "/" and "%" are escaped rather than rejected, but empty
    values, "." / "..", and control characters are still rejected (escaping
    leaves "." and ".." unchanged)."""
    value = _as_text(value)
    _check_not_dot_or_empty(value)
    _check_no_control_chars(value)
    return percent_encode(value)


def endpoint_path(template: str, *segments: Any) -> str:
    """Fill each `{}` in `template` with a validated, escaped path segment
    (see `path_segment`). Raises InvalidPathSegmentError on the first bad
    segment."""
    return template.format(*(path_segment(segment) for segment in segments))


def has_dot_segment(path: str) -> bool:
    """True when the percent-decoded `path` contains a "." or ".." segment.

    Decoding first means "%2e%2e" is caught the same way as "..". Both "/"
    and "\\" count as separators, since some servers treat them alike."""
    decoded = unquote(path).replace("\\", "/")
    return any(segment in (".", "..") for segment in decoded.split("/"))

"""Validator package.

Validators return ``str | None`` — None means valid; a non-None value is the
exact error message that callers surface in a 400 response. They never raise
for message-producing failures, though a few raise TypeError/AttributeError
for structurally malformed inputs, which callers convert into a 500 response.
"""

from .common import is_valid_meta_data

__all__ = ["is_valid_meta_data"]

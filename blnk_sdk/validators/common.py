"""Helpers shared across the validator modules."""

from __future__ import annotations

from typing import Any


def is_valid_meta_data(meta: Any) -> bool:
    """Checks that meta is a structured value: any object — lists included —
    passes; None and primitives (str/number/bool) fail. bool is listed
    explicitly because Python bools are ints."""
    return meta is not None and not isinstance(meta, (str, int, float, bool))

"""Typed DTO package. Request/response types are dataclasses using the DTO
mixin from blnk_sdk.types.base (to_dict omits None fields; from_dict is
tolerant of missing/extra keys). Wire field names stay snake_case."""

from .base import DTO

__all__ = ["DTO"]

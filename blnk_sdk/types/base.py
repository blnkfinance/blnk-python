"""DTO base mixin shared by all typed request/response dataclasses."""

from __future__ import annotations

import dataclasses
from typing import Any, Dict


def _convert(value: Any) -> Any:
    if isinstance(value, DTO):
        return value.to_dict()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        out = {}
        for f in dataclasses.fields(value):
            v = getattr(value, f.name)
            if v is None:
                continue
            out[f.name] = _convert(v)
        return out
    if isinstance(value, dict):
        # Plain dicts keep None values (serialized as JSON null); only DTO
        # fields treat None as "not provided".
        return {k: _convert(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_convert(item) for item in value]
    return value


class DTO:
    """Mixin for @dataclass DTOs.

    - to_dict(): dict with insertion (declaration) key order; None-valued
      fields are OMITTED entirely, so an unset optional never appears on the
      wire; nested DTOs/lists/dicts converted recursively; datetimes left as
      datetime (date FIELDS must be pre-serialized by the owning module's
      serializer).
    - from_dict(data): tolerant — unknown keys ignored, missing keys become
      None (even for otherwise-required fields).
    """

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for f in dataclasses.fields(self):
            value = getattr(self, f.name)
            if value is None:
                continue
            out[f.name] = _convert(value)
        return out

    @classmethod
    def from_dict(cls, data: Any):
        if not isinstance(data, dict):
            data = {}
        kwargs: Dict[str, Any] = {}
        for f in dataclasses.fields(cls):
            if f.name in data:
                kwargs[f.name] = data[f.name]
            elif (
                f.default is dataclasses.MISSING
                and f.default_factory is dataclasses.MISSING
            ):
                kwargs[f.name] = None
        return cls(**kwargs)

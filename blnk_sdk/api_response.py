"""ApiResponse — the value type returned by every endpoint method."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .errors import BlnkApiErrorDetail


@dataclass
class ApiResponse:
    """Return value of every endpoint method; never raised, always returned.

    `error` is None unless a structured error was parsed; `to_dict()` omits
    the `error` key entirely when it is falsy (the key is absent, not None).
    """

    status: int
    message: str
    data: Any
    error: Optional[BlnkApiErrorDetail] = None

    def to_dict(self) -> dict:
        out: dict = {"status": self.status, "message": self.message, "data": self.data}
        if self.error:
            out["error"] = (
                self.error.to_dict() if hasattr(self.error, "to_dict") else self.error
            )
        return out

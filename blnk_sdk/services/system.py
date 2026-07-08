"""The System service — health checks."""

from __future__ import annotations

from typing import Any, Callable

from ..logger import handle_error


class System:
    def __init__(
        self,
        request: Callable[..., Any],
        logger: Any,
        format_response: Callable[..., Any],
    ) -> None:
        self._request = request
        self._logger = logger
        self._format_response = format_response

    def health(self) -> Any:
        """GET health — Core payload is `{"status": "UP"}` on data."""
        try:
            return self._request("health", None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "health")

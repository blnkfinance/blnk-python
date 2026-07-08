"""Logging helpers: the default CustomLogger, the plain console fallback, and
the handle_error response mapper."""

from __future__ import annotations

import sys
from typing import Any, Callable

from .api_response import ApiResponse
from .safe_log_meta import safe_log_meta


class CustomLogger:
    """Default SDK logger injected by blnk_init when options.logger is None.

    Prefixes are exact: `INFO: ` / `ERROR: ` / `DEBUG: `. info/debug write to
    stdout, error writes to stderr.
    """

    def info(self, message: str, *meta: Any) -> None:
        print(f"INFO: {message}", *meta)

    def error(self, message: str, *meta: Any) -> None:
        print(f"ERROR: {message}", *meta, file=sys.stderr)

    def debug(self, message: str, *meta: Any) -> None:
        print(f"DEBUG: {message}", *meta)


class _ConsoleLogger:
    """Prefix-free logger used as the fallback when Blnk is constructed
    directly with no logger."""

    def info(self, message: str, *meta: Any) -> None:
        print(message, *meta)

    def error(self, message: str, *meta: Any) -> None:
        print(message, *meta, file=sys.stderr)

    def debug(self, message: str, *meta: Any) -> None:
        print(message, *meta)


console = _ConsoleLogger()


def handle_error(
    error: Any,
    logger: Any,
    format_response: Callable[..., ApiResponse],
    fn_name: str,
) -> ApiResponse:
    """Convert an unexpected error into a 500 ApiResponse. Never raises.

    `fn_name` is a stable identifier logged verbatim as part of the observable
    log output (the core client passes "request"; services pass their
    reporting name, e.g. "createMatchingRule"). Some services intentionally
    report one method's errors under another method's name (BalanceMonitors
    .list logs under "get"), and callers may match on these exact strings.
    """
    logger.error(fn_name, *safe_log_meta(error))
    if isinstance(error, Exception):
        return format_response(500, str(error), None)
    return format_response(500, "An unknown error occurred.", None)

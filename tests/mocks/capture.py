"""Call-recording wrappers used to assert on collaborator invocations."""

from __future__ import annotations

from typing import Any, Callable, List, Optional


class CapturedCall:
    def __init__(self, args: tuple, kwargs: dict) -> None:
        self.args = args
        self.kwargs = kwargs
        self.result: Any = None


class CapturingCallable:
    """Wraps any callable; records each call's positional/keyword args (and the
    return value) in `.calls`, then delegates."""

    def __init__(self, fn: Callable[..., Any]) -> None:
        self._fn = fn
        self.calls: List[CapturedCall] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        call = CapturedCall(args, kwargs)
        self.calls.append(call)
        call.result = self._fn(*args, **kwargs)
        return call.result


def capture_fn(fn: Callable[..., Any]) -> CapturingCallable:
    return CapturingCallable(fn)


class CapturingRequest:
    """Recorder for the client's request seam: records every
    `(endpoint, data, method, headers)` tuple in `.calls` and delegates to
    the wrapped request function."""

    def __init__(self, inner: Callable[..., Any]) -> None:
        self._inner = inner
        self.calls: List[tuple] = []

    def __call__(
        self,
        endpoint: str,
        data: Any,
        method: str,
        header_options: Optional[dict] = None,
    ) -> Any:
        self.calls.append((endpoint, data, method, header_options))
        return self._inner(endpoint, data, method, header_options)

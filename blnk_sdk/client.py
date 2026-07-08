"""Core Blnk client.

Blnk._request is the single HTTP seam. Each service receives a request
callable `(endpoint, data, method, header_options=None) -> ApiResponse`
(a bound Blnk._request), so services never talk to the transport directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Union

from .constants import (
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY_MS,
    DEFAULT_TIMEOUT_MS,
)
from .api_response import ApiResponse
from .errors import BlnkServiceError, BlnkTimeoutError, parse_blnk_api_error_body
from .http_client import format_response, read_response_json_body
from .coercion import format_number, is_truthy
from .logger import CustomLogger, console, handle_error
from .multipart import is_multipart_body
from .request_retry import (
    is_retryable_http_method,
    is_retryable_http_status,
    is_retryable_transport_error,
    normalize_retry_count,
    normalize_retry_delay_ms,
    retry_delay_for_attempt,
    sleep_ms,
)
from .safe_log_meta import redact_sensitive_log_meta, safe_log_meta
from .serialization import compact_json_dumps
from .transport import RequestsTransport, TransportRequest

Number = Union[int, float]


@dataclass
class BlnkClientOptions:
    """Client options. None means "not provided".

    Note: the Blnk constructor and blnk_init mutate this instance in place
    (trailing slash appended to base_url; default logger assigned), so the
    normalized values are observable on the object the caller passed in.
    """

    base_url: str = ""
    timeout: Optional[Number] = None
    retry_count: Optional[Number] = None
    retry_delay_ms: Optional[Number] = None
    logger: Any = None


class Blnk:
    """Core Blnk client. Endpoint methods NEVER raise for request/validation
    failures — they return ApiResponse values. Only the constructor
    (ValueError) and unknown-service access (BlnkServiceError) raise."""

    def __init__(
        self,
        api_key: str,
        options: BlnkClientOptions,
        services: Dict[str, type],
        format_response_fn: Callable[..., ApiResponse],
        third_party_request: Callable[..., Any],
    ) -> None:
        if not options.base_url:
            raise ValueError("base_url is required for self-hosted Blnk SDK.")

        # Mutates the caller's options object in place; the normalized
        # base URL is visible to the caller afterwards.
        if not options.base_url.endswith("/"):
            options.base_url = options.base_url + "/"

        self._api_key = api_key
        # Options are stored without the logger; defaults are merged, then the
        # retry options are normalized. `timeout` is stored as provided.
        self._options: Dict[str, Any] = {
            "base_url": options.base_url,
            "timeout": options.timeout
            if options.timeout is not None
            else DEFAULT_TIMEOUT_MS,
            "retry_count": options.retry_count
            if options.retry_count is not None
            else DEFAULT_RETRY_COUNT,
            "retry_delay_ms": options.retry_delay_ms
            if options.retry_delay_ms is not None
            else DEFAULT_RETRY_DELAY_MS,
        }
        self._options["retry_count"] = normalize_retry_count(
            self._options["retry_count"]
        )
        self._options["retry_delay_ms"] = normalize_retry_delay_ms(
            self._options["retry_delay_ms"]
        )

        # No logger provided -> fall back to the plain console logger.
        self._logger = options.logger if options.logger is not None else console
        self._services = services
        self._service_instances: Dict[str, Any] = {}
        self._format_response = format_response_fn
        self._third_party_request = third_party_request

    # ------------------------------------------------------------------ #
    # lifecycle

    def close(self) -> None:
        close_fn = getattr(self._third_party_request, "close", None)
        if callable(close_fn):
            close_fn()

    def __enter__(self) -> "Blnk":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self.close()
        return False

    # ------------------------------------------------------------------ #
    # the single HTTP seam

    def _request(
        self,
        endpoint: str,
        data: Any,
        method: str,
        header_options: Optional[Dict[str, str]] = None,
    ) -> ApiResponse:
        """Perform one logical request (including retries). Never raises —
        every outcome, including transport failures, becomes an ApiResponse."""
        timeout_ms = self._options.get("timeout")
        if timeout_ms is None:
            timeout_ms = DEFAULT_TIMEOUT_MS
        max_attempts = normalize_retry_count(self._options.get("retry_count"))
        retry_delay_ms = normalize_retry_delay_ms(self._options.get("retry_delay_ms"))

        body: Any = None
        form_data_headers: Dict[str, str] = {}
        # Falsy payloads (None, "", 0, False, NaN) send no body at all;
        # an empty dict counts as a payload and serializes to "{}".
        if is_truthy(data):
            if is_multipart_body(data):
                body = data
                form_data_headers.update(data.get_headers())
            else:
                body = compact_json_dumps(data)

        is_multipart = is_multipart_body(data)
        can_retry = (
            not is_multipart
            and max_attempts > 1
            and is_retryable_http_method(method)
        )

        # Header precedence (later wins): X-Blnk-Key (only when api_key != ""),
        # JSON content-type (only when not multipart), caller header_options,
        # multipart form headers.
        headers: Dict[str, str] = {}
        if self._api_key != "":
            headers["X-Blnk-Key"] = self._api_key
        if not is_multipart:
            headers["content-type"] = "application/json"
        if header_options:
            headers.update(header_options)
        headers.update(form_data_headers)

        url = f"{self._options['base_url']}{endpoint}"

        attempt = 0
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                delay_ms = retry_delay_for_attempt(attempt - 1, retry_delay_ms)
                self._logger.info(
                    f"Retrying request to {endpoint}",
                    {
                        "attempt": attempt,
                        "maxAttempts": max_attempts,
                        "delayMs": delay_ms,
                    },
                )
                sleep_ms(delay_ms)

            init = TransportRequest(
                method=method, headers=headers, body=body, timeout_ms=timeout_ms
            )

            try:
                response = self._third_party_request(url, init)

                if not getattr(response, "ok", False):
                    error_result: Any = None
                    try:
                        error_result = read_response_json_body(response)
                    except Exception:
                        error_result = None
                    structured_error = parse_blnk_api_error_body(error_result)
                    status = response.status

                    if (
                        can_retry
                        and is_retryable_http_status(status)
                        and attempt < max_attempts
                    ):
                        self._logger.info(
                            f"Request to {endpoint} failed with status {status}; retrying."
                        )
                        continue

                    self._logger.error(
                        f"Request to {endpoint} failed with status {status}."
                    )
                    message = (
                        structured_error.message
                        if structured_error is not None
                        else getattr(response, "status_text", "")
                    )
                    return self._format_response(
                        status, message, error_result, structured_error
                    )

                if response.status in (204, 205):
                    return self._format_response(response.status, "Success", None)

                # A JSON parse failure on a success response is deliberately
                # not caught here — it falls into the except below and is
                # reported as a 500.
                json_response = read_response_json_body(response)
                return self._format_response(response.status, "Success", json_response)
            except BlnkTimeoutError:
                # Timeouts are never retried; they map straight to a
                # synthetic 408 response.
                self._logger.error(
                    "Request timed out",
                    redact_sensitive_log_meta(
                        {"endpoint": endpoint, "timeoutMs": timeout_ms}
                    ),
                )
                return self._format_response(
                    408,
                    f"Request timed out after {format_number(timeout_ms)}ms",
                    None,
                )
            except Exception as error:
                if (
                    can_retry
                    and is_retryable_transport_error(error)
                    and attempt < max_attempts
                ):
                    self._logger.info(
                        f"Request to {endpoint} failed; retrying.",
                        *safe_log_meta(error),
                    )
                    continue

                self._logger.error(
                    "Request failed",
                    redact_sensitive_log_meta({"endpoint": endpoint, "error": error}),
                )
                return handle_error(
                    error, self._logger, self._format_response, "request"
                )

        # Unreachable in practice (the final attempt always returns above);
        # kept as a defensive terminal response.
        return self._format_response(
            500,
            f"Request failed after {format_number(max_attempts)} attempts",
            None,
        )

    # ------------------------------------------------------------------ #
    # service registry

    def _get_service(self, service_name: str) -> Any:
        if not self._services.get(service_name):
            raise BlnkServiceError(f"Service {service_name} is not registered")

        if not self._service_instances.get(service_name):
            self._service_instances[service_name] = self._services[service_name](
                self._request, self._logger, self._format_response
            )

        return self._service_instances[service_name]

    @property
    def ledgers(self) -> Any:
        return self._get_service("Ledgers")

    @property
    def ledger_balances(self) -> Any:
        return self._get_service("LedgerBalances")

    @property
    def transactions(self) -> Any:
        return self._get_service("Transactions")

    @property
    def balance_monitor(self) -> Any:
        return self._get_service("BalanceMonitor")

    @property
    def reconciliation(self) -> Any:
        return self._get_service("Reconciliation")

    @property
    def search(self) -> Any:
        return self._get_service("Search")

    @property
    def identity(self) -> Any:
        return self._get_service("Identity")

    @property
    def system(self) -> Any:
        return self._get_service("System")

    @property
    def metadata(self) -> Any:
        return self._get_service("Metadata")

    @property
    def hooks(self) -> Any:
        return self._get_service("Hooks")

    @property
    def api_keys(self) -> Any:
        return self._get_service("ApiKeys")

    # NOTE: the API key is intentionally not exposed as a property.

    @classmethod
    def init(cls, api_key: str, options: BlnkClientOptions) -> "Blnk":
        return blnk_init(api_key, options)


def blnk_init(api_key: str, options: BlnkClientOptions) -> Blnk:
    """Create a fully wired Blnk client.

    Injects CustomLogger when options.logger is None (mutating the caller's
    options object) and wires the default services map, the response
    formatter, and the requests-backed transport.
    """
    if options.logger is None:
        options.logger = CustomLogger()

    from .services import default_services_map

    return Blnk(
        api_key,
        options,
        default_services_map(),
        format_response,
        RequestsTransport(),
    )

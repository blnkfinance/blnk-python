"""Unit tests for the core Blnk client: construction, auth headers,
request dispatch, multipart bodies, timeouts, retries, and error shaping.

The suite deliberately shares ONE options object across all tests (the
module-level OPTIONS instance); the client normalizes base_url in place,
so after the first construction its base_url is already
"http://mock-api.com/".

Several test endpoints keep their leading slash ("/test-endpoint", ...)
on purpose: the client does NOT normalize the resulting double slash.
"""

from __future__ import annotations

import dataclasses
import json
import re

import pytest

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.client import Blnk, BlnkClientOptions
from blnk_sdk.errors import BlnkApiErrorDetail, BlnkTimeoutError
from blnk_sdk.http_client import format_response
from blnk_sdk.multipart import MultipartBody
from blnk_sdk.services.reconciliation import Reconciliation
from tests.mocks.blnk_client_mocks import (
    capture_fn,
    create_mock_blnk_client_options,
    create_mock_services,
)
from tests.mocks.transport_mock import transport_fail_mock, transport_mock, make_response
from tests.mocks.stream_test_utils import read_stream_body

OPTIONS = create_mock_blnk_client_options()  # deliberately shared by the whole suite
MOCK_SERVICES = create_mock_services()
API_KEY = "123455"


@pytest.fixture
def blnk() -> Blnk:
    return Blnk(API_KEY, OPTIONS, MOCK_SERVICES, format_response, transport_mock)


def test_init_blnk_client(blnk: Blnk) -> None:
    assert blnk._api_key == API_KEY


def test_should_throw_error_when_base_url_is_missing_in_options() -> None:
    with pytest.raises(ValueError) as excinfo:
        Blnk(API_KEY, BlnkClientOptions(), MOCK_SERVICES, format_response, transport_mock)
    assert str(excinfo.value) == "base_url is required for self-hosted Blnk SDK."


def test_omits_x_blnk_key_for_local_unauthenticated_mode() -> None:
    captured_transport = capture_fn(transport_mock)
    local_blnk = Blnk("", OPTIONS, MOCK_SERVICES, format_response, captured_transport)

    local_blnk._request("health", {}, "GET")

    init = captured_transport.calls[0].args[1]
    assert "X-Blnk-Key" not in init.headers


def test_sends_x_blnk_key_when_api_key_is_set() -> None:
    captured_transport = capture_fn(transport_mock)
    authed_blnk = Blnk(API_KEY, OPTIONS, MOCK_SERVICES, format_response, captured_transport)

    authed_blnk._request("health", {}, "GET")

    init = captured_transport.calls[0].args[1]
    assert init.headers["X-Blnk-Key"] == API_KEY


def test_does_not_expose_public_get_api_key_getter(blnk: Blnk) -> None:
    assert not hasattr(blnk, "get_api_key")
    assert not hasattr(blnk, "getApiKey")
    assert not hasattr(blnk, "api_key")


def test_constructor_sets_api_key_options_logger_services_and_format_response(
    blnk: Blnk,
) -> None:
    assert blnk._api_key == API_KEY, "apiKey is set correctly"
    assert blnk._options["timeout"] == 5000, "timeout is set correctly"
    assert blnk._logger is OPTIONS.logger, "logger is set correctly"
    assert blnk._services is MOCK_SERVICES, "services are set correctly"
    assert blnk._format_response is format_response, "formatResponse is set correctly"


def _created_201_transport():
    return capture_fn(
        lambda _url, _init: make_response(
            ok=True,
            status=201,
            status_text="Created",
            json_body={"upload_id": "upl_test"},
        )
    )


def test_request_converts_multipart_form_data_for_the_transport() -> None:
    form_data = MultipartBody()
    form_data.append("source", "stripe")
    form_data.append("file", b"a,b,c", filename="test.csv")

    captured_transport = _created_201_transport()
    form_blnk = Blnk(API_KEY, OPTIONS, MOCK_SERVICES, format_response, captured_transport)

    form_blnk._request("reconciliation/upload", form_data, "POST")

    init = captured_transport.calls[0].args[1]
    assert isinstance(init.body, MultipartBody)
    payload = read_stream_body(init.body)
    assert re.search(r"a,b,c", payload)
    assert re.search(r"multipart/form-data", init.headers["content-type"])
    assert not re.search(r"application/json", init.headers["content-type"])


def test_request_converts_stream_backed_multipart_form_data_for_the_transport(
    tmp_path,
) -> None:
    file_path = tmp_path / "upload.csv"
    file_path.write_text("amount,ref\n100,abc")

    form_data = MultipartBody()
    form_data.append("source", "stripe")
    form_data.append("file", open(file_path, "rb"), filename="upload.csv")

    captured_transport = _created_201_transport()
    form_blnk = Blnk(API_KEY, OPTIONS, MOCK_SERVICES, format_response, captured_transport)

    form_blnk._request("reconciliation/upload", form_data, "POST")

    init = captured_transport.calls[0].args[1]
    assert isinstance(init.body, MultipartBody)
    payload = read_stream_body(init.body)
    assert re.search(r"amount,ref", payload)
    assert re.search(r"100,abc", payload)


def test_reconciliation_upload_sends_stream_multipart_body_through_transport(
    tmp_path,
) -> None:
    file_path = tmp_path / "upload.csv"
    file_path.write_text("amount,ref\n200,xyz")

    captured_transport = _created_201_transport()
    upload_blnk = Blnk(
        API_KEY,
        OPTIONS,
        {**MOCK_SERVICES, "Reconciliation": Reconciliation},
        format_response,
        captured_transport,
    )

    response = upload_blnk.reconciliation.upload(str(file_path), "stripe")

    assert response.status == 201
    init = captured_transport.calls[0].args[1]
    assert isinstance(init.body, MultipartBody)
    payload = read_stream_body(init.body)
    assert re.search(r"stripe", payload)
    assert re.search(r"200,xyz", payload)


def test_returns_success_for_204_no_content_without_parsing_json() -> None:
    def no_content_transport(_url, _init):
        return make_response(
            ok=True,
            status=204,
            status_text="No Content",
            json_raises=ValueError("Unexpected end of JSON input"),
            text_body="",
        )

    no_content_blnk = Blnk(
        API_KEY, OPTIONS, MOCK_SERVICES, format_response, no_content_transport
    )

    response = no_content_blnk._request("api-keys/api_key_test_123", None, "DELETE")

    assert response.status == 204
    assert response.message == "Success"
    assert response.data is None


def test_returns_success_for_200_ok_with_empty_delete_body() -> None:
    def empty_body_transport(_url, _init):
        return make_response(
            ok=True,
            status=200,
            status_text="OK",
            json_raises=ValueError("Unexpected end of JSON input"),
            text_body="",
        )

    empty_body_blnk = Blnk(
        API_KEY, OPTIONS, MOCK_SERVICES, format_response, empty_body_transport
    )

    response = empty_body_blnk._request("identities/idt_test_123", None, "DELETE")

    assert response.status == 200
    assert response.message == "Success"
    assert response.data is None


def test_attaches_error_detail_code_on_409_conflict() -> None:
    body = {
        "error": "duplicate transaction reference",
        "error_detail": {
            "code": "TXN_DUPLICATE_REFERENCE",
            "message": "duplicate transaction reference",
        },
    }

    def conflict_transport(_url, _init):
        return make_response(
            ok=False,
            status=409,
            status_text="Conflict",
            json_body=body,
            text_body=json.dumps(body),
        )

    conflict_blnk = Blnk(
        API_KEY, OPTIONS, MOCK_SERVICES, format_response, conflict_transport
    )

    result = conflict_blnk._request("transactions", {"reference": "dup_ref"}, "POST")

    assert result.status == 409
    assert result.error == BlnkApiErrorDetail(
        code="TXN_DUPLICATE_REFERENCE", message="duplicate transaction reference"
    )


def test_attaches_error_detail_code_on_423_locked() -> None:
    body = {
        "error": "resource locked",
        "error_detail": {"code": "GEN_LOCKED", "message": "resource locked"},
    }

    def locked_transport(_url, _init):
        return make_response(
            ok=False,
            status=423,
            status_text="Locked",
            json_body=body,
            text_body=json.dumps(body),
        )

    locked_blnk = Blnk(API_KEY, OPTIONS, MOCK_SERVICES, format_response, locked_transport)

    result = locked_blnk._request("balances/bln_test", {}, "PUT")

    assert result.status == 423
    assert result.error == BlnkApiErrorDetail(
        code="GEN_LOCKED", message="resource locked"
    )


def test_request_passes_timeout_to_the_transport() -> None:
    # The configured timeout reaches the transport as a per-attempt timeout_ms.
    captured_transport = capture_fn(
        lambda _url, _init: make_response(
            ok=True, status=200, status_text="OK", json_body={"message": "Success"}
        )
    )
    signal_blnk = Blnk(API_KEY, OPTIONS, MOCK_SERVICES, format_response, captured_transport)

    signal_blnk._request("/test", {"foo": "bar"}, "POST")

    init = captured_transport.calls[0].args[1]
    assert init.timeout_ms == 5000


def test_request_returns_408_when_transport_aborts_immediately() -> None:
    # Note: ANY timeout error from the transport yields the 408 response, even
    # when it did not come from the timeout timer.
    def aborting_transport(_url, _init):
        raise BlnkTimeoutError("The operation was aborted.")

    abort_blnk = Blnk(API_KEY, OPTIONS, MOCK_SERVICES, format_response, aborting_transport)

    result = abort_blnk._request("/slow", {"foo": "bar"}, "POST")

    assert result.status == 408
    assert re.search(r"timed out", result.message)
    assert result.message == "Request timed out after 5000ms"


def test_request_returns_408_when_transport_aborts_timeout() -> None:
    def aborting_transport(_url, init):
        assert init.timeout_ms == 10
        raise BlnkTimeoutError("The operation was aborted.")

    timeout_blnk = Blnk(
        API_KEY,
        dataclasses.replace(OPTIONS, timeout=10),
        MOCK_SERVICES,
        format_response,
        aborting_transport,
    )

    result = timeout_blnk._request("/slow", {"foo": "bar"}, "POST")

    assert result.status == 408
    assert re.search(r"timed out", result.message)
    assert result.message == "Request timed out after 10ms"


def test_request_method_should_make_successful_post_request_and_return_formatted_response(
    blnk: Blnk,
) -> None:
    result = blnk._request("/test-endpoint", {"foo": "bar"}, "POST")

    assert result == ApiResponse(
        status=200, message="Success", data={"message": "Success"}
    ), "Returns the expected ApiResponse"
    assert "error" not in result.to_dict()


def test_request_method_should_make_failed_request_and_return_formatted_response() -> None:
    bad_blnk_request = Blnk(
        API_KEY, OPTIONS, MOCK_SERVICES, format_response, transport_fail_mock
    )
    result = bad_blnk_request._request("/test-endpoint", {"foo": "bar"}, "POST")

    # Note: the message comes from the response status text ("Failed"); data is
    # the parsed body, and NO error key is attached.
    assert result == ApiResponse(
        status=500, message="Failed", data={"message": "Failed"}
    ), "Returns the expected ApiResponse"
    assert "error" not in result.to_dict()


def test_defaults_client_timeout_and_retry_options() -> None:
    default_blnk = Blnk(
        API_KEY,
        BlnkClientOptions(base_url="http://mock-api.com"),
        MOCK_SERVICES,
        format_response,
        transport_mock,
    )
    assert default_blnk._options["timeout"] == 10000
    assert default_blnk._options["retry_count"] == 1
    assert default_blnk._options["retry_delay_ms"] == 2000


def test_request_attaches_structured_error_from_error_detail() -> None:
    # json-only mock (no text fn) -> json() fallback path.
    def error_transport(_url, _init):
        return make_response(
            ok=False,
            status=404,
            status_text="Not Found",
            json_body={
                "error": "ledger not found",
                "error_detail": {
                    "code": "LGR_NOT_FOUND",
                    "message": "ledger not found",
                },
            },
        )

    error_blnk = Blnk(API_KEY, OPTIONS, MOCK_SERVICES, format_response, error_transport)

    result = error_blnk._request("ledgers/missing", {}, "GET")

    assert result.status == 404
    assert result.error == BlnkApiErrorDetail(
        code="LGR_NOT_FOUND", message="ledger not found"
    )


def test_request_retries_retryable_5xx_get_responses() -> None:
    calls = 0

    def retry_transport(_url, _init):
        nonlocal calls
        calls += 1
        if calls == 1:
            return make_response(
                ok=False,
                status=503,
                status_text="Service Unavailable",
                json_body={"error": "temporarily unavailable"},
            )
        return make_response(
            ok=True, status=200, status_text="OK", json_body={"message": "Success"}
        )

    retry_blnk = Blnk(
        API_KEY,
        dataclasses.replace(OPTIONS, retry_count=3, retry_delay_ms=1),
        MOCK_SERVICES,
        format_response,
        retry_transport,
    )

    result = retry_blnk._request("/retry-me", {}, "GET")

    assert calls == 2
    assert result.status == 200


def test_request_does_not_retry_mutating_post_on_5xx() -> None:
    calls = 0

    def post_transport(_url, _init):
        nonlocal calls
        calls += 1
        return make_response(
            ok=False,
            status=503,
            status_text="Service Unavailable",
            json_body={
                "error": "temporarily unavailable",
                "error_detail": {
                    "code": "GEN_INTERNAL",
                    "message": "temporarily unavailable",
                },
            },
        )

    post_blnk = Blnk(
        API_KEY,
        dataclasses.replace(OPTIONS, retry_count=3, retry_delay_ms=1),
        MOCK_SERVICES,
        format_response,
        post_transport,
    )

    result = post_blnk._request("transactions", {"amount": 100}, "POST")

    assert calls == 1
    assert result.status == 503
    assert result.error is not None
    assert result.error.code == "GEN_INTERNAL"


def test_request_does_not_retry_timeouts_even_when_retry_count_gt_1() -> None:
    calls = 0

    def timeout_transport(_url, _init):
        nonlocal calls
        calls += 1
        raise BlnkTimeoutError("The operation was aborted.")

    timeout_blnk = Blnk(
        API_KEY,
        dataclasses.replace(OPTIONS, timeout=10, retry_count=3, retry_delay_ms=1),
        MOCK_SERVICES,
        format_response,
        timeout_transport,
    )

    result = timeout_blnk._request("/slow", {}, "GET")

    assert calls == 1
    assert result.status == 408


def test_request_returns_structured_error_after_get_retries_are_exhausted() -> None:
    calls = 0

    def failing_transport(_url, _init):
        nonlocal calls
        calls += 1
        return make_response(
            ok=False,
            status=503,
            status_text="Service Unavailable",
            json_body={
                "error": "still unavailable",
                "error_detail": {
                    "code": "GEN_INTERNAL",
                    "message": "still unavailable",
                },
            },
        )

    exhausted_blnk = Blnk(
        API_KEY,
        dataclasses.replace(OPTIONS, retry_count=2, retry_delay_ms=1),
        MOCK_SERVICES,
        format_response,
        failing_transport,
    )

    result = exhausted_blnk._request("/unstable", {}, "GET")

    assert calls == 2
    assert result.status == 503
    assert result.error == BlnkApiErrorDetail(
        code="GEN_INTERNAL", message="still unavailable"
    )


def test_retry_count_below_1_is_normalized_to_1() -> None:
    normalized_blnk = Blnk(
        API_KEY,
        BlnkClientOptions(base_url="http://mock-api.com", retry_count=0),
        MOCK_SERVICES,
        format_response,
        transport_mock,
    )

    assert normalized_blnk._options["retry_count"] == 1


def test_non_finite_retry_options_are_normalized_on_the_client() -> None:
    normalized_blnk = Blnk(
        API_KEY,
        BlnkClientOptions(
            base_url="http://mock-api.com",
            retry_count=float("nan"),
            retry_delay_ms=float("inf"),
        ),
        MOCK_SERVICES,
        format_response,
        transport_mock,
    )

    assert normalized_blnk._options["retry_count"] == 1
    assert normalized_blnk._options["retry_delay_ms"] == 2000


def test_request_does_not_retry_4xx_responses() -> None:
    calls = 0

    def client_error_transport(_url, _init):
        nonlocal calls
        calls += 1
        return make_response(
            ok=False,
            status=400,
            status_text="Bad Request",
            json_body={
                "error": "bad request",
                "error_detail": {"code": "GEN_BAD_REQUEST", "message": "bad request"},
            },
        )

    no_retry_blnk = Blnk(
        API_KEY,
        dataclasses.replace(OPTIONS, retry_count=3, retry_delay_ms=1),
        MOCK_SERVICES,
        format_response,
        client_error_transport,
    )

    result = no_retry_blnk._request("/bad", {"foo": "bar"}, "POST")

    assert calls == 1
    assert result.status == 400
    assert result.error is not None
    assert result.error.code == "GEN_BAD_REQUEST"


def test_should_append_slash_to_base_url_if_it_is_not_set() -> None:
    options_without_base_url = dataclasses.replace(OPTIONS, base_url="base")
    blnk_without_base_url = Blnk(
        API_KEY, options_without_base_url, MOCK_SERVICES, format_response, transport_mock
    )
    assert blnk_without_base_url._options["base_url"] == "base/"
    # Note: the caller's options object is mutated in place.
    assert options_without_base_url.base_url == "base/"

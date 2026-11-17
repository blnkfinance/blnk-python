"""Path-injection tests against a real local HTTP server.

Every service method that puts a caller-supplied value into the request path
is called with hostile inputs. Each call must return an error response and
the server must receive NOTHING, on both a Core base URL and a Cloud Proxy
style `/proxy/` base. Valid ids must reach the server unchanged.

The server records the raw request target of every request it receives, so
these tests see what actually went over the wire (after the transport's own
URL normalization), not what the SDK meant to send.
"""

from __future__ import annotations

import http.client
import posixpath
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote

import pytest

from blnk_sdk import BlnkClientOptions, blnk_init


class _SilentLogger:
    def info(self, *args: Any) -> None:
        pass

    def error(self, *args: Any) -> None:
        pass

    def debug(self, *args: Any) -> None:
        pass


class _RecordingHandler(BaseHTTPRequestHandler):
    def _record(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self.server.received.append(  # type: ignore[attr-defined]
            (self.command, self.path, self.headers.get("X-Blnk-Key"))
        )
        body = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _record

    def log_message(self, *args: Any) -> None:
        pass


class _Server:
    def __init__(self) -> None:
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingHandler)
        self._httpd.received = []  # type: ignore[attr-defined]
        self.origin = f"http://127.0.0.1:{self._httpd.server_address[1]}"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    @property
    def received(self) -> list[tuple[str, str, Any]]:
        return self._httpd.received  # type: ignore[attr-defined]

    def clear(self) -> None:
        self.received.clear()

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


@pytest.fixture(scope="module")
def server() -> Iterator[_Server]:
    srv = _Server()
    yield srv
    srv.close()


# Base paths: direct Core, and a Cloud Proxy style base whose /proxy/ prefix
# must never be escaped.
BASES = ["/", "/proxy/"]


def _client(server: _Server, base: str) -> Any:
    return blnk_init(
        "test-key",
        BlnkClientOptions(
            base_url=server.origin + base,
            retry_count=1,
            logger=_SilentLogger(),
        ),
    )


# --------------------------------------------------------------------------- #
# Every method that puts a caller-supplied value into the path. Each entry is
# (name, call(client, value), expected path for value "ID_1" relative to the
# base). Payloads are valid, so the only thing that can stop a request is the
# path value.

MONITOR = {
    "balance_id": "bln_1",
    "condition": {
        "field": "debit_balance",
        "operator": ">",
        "value": 1,
        "precision": 100,
    },
}
MATCHER = {"name": "rule", "description": "d", "criteria": []}
HOOK = {
    "name": "hook",
    "url": "https://example.com/hook",
    "type": "PRE_TRANSACTION",
    "active": True,
    "timeout": 30,
    "retry_count": 3,
}
IDENTITY = {"identity_type": "individual", "first_name": "Ada"}

PATH_METHODS: list[tuple[str, Callable[[Any, Any], Any], str]] = [
    ("ledgers.get", lambda c, v: c.ledgers.get(v), "ledgers/ID_1"),
    ("ledgers.update", lambda c, v: c.ledgers.update(v, {"name": "n"}), "ledgers/ID_1"),
    ("ledger_balances.get", lambda c, v: c.ledger_balances.get(v), "balances/ID_1"),
    (
        "ledger_balances.get_by_indicator[indicator]",
        lambda c, v: c.ledger_balances.get_by_indicator(v, "USD"),
        "balances/indicator/ID_1/currency/USD",
    ),
    (
        "ledger_balances.get_by_indicator[currency]",
        lambda c, v: c.ledger_balances.get_by_indicator("@World", v),
        "balances/indicator/%40World/currency/ID_1",
    ),
    (
        "ledger_balances.update_identity",
        lambda c, v: c.ledger_balances.update_identity(v, {"identity_id": "idt_1"}),
        "balances/ID_1/identity",
    ),
    (
        "ledger_balances.get_at",
        lambda c, v: c.ledger_balances.get_at(v, {"timestamp": "2025-01-01T00:00:00Z"}),
        "balances/ID_1/at?timestamp=2025-01-01T00%3A00%3A00Z",
    ),
    (
        "ledger_balances.get_lineage",
        lambda c, v: c.ledger_balances.get_lineage(v),
        "balances/ID_1/lineage",
    ),
    (
        "transactions.update_status",
        lambda c, v: c.transactions.update_status(v, {"status": "commit"}),
        "transactions/inflight/ID_1",
    ),
    (
        "transactions.refund",
        lambda c, v: c.transactions.refund(v),
        "refund-transaction/ID_1",
    ),
    ("transactions.get", lambda c, v: c.transactions.get(v), "transactions/ID_1"),
    (
        "transactions.get_lineage",
        lambda c, v: c.transactions.get_lineage(v),
        "transactions/ID_1/lineage",
    ),
    (
        "balance_monitor.get",
        lambda c, v: c.balance_monitor.get(v),
        "balance-monitors/ID_1",
    ),
    (
        "balance_monitor.list_by_balance_id",
        lambda c, v: c.balance_monitor.list_by_balance_id(v),
        "balance-monitors/balances/ID_1",
    ),
    (
        "balance_monitor.update",
        lambda c, v: c.balance_monitor.update(v, MONITOR),
        "balance-monitors/ID_1",
    ),
    (
        "balance_monitor.delete",
        lambda c, v: c.balance_monitor.delete(v),
        "balance-monitors/ID_1",
    ),
    (
        "reconciliation.update_matching_rule",
        lambda c, v: c.reconciliation.update_matching_rule(v, MATCHER),
        "reconciliation/matching-rules/ID_1",
    ),
    (
        "reconciliation.delete_matching_rule",
        lambda c, v: c.reconciliation.delete_matching_rule(v),
        "reconciliation/matching-rules/ID_1",
    ),
    ("reconciliation.get", lambda c, v: c.reconciliation.get(v), "reconciliation/ID_1"),
    ("identity.get", lambda c, v: c.identity.get(v), "identities/ID_1"),
    ("identity.update", lambda c, v: c.identity.update(v, IDENTITY), "identities/ID_1"),
    ("identity.delete", lambda c, v: c.identity.delete(v), "identities/ID_1"),
    (
        "identity.get_tokenized_fields",
        lambda c, v: c.identity.get_tokenized_fields(v),
        "identities/ID_1/tokenized-fields",
    ),
    (
        "identity.tokenize_field[id]",
        lambda c, v: c.identity.tokenize_field(v, "first_name"),
        "identities/ID_1/tokenize/first_name",
    ),
    (
        "identity.tokenize_field[field]",
        lambda c, v: c.identity.tokenize_field("idt_1", v),
        "identities/idt_1/tokenize/ID_1",
    ),
    (
        "identity.tokenize",
        lambda c, v: c.identity.tokenize(v, {"fields": ["first_name"]}),
        "identities/ID_1/tokenize",
    ),
    (
        "identity.detokenize_field[id]",
        lambda c, v: c.identity.detokenize_field(v, "first_name"),
        "identities/ID_1/detokenize/first_name",
    ),
    (
        "identity.detokenize_field[field]",
        lambda c, v: c.identity.detokenize_field("idt_1", v),
        "identities/idt_1/detokenize/ID_1",
    ),
    (
        "identity.detokenize",
        lambda c, v: c.identity.detokenize(v, {"fields": []}),
        "identities/ID_1/detokenize",
    ),
    (
        "metadata.update",
        lambda c, v: c.metadata.update(v, {"meta_data": {"k": "v"}}),
        "ID_1/metadata",
    ),
    ("hooks.get", lambda c, v: c.hooks.get(v), "hooks/ID_1"),
    ("hooks.update", lambda c, v: c.hooks.update(v, HOOK), "hooks/ID_1"),
    ("hooks.delete", lambda c, v: c.hooks.delete(v), "hooks/ID_1"),
    ("api_keys.delete", lambda c, v: c.api_keys.delete(v), "api-keys/ID_1"),
]

# Collections are checked against four literals before the path is built;
# they still belong in the hostile matrix.
COLLECTION_METHODS: list[tuple[str, Callable[[Any, Any], Any]]] = [
    ("search.search", lambda c, v: c.search.search({"q": "*"}, v)),
    ("search.filter", lambda c, v: c.search.filter({"filters": []}, v)),
]

HOSTILE = [
    "../backup",
    "../search/reindex",
    "../api-keys/x",
    "%2e%2e/%2e%2e/secret",
    "%2E%2E",
    "..%2Fbackup",
    "ldg_1/../../backup",
    "ldg_1/x",
    ".",
    "..",
    "?",
    "ldg_1?owner=x",
    "#",
    "ldg_1#frag",
    "\\",
    "..\\backup",
    "ldg_1\r\nX-Injected: 1",
    "ldg_1\x00",
    "",
]


INDICATOR_METHOD = "ledger_balances.get_by_indicator"
INDICATOR_ENCODED = {"?", "ldg_1?owner=x", "#", "ldg_1#frag", "\\"}


def _hostile_cases() -> list[Any]:
    cases = []
    for name, call, _ in PATH_METHODS:
        # Indicators and currencies may legitimately contain ? # \\ (Core
        # accepts them and its route serves them once encoded); those are
        # covered by the indicator tests below.
        allowed = INDICATOR_ENCODED if name.startswith(INDICATOR_METHOD) else ()
        for value in HOSTILE:
            if value in allowed:
                continue
            cases.append(pytest.param(call, value, id=f"{name}-{value!r}"))
    for name, call in COLLECTION_METHODS:
        for value in HOSTILE:
            cases.append(pytest.param(call, value, id=f"{name}-{value!r}"))
    return cases


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize("call,value", _hostile_cases())
def test_hostile_path_values_are_rejected_and_nothing_is_sent(
    server: _Server, base: str, call: Callable[[Any, Any], Any], value: str
) -> None:
    server.clear()
    client = _client(server, base)
    try:
        response = call(client, value)
    finally:
        client.close()

    assert server.received == []
    assert response.status == 400


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize(
    "call,expected",
    [pytest.param(call, path, id=name) for name, call, path in PATH_METHODS],
)
def test_valid_ids_are_sent_unchanged(
    server: _Server, base: str, call: Callable[[Any, Any], Any], expected: str
) -> None:
    server.clear()
    client = _client(server, base)
    try:
        response = call(client, "ID_1")
    finally:
        client.close()

    assert response.status == 200
    assert [path for _, path, _ in server.received] == [base + expected]


@pytest.mark.parametrize("base", BASES)
def test_valid_id_with_space_is_escaped(server: _Server, base: str) -> None:
    server.clear()
    client = _client(server, base)
    try:
        client.ledgers.get("ldg 1")
    finally:
        client.close()

    assert [path for _, path, _ in server.received] == [base + "ledgers/ldg%201"]


# --------------------------------------------------------------------------- #
# The attack calls that motivated this change, by name.

ATTACK_CALLS = [
    ("refund-to-search-reindex", lambda c: c.transactions.refund("../search/reindex")),
    ("identity-get-backup", lambda c: c.identity.get("../backup")),
    ("hooks-delete-api-key", lambda c: c.hooks.delete("../api-keys/api_key_victim")),
    ("ledger-get-encoded-dots", lambda c: c.ledgers.get("%2e%2e/%2e%2e/secret")),
]


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize("call", [pytest.param(c, id=n) for n, c in ATTACK_CALLS])
def test_known_attack_calls_send_nothing(
    server: _Server, base: str, call: Callable[[Any], Any]
) -> None:
    server.clear()
    client = _client(server, base)
    try:
        response = call(client)
    finally:
        client.close()

    assert server.received == []
    assert response.status == 400


# --------------------------------------------------------------------------- #
# get_by_reference: references are free-form, so "/" and "%" are escaped
# rather than rejected, but "." / ".." are still refused.


@pytest.mark.parametrize("base", BASES)
def test_get_by_reference_escapes_slash_and_percent(server: _Server, base: str) -> None:
    server.clear()
    client = _client(server, base)
    try:
        response = client.transactions.get_by_reference("order/2025/%41")
    finally:
        client.close()

    assert response.status == 200
    assert [path for _, path, _ in server.received] == [
        base + "transactions/reference/order%2F2025%2F%2541"
    ]


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize(
    "reference",
    [
        ".",
        "..",
        "",
        "ref\r\nX-Injected: 1",
        "../backup",
        "a/./b",
        # Encoded and double-encoded dot segments and separators: a proxy
        # and an upstream that each decode once must not be able to turn
        # any of these into a dot segment.
        "%2e%2e",
        "%2E%2e",
        "%2e%2e%2fsecret",
        "%2e%2e%2f%2e%2e%2fsecret",
        "%252e%252e",
        "%252E%252e%252Fsecret",
        "%25252e%25252e%25252fsecret",
        "a%2F..%2Fb",
        "a%2f%2e%2e%2fb",
        "..%5Cbackup",
        "%2e%2e%5csecret",
    ],
)
def test_get_by_reference_rejects_dot_segments(
    server: _Server, base: str, reference: str
) -> None:
    server.clear()
    client = _client(server, base)
    try:
        response = client.transactions.get_by_reference(reference)
    finally:
        client.close()

    assert server.received == []
    assert response.status == 400


# --------------------------------------------------------------------------- #
# The client itself refuses endpoints with dot segments, decoded or not, so a
# future call site that forgets to validate still cannot leave the base path.


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize(
    "endpoint",
    [
        "ledgers/../backup",
        "ledgers/%2e%2e/%2e%2e/secret",
        "ledgers/%2E%2E/backup",
        "ledgers/.%2e/backup",
        "ledgers/./x",
        "ledgers/..\\backup",
        "../backup?x=1",
        "transactions/reference/%252e%252e%252fsecret",
        "transactions/reference/%252E%252E/x",
        "transactions/reference/%25252e%25252e/x",
        "transactions/reference/a%252f%252e%252e%252fb",
    ],
)
def test_client_refuses_dot_segment_endpoints(
    server: _Server, base: str, endpoint: str
) -> None:
    server.clear()
    client = _client(server, base)
    try:
        response = client._request(endpoint, None, "GET")
    finally:
        client.close()

    assert server.received == []
    assert response.status == 400


# --------------------------------------------------------------------------- #
# Balance indicators. Core's lookup route matches on the decoded path, so an
# indicator containing "/" can never be found there (Core returns 404); the
# SDK returns 400 instead. Every other character Core accepts when creating
# an indicator must still reach Core intact.


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize(
    "indicator,wire",
    [
        ("@World", "%40World"),
        ("@50%off", "%4050%25off"),
        ("@a?b", "%40a%3Fb"),
        ("@a#b", "%40a%23b"),
        ("@a\\b", "%40a%5Cb"),
        ("@a%2fb", "%40a%252fb"),
        ("@a..b", "%40a..b"),
    ],
)
def test_get_by_indicator_sends_core_accepted_indicators(
    server: _Server, base: str, indicator: str, wire: str
) -> None:
    server.clear()
    client = _client(server, base)
    try:
        response = client.ledger_balances.get_by_indicator(indicator, "USD")
    finally:
        client.close()

    assert response.status == 200
    assert [path for _, path, _ in server.received] == [
        base + f"balances/indicator/{wire}/currency/USD"
    ]


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize(
    "indicator,currency",
    [
        ("@user/name", "USD"),
        ("@World", "USD/EUR"),
        ("@x%2f..%2f..%2fsecret", "USD"),
        ("@x%252f%252e%252e", "USD"),
        ("..", "USD"),
        ("@World", "%2e%2e"),
        ("@World\r\n", "USD"),
        ("", "USD"),
    ],
)
def test_get_by_indicator_rejects_unroutable_or_unsafe_values(
    server: _Server, base: str, indicator: str, currency: str
) -> None:
    server.clear()
    client = _client(server, base)
    try:
        response = client.ledger_balances.get_by_indicator(indicator, currency)
    finally:
        client.close()

    assert server.received == []
    assert response.status == 400


# --------------------------------------------------------------------------- #
# A real decoding chain: requests go to a proxy that strips "/proxy/",
# percent-decodes the path ONCE and forwards it verbatim to an upstream that
# decodes again and resolves dot segments, the way a lenient server would.
# Whatever the SDK sends, the upstream must only ever see paths under the
# resource the method targets.


class _UpstreamHandler(BaseHTTPRequestHandler):
    def _record(self) -> None:
        raw = self.path.split("?", 1)[0]
        resolved = posixpath.normpath(unquote(raw).replace("\\", "/"))
        self.server.received.append(resolved)  # type: ignore[attr-defined]
        body = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_DELETE = _record

    def log_message(self, *args: Any) -> None:
        pass


class _DecodingProxyHandler(BaseHTTPRequestHandler):
    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        path, _, query = self.path.partition("?")
        assert path.startswith("/proxy/")
        once = unquote(path[len("/proxy") :])
        target = once + ("?" + query if query else "")
        conn = http.client.HTTPConnection(*self.server.upstream)  # type: ignore[attr-defined]
        # skip_host / raw putrequest keeps the decoded path byte-for-byte.
        conn.putrequest(self.command, target, skip_accept_encoding=True)
        conn.putheader("Content-Length", str(len(body or b"")))
        conn.endheaders(body)
        upstream = conn.getresponse()
        data = upstream.read()
        conn.close()
        self.send_response(upstream.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = _forward

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture(scope="module")
def decoding_chain() -> Iterator[tuple[str, list[str]]]:
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), _UpstreamHandler)
    upstream.received = []  # type: ignore[attr-defined]
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), _DecodingProxyHandler)
    proxy.upstream = upstream.server_address  # type: ignore[attr-defined]
    threads = [
        threading.Thread(target=srv.serve_forever, daemon=True)
        for srv in (upstream, proxy)
    ]
    for thread in threads:
        thread.start()
    yield (
        f"http://127.0.0.1:{proxy.server_address[1]}/proxy/",
        upstream.received,  # type: ignore[attr-defined]
    )
    for srv in (proxy, upstream):
        srv.shutdown()
        srv.server_close()


DOUBLE_ENCODED = [
    "%2e%2e%2f%2e%2e%2fsecret",
    "%252e%252e%252f%252e%252e%252fsecret",
    "%252E%252E%252F%252E%252E%252Fsecret",
    "x%2f%2e%2e%2f%2e%2e%2f%2e%2e%2fsecret",
    "%2e%2e%5c%2e%2e%5csecret",
]


@pytest.mark.parametrize("reference", DOUBLE_ENCODED)
def test_decoding_proxy_cannot_resolve_reference_outside_resource(
    decoding_chain: tuple[str, list[str]], reference: str
) -> None:
    base_url, received = decoding_chain
    received.clear()
    client = blnk_init(
        "test-key",
        BlnkClientOptions(base_url=base_url, retry_count=1, logger=_SilentLogger()),
    )
    try:
        client.transactions.get_by_reference(reference)
    finally:
        client.close()

    assert all(path.startswith("/transactions/reference/") for path in received)


@pytest.mark.parametrize(
    "indicator", ["@x%2f..%2f..%2fsecret", "@x%252f%252e%252e%252fs"]
)
def test_decoding_proxy_cannot_resolve_indicator_outside_resource(
    decoding_chain: tuple[str, list[str]], indicator: str
) -> None:
    base_url, received = decoding_chain
    received.clear()
    client = blnk_init(
        "test-key",
        BlnkClientOptions(base_url=base_url, retry_count=1, logger=_SilentLogger()),
    )
    try:
        client.ledger_balances.get_by_indicator(indicator, "USD")
    finally:
        client.close()

    assert all(path.startswith("/balances/indicator/") for path in received)


def test_decoding_proxy_still_serves_valid_reference(
    decoding_chain: tuple[str, list[str]],
) -> None:
    base_url, received = decoding_chain
    received.clear()
    client = blnk_init(
        "test-key",
        BlnkClientOptions(base_url=base_url, retry_count=1, logger=_SilentLogger()),
    )
    try:
        response = client.transactions.get_by_reference("order-2025-001")
    finally:
        client.close()

    assert response.status == 200
    assert received == ["/transactions/reference/order-2025-001"]

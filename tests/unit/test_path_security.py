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

import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

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


def _hostile_cases() -> list[Any]:
    cases = []
    for name, call, _ in PATH_METHODS:
        for value in HOSTILE:
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
# The scanner's proof-of-concept calls, by name.

SCANNER_POCS = [
    ("refund-to-search-reindex", lambda c: c.transactions.refund("../search/reindex")),
    ("identity-get-backup", lambda c: c.identity.get("../backup")),
    ("hooks-delete-api-key", lambda c: c.hooks.delete("../api-keys/api_key_victim")),
    ("ledger-get-encoded-dots", lambda c: c.ledgers.get("%2e%2e/%2e%2e/secret")),
]


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize("call", [pytest.param(c, id=n) for n, c in SCANNER_POCS])
def test_scanner_proofs_of_concept_send_nothing(
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
    "reference", [".", "..", "", "ref\r\nX-Injected: 1", "../backup", "a/./b"]
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


@pytest.mark.parametrize("base", BASES)
def test_get_by_reference_keeps_encoded_dots_literal(
    server: _Server, base: str
) -> None:
    """A reference that is literally "%2e%2e" is escaped to "%252e%252e":
    one decode gives back the literal text, never a dot segment."""
    server.clear()
    client = _client(server, base)
    try:
        response = client.transactions.get_by_reference("%2e%2e")
    finally:
        client.close()

    assert response.status == 200
    assert [path for _, path, _ in server.received] == [
        base + "transactions/reference/%252e%252e"
    ]


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

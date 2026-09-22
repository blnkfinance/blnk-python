# Blnk Python SDK

Python client for the [Blnk Finance](https://docs.blnkfinance.com) open-source ledger.
It covers the full Core API: ledgers, balances, transactions (including bulk, inflight,
and refunds), identities and tokenization, balance monitors, reconciliation, search,
metadata, hooks, API keys, and system health.

## Requirements

- Python 3.10+
- `requests` (installed automatically)

## Installation

Install from PyPI:

```sh
pip install blnk-python
```

The PyPI distribution name is `blnk-python`. Import the SDK with `from blnk_sdk import ...`.
This is the first public PyPI release for the Python SDK; earlier docs may reference
`blnk-sdk`, but that name was never published to PyPI.

Install from source:

```sh
pip install .            # from this directory
```

Development install with test tooling:

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Quickstart

```python
from blnk_sdk import BlnkClientOptions, blnk_init

blnk = blnk_init(
    "<secret_key_if_set>",
    BlnkClientOptions(base_url="http://localhost:5001"),  # trailing "/" appended automatically
)

new_ledger = blnk.ledgers.create({
    "name": "Customer Savings Account",
    "meta_data": {"project_owner": "YOUR_APP_NAME"},
})

print(new_ledger.status)   # 201
print(new_ledger.message)  # "Success"
print(new_ledger.data)     # parsed JSON body (dict)
```

A follow-up flow — create a balance and move money into it:

```python
ledger_id = new_ledger.data["ledger_id"]

balance = blnk.ledger_balances.create({
    "ledger_id": ledger_id,
    "currency": "USD",
})

deposit = blnk.transactions.create({
    "amount": 750,
    "precision": 100,
    "currency": "USD",
    "reference": "ref_001adcfgf",
    "description": "First deposit",
    "source": "@WorldUSD",
    "destination": balance.data["balance_id"],
    "allow_overdraft": True,
})

# Core 0.15.3+: preview without writing (HTTP 200, no transaction_id)
preview = blnk.transactions.create({
    "amount": 750,
    "precision": 100,
    "currency": "USD",
    "reference": "ref_001adcfgf",
    "description": "First deposit",
    "source": "@WorldUSD",
    "destination": balance.data["balance_id"],
    "allow_overdraft": True,
    "dry_run": True,
})
print(preview.status)                 # 200
print(preview.data["would_apply"])    # True/False
print(preview.data["balances"])       # current_* / resulting_* projections
```

Search several collections in one request (`POST /multi-search`; results come back
in the same order as the searches):

```python
results = blnk.search.multi_search({
    "searches": [
        {"collection": "transactions", "q": "ref_001", "query_by": "reference"},
        {"collection": "balances", "q": "*", "filter_by": "currency:USD"},
        {"collection": "ledgers", "q": "savings", "query_by": "name"},
    ],
})

transaction_hits = results.data["results"][0]["hits"]
```

Page through ledgers, balances, or transactions (Core defaults to `offset=0` and a
`limit` of `10`, or `20` for transactions). Invalid `limit`/`offset` is rejected
client-side with `400` before any request is made:

```python
from blnk_sdk.types.list_options import ListOptions

first_page = blnk.ledgers.list()
next_page = blnk.ledgers.list({"limit": 10, "offset": 10})
# same as blnk.ledgers.list(ListOptions(limit=10, offset=10))

usd_balances = blnk.ledger_balances.list({"limit": 50})
recent_transactions = blnk.transactions.list({"limit": 100})

monitors_for_balance = blnk.balance_monitor.list_by_balance_id(
    balance.data["balance_id"]
)
```

The client is a context manager — `with blnk_init(...) as blnk:` closes the underlying
`requests.Session` on exit.

## Authentication

Pass your Blnk secret key as the first argument to `blnk_init`. When set, every request
carries it in the `X-Blnk-Key` header; pass an empty string for unsecured self-hosted
instances.

## Services

Services are created lazily and cached per client instance:

`ledgers`, `ledger_balances`, `transactions`, `balance_monitor`, `reconciliation`,
`search`, `identity`, `system`, `metadata`, `hooks`, `api_keys`.

Request payloads are plain dicts, or the typed dataclasses in `blnk_sdk.types` — their
`to_dict()` omits fields left as `None`, so unset optionals never reach the wire.
Date fields accept `datetime` objects or preformatted strings and are sent as UTC
ISO-8601 timestamps without fractional seconds (`2026-12-31T23:59:59Z`), the format
Blnk Core expects; naive datetimes are treated as local time.

## Configuration

| Option | Default | Notes |
|---|---|---|
| `base_url` | required | `ValueError` if missing; `/` appended if absent |
| `timeout` | `10000` ms | per attempt; a timeout produces a synthetic `408` response and is never retried |
| `retry_count` | `1` | TOTAL attempts including the first; retries apply to `GET` requests only |
| `retry_delay_ms` | `2000` | linear backoff: `delay × attempt_number` |
| `logger` | console-like | any object with `info`/`error` (optional `debug`); sensitive keys (API keys, tokens, cookies) are redacted from log metadata |

## Error handling

SDK methods **never raise** for request or validation failures — they return an
`ApiResponse` value you can branch on:

- `status` — the HTTP status; `400` for client-side validation failures, `408` for
  timeouts, `500` for transport errors.
- `message` — `"Success"`, a specific validation message, or the error text. When
  Blnk Core returns a structured `error_detail` body, its message is used.
- `data` — the parsed JSON body (`None` on failure or empty body).
- `error` — a structured `BlnkApiErrorDetail(code, message, details)` when the Core
  returned a JSON error body.

Compare `error.code` against the constants in `BlnkErrorCode`, which mirror the
full Core 0.15.4 catalogue (`TXN_ALREADY_REFUNDED`, `BAL_NOT_FOUND`,
`TXN_INSUFFICIENT_FUNDS`, `TXN_DUPLICATE_REFERENCE`, `LGR_NOT_FOUND`, and so on):

```python
from blnk_sdk import BlnkErrorCode

refund = blnk.transactions.refund(transaction_id)
if refund.error and refund.error.code == BlnkErrorCode.TXN_ALREADY_REFUNDED:
    # 409: already refunded, or this id is itself a refund — nothing to do
    pass
```

Client-side validation runs before any request is sent: an invalid payload returns a
`400` response immediately and the HTTP layer is never invoked. The only raising paths
are programmer errors: constructing a client without a `base_url` (`ValueError`) and
requesting an unregistered service.

## Tests

```sh
.venv/bin/pytest tests/                # 528 offline unit tests; live-gated suites skip
BLNK_E2E=1 .venv/bin/pytest tests/     # also runs integration + e2e against http://localhost:5001
BLNK_E2E=1 .venv/bin/pytest tests/integration/test_core_0_15_3.py
```

Unit tests inject a mock transport and run fully offline. The live suites need a running
Blnk Core 0.15.3+ (`docker compose up` in the [blnk](https://github.com/blnkfinance/blnk) repo).

A Postman collection for the same Core 0.15.3 checks lives at
`postman/blnk-core-0.15.3.collection.json`. Import it and set `base_url` plus
`api_key` in the collection variables.

## Project layout

- `blnk_sdk/` — `client.py` (`Blnk`, `blnk_init`, `BlnkClientOptions`), `services/`
  (one module per service), `types/` (request/response dataclasses), `validators/`
  (client-side payload validation), plus retry policy, log redaction, serialization,
  and multipart helpers.
- `tests/` — unit suites per service/validator, `mocks/` fixtures, `integration/` and
  `e2e/` live suites (environment-gated).

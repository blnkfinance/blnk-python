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

Client-side validation runs before any request is sent: an invalid payload returns a
`400` response immediately and the HTTP layer is never invoked. The only raising paths
are programmer errors: constructing a client without a `base_url` (`ValueError`) and
requesting an unregistered service.

## Tests

```sh
.venv/bin/pytest tests/                # 489 tests: 444 offline unit tests, 45 live-gated
BLNK_E2E=1 .venv/bin/pytest tests/     # also runs integration + e2e against http://localhost:5001
```

Unit tests inject a mock transport and run fully offline. The live suites need a running
Blnk Core (`docker compose up` in the [blnk](https://github.com/blnkfinance/blnk) repo).

## Project layout

- `blnk_sdk/` — `client.py` (`Blnk`, `blnk_init`, `BlnkClientOptions`), `services/`
  (one module per service), `types/` (request/response dataclasses), `validators/`
  (client-side payload validation), plus retry policy, log redaction, serialization,
  and multipart helpers.
- `tests/` — unit suites per service/validator, `mocks/` fixtures, `integration/` and
  `e2e/` live suites (environment-gated).

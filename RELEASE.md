# Release Notes

## v1.5.0

v1.5.0 targets **Blnk Core 0.15.4**. v1.4.0 shipped Core 0.15.3 parity; this
release adds the full Core error catalogue, `search.multi_search`, and list
methods for ledgers, balances, transactions, and monitors by balance id.

See the [error codes guide](https://docs.blnkfinance.com/advanced/error-codes)
and the [Core changelog](https://docs.blnkfinance.com/changelog/blnk-core).

### Errors

- **`BlnkErrorCode`** — Mirrors Core's full `error_detail.code` catalogue
  (`internal/apierror/codes.go`), grouped by prefix: `GEN_`, `AUTH_`, `APIKEY_`,
  `TXN_`, `BAL_`, `LGR_`, `ACC_`, `IDT_`, `RECON_`, `META_`, `HOOK_`, `QUEUE_`,
  `SRCH_`, and `ADMIN_`. Each constant documents the HTTP status Core pairs it
  with.
- Codes introduced or re-routed in Core 0.15.4 that callers should branch on:
  - `TXN_ALREADY_REFUNDED` (`409`): refunding a transaction twice, or refunding a
    refund. Previously the reversal went through.
  - `BAL_NOT_FOUND` (`404`): a transaction naming a missing balance. Previously
    reported as `TXN_NOT_FOUND`.
  - `TXN_VALIDATION_ERROR` (`400`) is now also returned for a split request that
    carries both `sources` and `destinations`.
  - `GEN_CONFLICT` (`409`) is now also returned when a multi-leg refund fails
    part-way.
- The three existing constants (`TXN_INVALID_AMOUNT`, `GEN_CONFLICT`,
  `TXN_VALIDATION_ERROR`) keep their values; no caller changes are needed.
  [Guide](https://docs.blnkfinance.com/advanced/error-codes)

### Search

- **`search.multi_search`** — Wraps Core's `POST /multi-search`
  (`api/api.go`: `router.POST("/multi-search", a.MultiSearch)`). That route has
  been in Core since v0.10.0 (`b396752`); this SDK release is aligned with Core
  0.15.4. Core binds the body to Typesense's `MultiSearchSearchesParameter` and
  forwards it unchanged, so the wire shape is
  `{"searches": [{"collection": ..., "q": ..., ...}]}`. The response has
  `results` in the same order as `searches`. Each entry is validated client-side
  with the same rules as `search()`, and failures name the entry
  (`searches[1].collection ...`).

### List

- **`ledgers.list`** / **`ledger_balances.list`** — Wrap Core's `GET /ledgers`
  and `GET /balances`. Both take optional `ListOptions` (`limit` at least `1`,
  `offset` at least `0`) as query parameters; unset fields fall back to Core's
  defaults of `10` and `0`. Invalid pagination is rejected client-side with a
  `400` before any request is made.
- **`transactions.list`** — Wraps Core's `GET /transactions`, with the same
  optional `ListOptions`. Core's default page here is `limit=20`. Core's
  `GetAllTransactions` handler silently falls back to its defaults on invalid
  pagination; the SDK rejects it with a `400` instead so mistakes are visible.
- **`balance_monitor.list_by_balance_id`** — Wraps Core's
  `GET /balance-monitors/balances/:balance_id`. Existing `balance_monitor.list()`
  (all monitors) is unchanged.

These GET list routes have been in Core since ~0.14; this SDK release is
aligned with Core 0.15.4.

## v1.4.0

v1.4.0 targets **Blnk Core 0.15.3**. v1.3.0 shipped Core 0.15.0 parity; this
release adds dry-run previews, General Ledger `indicator` on create, refund
narration/metadata, and named Core error codes.

See [Dry-run transactions](https://docs.blnkfinance.com/transactions/dry-run)
and the [Core changelog](https://docs.blnkfinance.com/changelog/blnk-core).

### Transactions

- **`dry_run`** — Optional on `transactions.create`, `create_bulk`, `refund`,
  `update_status`, `bulk_commit_inflight`, and `bulk_void_inflight`. Core
  returns HTTP 200 with a preview (`would_apply`, `rejection`, `balances`).
  Nothing is written; `reference` is not consumed. Typed as
  `TransactionPreview` / `BulkTransactionPreview`. Use
  `is_transaction_preview` / `is_bulk_transaction_preview` to narrow a live
  `ApiResponse.data` dict. [Guide](https://docs.blnkfinance.com/transactions/dry-run)

- **`transactions.refund`** — Accepts `description` and `meta_data` in addition
  to `skip_queue`. Empty description inherits the original; metadata is merged
  onto the inherited copy.
  [Reference](https://docs.blnkfinance.com/reference/refund-transaction)

### Balances

- **`ledger_balances.create`** — Optional `indicator` (must start with `@`, no
  spaces) when `ledger_id` is `"general_ledger_id"`. Duplicate indicator +
  currency returns `409` / `GEN_CONFLICT`.
  [Guide](https://docs.blnkfinance.com/balances/internal-balances)

### Hooks

- **`hooks.list()`** — `type` remains optional. Omitting it lists PRE and POST
  hooks (`GET /hooks`).

### Errors

- **`BlnkErrorCode`** — Exported constants for `TXN_INVALID_AMOUNT`,
  `GEN_CONFLICT`, and `TXN_VALIDATION_ERROR`. Core 0.15.3 uses
  `TXN_VALIDATION_ERROR` for negative amounts and for source equal to
  destination; duplicate GL indicators return `GEN_CONFLICT`. Branch on
  `response.error.code`.
  [Guide](https://docs.blnkfinance.com/advanced/error-codes)

# Release Notes

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

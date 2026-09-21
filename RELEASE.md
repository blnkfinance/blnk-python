# Release Notes

## Unreleased — Core 0.15.4

Aligns the Python SDK error catalogue with
[Blnk Core 0.15.4](https://docs.blnkfinance.com/changelog/blnk-core).

### Errors

- **`BlnkErrorCode`** now mirrors Core's full `error_detail.code` catalogue
  (`internal/apierror/codes.go`), grouped by prefix: `GEN_`, `AUTH_`, `APIKEY_`,
  `TXN_`, `BAL_`, `LGR_`, `ACC_`, `IDT_`, `RECON_`, `META_`, `HOOK_`, `QUEUE_`,
  `SRCH_`, and `ADMIN_`. Each constant documents the HTTP status Core pairs it with.
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

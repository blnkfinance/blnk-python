"""Sample bulk-transaction responses from the Blnk Core API reference."""

# Sample `POST /transactions/bulk` response from the Blnk Core API reference.
# https://docs.blnkfinance.com/reference/bulk-transactions
core_bulk_transaction_reference_response = {
    "batch_id": "bulk_c62f200b-905f-4983-a349-cadd279234aa",
    "status": "applied",
    "transaction_count": 4,
}

# Async bulk response when `run_async` is true.
core_bulk_transaction_async_reference_response = {
    "batch_id": "bulk_c62f200b-905f-4983-a349-cadd279234aa",
    "status": "queued",
    "message": "Bulk transaction processing started",
}

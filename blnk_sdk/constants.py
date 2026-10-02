"""Client defaults and shared constants."""

# Default HTTP timeout in milliseconds.
DEFAULT_TIMEOUT_MS = 10000

# Total request attempts including the first (1 means no retries).
DEFAULT_RETRY_COUNT = 1

# Base delay between retry attempts in milliseconds.
DEFAULT_RETRY_DELAY_MS = 2000

# Cloud Proxy API root. Pair with BlnkClientOptions.instance_id so Core
# paths are sent as /proxy/{path}?instance_id=...
# See https://docs.blnkfinance.com/cloud/reference/proxy-api
CLOUD_PROXY_BASE_URL = "https://api.cloud.blnkfinance.com/proxy"

# Bulk-transaction limits shared by the transaction types and validators.
MAX_BULK_INFLIGHT_ITEMS = 100
MAX_BULK_CREATE_ITEMS = 10000

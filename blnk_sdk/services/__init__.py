"""Service package. Every service class has the constructor seam
`(request, logger, format_response)` where `request` is a BlnkRequest callable
`(endpoint, data, method, header_options=None) -> ApiResponse`.

default_services_map() builds the registry used by blnk_init. It imports each
service module lazily and skips modules that cannot be found, so the package
stays importable even if a service module is absent; accessing a service that
is not in the registry raises `Service {name} is not registered`."""

from __future__ import annotations

import importlib
from typing import Dict

_SERVICE_SPECS = (
    ("Ledgers", "ledgers", "Ledgers"),
    ("LedgerBalances", "ledger_balances", "LedgerBalances"),
    ("Transactions", "transactions", "Transactions"),
    ("BalanceMonitor", "balance_monitors", "BalanceMonitor"),
    ("Reconciliation", "reconciliation", "Reconciliation"),
    ("Search", "search", "Search"),
    ("Identity", "identity", "Identity"),
    ("System", "system", "System"),
    ("Metadata", "metadata", "Metadata"),
    ("Hooks", "hooks", "Hooks"),
    ("ApiKeys", "api_keys", "ApiKeys"),
)


def default_services_map() -> Dict[str, type]:
    services: Dict[str, type] = {}
    for service_name, module_name, class_name in _SERVICE_SPECS:
        try:
            module = importlib.import_module(f"{__name__}.{module_name}")
        except ModuleNotFoundError:
            continue
        cls = getattr(module, class_name, None)
        if cls is not None:
            services[service_name] = cls
    return services

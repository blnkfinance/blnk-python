"""Unit tests for `validate_monitor_id` (1 case with two assertions)."""

from __future__ import annotations

from blnk_sdk.validators.balance_monitors import validate_monitor_id


def test_validate_monitor_id() -> None:
    """ValidateMonitorId"""
    assert validate_monitor_id("mon_test_123") is None
    assert validate_monitor_id("") == "monitor id is required"

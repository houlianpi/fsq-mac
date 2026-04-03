# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for the AutomationAdapter protocol."""

from __future__ import annotations

from fsq_mac.adapters.protocol import AutomationAdapter
from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter


def test_appium_mac2_satisfies_protocol():
    """AppiumMac2Adapter must satisfy AutomationAdapter at runtime."""
    adapter = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
    assert isinstance(adapter, AutomationAdapter)


def test_protocol_is_runtime_checkable():
    """AutomationAdapter must be a runtime-checkable Protocol."""
    assert hasattr(AutomationAdapter, "__protocol_attrs__") or hasattr(AutomationAdapter, "_is_protocol")
    # Non-adapters should not match
    assert not isinstance("a string", AutomationAdapter)
    assert not isinstance(42, AutomationAdapter)

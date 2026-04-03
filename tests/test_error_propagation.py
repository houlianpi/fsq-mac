# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for unified error propagation — adapter returns error dicts, core translates."""

from __future__ import annotations

from unittest.mock import MagicMock

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
from fsq_mac.models import ErrorCode


class TestAdapterErrorDicts:
    def test_app_activate_no_driver(self):
        adapter = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        result = adapter.app_activate("com.test")
        assert result["error_code"] == ErrorCode.BACKEND_UNAVAILABLE
        assert "No active session" in result["detail"]

    def test_app_terminate_no_driver(self):
        adapter = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        result = adapter.app_terminate("com.test")
        assert result["error_code"] == ErrorCode.BACKEND_UNAVAILABLE
        assert "No active session" in result["detail"]

    def test_app_activate_connected_returns_dict(self):
        adapter = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        adapter._driver = MagicMock()
        adapter._driver.get_window_size.return_value = {"width": 100, "height": 100}
        adapter._driver.activate_app.return_value = None
        result = adapter.app_activate("com.test")
        # Should return a normal dict, not an error dict
        assert "error_code" not in result
        assert result["bundle_id"] == "com.test"

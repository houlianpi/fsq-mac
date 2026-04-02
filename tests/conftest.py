# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Shared test fixtures — all tests mock Appium; no real driver needed."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
from fsq_mac.session import SessionManager
import fsq_mac.session as session_module


@pytest.fixture()
def mock_config():
    return {
        "server_url": "http://127.0.0.1:4723",
        "platformName": "mac",
        "automationName": "Mac2",
        "bundleId": "com.apple.calculator",
    }


@pytest.fixture()
def mock_driver():
    driver = MagicMock()
    driver.capabilities = {"bundleId": "com.apple.calculator"}
    driver.get_window_size.return_value = {"width": 400, "height": 600}
    driver.page_source = "<AppiumAUT><XCUIElementTypeButton name='5'/></AppiumAUT>"
    return driver


@pytest.fixture()
def adapter(mock_config, mock_driver):
    a = AppiumMac2Adapter(mock_config)
    a._driver = mock_driver
    return a


@pytest.fixture()
def session_manager(tmp_path, mock_config, monkeypatch):
    monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
    return SessionManager(mock_config)

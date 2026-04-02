# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Semantic correctness: app_current returns frontmost, window_current returns position+size."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter


def test_app_current_returns_frontmost(mock_config):
    adapter = AppiumMac2Adapter(mock_config)
    adapter._driver = MagicMock()

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Finder\x1fcom.apple.finder\n"

    with patch("subprocess.run", return_value=mock_result):
        info = adapter.app_current()

    assert info["name"] == "Finder"
    assert info["bundle_id"] == "com.apple.finder"


def test_app_current_fallback(mock_config):
    """On AppleScript failure, should fall back to managed app info."""
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    driver.capabilities = {"bundleId": "com.apple.calculator"}
    adapter._driver = driver

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    # First call (frontmost query) fails, second call (fallback name query) succeeds
    fallback_result = MagicMock()
    fallback_result.returncode = 0
    fallback_result.stdout = "Calculator\n"

    with patch("subprocess.run", side_effect=[mock_result, fallback_result]):
        info = adapter.app_current()

    assert info["bundle_id"] == "com.apple.calculator"


def test_window_current_returns_position_and_size(mock_config):
    adapter = AppiumMac2Adapter(mock_config)
    adapter._driver = MagicMock()

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Finder\x1fcom.apple.finder\x1fDownloads\x1f100\x1f200\x1f800\x1f600\n"

    with patch("subprocess.run", return_value=mock_result):
        info = adapter.window_current()

    assert info["app_name"] == "Finder"
    assert info["app_bundle_id"] == "com.apple.finder"
    assert info["title"] == "Downloads"
    assert info["x"] == 100
    assert info["y"] == 200
    assert info["width"] == 800
    assert info["height"] == 600


def test_window_current_fallback(mock_config):
    """When frontmost query fails, falls back to managed app window."""
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    driver.capabilities = {"bundleId": "com.apple.calculator"}
    driver.get_window_size.return_value = {"width": 400, "height": 600}
    adapter._driver = driver

    # First call (frontmost) fails, second call (title query) succeeds
    fail_result = MagicMock()
    fail_result.returncode = 1
    fail_result.stdout = ""

    title_result = MagicMock()
    title_result.returncode = 0
    title_result.stdout = "Calculator\n"

    with patch("subprocess.run", side_effect=[fail_result, title_result]):
        info = adapter.window_current()

    assert info["width"] == 400
    assert info["height"] == 600
    assert info["title"] == "Calculator"

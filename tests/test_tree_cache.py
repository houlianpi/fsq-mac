# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for tree cache in AppiumMac2Adapter."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, PropertyMock

import pytest

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter


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
    # Use a PropertyMock so we can count accesses
    page_source_mock = PropertyMock(
        return_value="<AppiumAUT><XCUIElementTypeButton name='5'/></AppiumAUT>"
    )
    type(driver).page_source = page_source_mock
    driver._page_source_mock = page_source_mock
    return driver


@pytest.fixture()
def adapter(mock_config, mock_driver):
    a = AppiumMac2Adapter(mock_config)
    a._driver = mock_driver
    return a


def test_page_source_cached_within_ttl(adapter, mock_driver):
    """Calling _get_page_source() twice rapidly should access driver only once."""
    result1 = adapter._get_page_source()
    result2 = adapter._get_page_source()
    assert result1 == result2
    assert mock_driver._page_source_mock.call_count == 1


def test_page_source_expired_refetches(mock_config, mock_driver):
    """After TTL expires, cache should refetch from driver."""
    mock_config["tree_cache_ttl"] = 0.01
    adapter = AppiumMac2Adapter(mock_config)
    adapter._driver = mock_driver

    adapter._get_page_source()
    time.sleep(0.02)
    adapter._get_page_source()
    assert mock_driver._page_source_mock.call_count == 2


def test_cache_invalidated_after_click(adapter):
    """click() should invalidate the tree cache."""
    adapter._tree_cache = "cached"
    # Simulate click internals — just verify cache is cleared
    adapter._tree_cache = "cached"
    adapter._invalidate_refs = MagicMock()
    # Mock _resolve_ref and _wait_for_actionable for click to succeed
    mock_el = MagicMock()
    adapter._resolve_ref = MagicMock(return_value=(mock_el, None))
    adapter._wait_for_actionable = MagicMock(return_value=None)
    adapter.click("e0")
    assert adapter._tree_cache is None


def test_cache_invalidated_after_type(adapter):
    """type_text() should invalidate the tree cache."""
    adapter._tree_cache = "cached"
    adapter._invalidate_refs = MagicMock()
    mock_el = MagicMock()
    mock_el.get_attribute.return_value = "hello"
    adapter._resolve_ref = MagicMock(return_value=(mock_el, None))
    adapter._wait_for_actionable = MagicMock(return_value=None)
    adapter.type_text("e0", "hello")
    assert adapter._tree_cache is None


def test_cache_disabled_when_ttl_zero(mock_config, mock_driver):
    """With tree_cache_ttl=0, every call should hit the driver."""
    mock_config["tree_cache_ttl"] = 0
    adapter = AppiumMac2Adapter(mock_config)
    adapter._driver = mock_driver

    adapter._get_page_source()
    adapter._get_page_source()
    assert mock_driver._page_source_mock.call_count == 2


def test_force_refresh_bypasses_cache(adapter, mock_driver):
    """force_refresh=True should bypass the cache."""
    adapter._get_page_source()
    adapter._get_page_source(force_refresh=True)
    assert mock_driver._page_source_mock.call_count == 2

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for command timeout (issue #4): prevent driver operations from hanging."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
from fsq_mac.models import ErrorCode


@pytest.fixture()
def mock_config():
    return {
        "server_url": "http://127.0.0.1:4723",
        "platformName": "mac",
        "automationName": "Mac2",
        "bundleId": "com.apple.calculator",
        "command_timeout": 0.5,  # short timeout for tests
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


# ---------------------------------------------------------------------------
# _run_with_timeout unit tests
# ---------------------------------------------------------------------------

def test_run_with_timeout_returns_result(adapter):
    """Successful function returns its value."""
    result = adapter._run_with_timeout(lambda: 42)
    assert result == 42


def test_run_with_timeout_raises_on_timeout(adapter):
    """Blocking function triggers TimeoutError."""
    def _block():
        time.sleep(5)
    with pytest.raises(TimeoutError, match="timed out after"):
        adapter._run_with_timeout(_block, timeout=0.1)


def test_run_with_timeout_propagates_exception(adapter):
    """Exception in fn is re-raised by the caller."""
    def _fail():
        raise ValueError("boom")
    with pytest.raises(ValueError, match="boom"):
        adapter._run_with_timeout(_fail)


def test_run_with_timeout_uses_config_default(mock_config, mock_driver):
    """Timeout defaults to command_timeout from config."""
    mock_config["command_timeout"] = 0.1
    a = AppiumMac2Adapter(mock_config)
    a._driver = mock_driver
    with pytest.raises(TimeoutError):
        a._run_with_timeout(lambda: time.sleep(5))


# ---------------------------------------------------------------------------
# click() returns TIMEOUT instead of hanging
# ---------------------------------------------------------------------------

def _prep_adapter(adapter):
    """Set up common mocks for action methods."""
    adapter._invalidate_refs = MagicMock()
    mock_el = MagicMock()
    mock_el.location = {"x": 10, "y": 10}
    mock_el.size = {"width": 20, "height": 20}
    adapter._resolve_ref = MagicMock(return_value=(mock_el, None))
    adapter._wait_for_actionable = MagicMock(return_value=None)
    return mock_el


def test_click_recovers_via_coordinate_fallback_when_driver_click_hangs(adapter):
    """click() should succeed when driver click hangs but coordinate fallback works."""
    mock_el = _prep_adapter(adapter)
    with patch("fsq_mac.adapters.appium_mac2.ActionChains") as MockAC:
        chain = MockAC.return_value.move_to_element.return_value.click.return_value
        chain.perform.side_effect = lambda: time.sleep(5)
        # Also make fallback el.click() block
        mock_el.click.side_effect = lambda: time.sleep(5)
        with patch.object(adapter, "input_click_at", return_value={}) as mock_click_at:
            result = adapter.click("e0")
    assert result == {}
    mock_click_at.assert_called_once()


def test_click_returns_timeout_when_driver_click_and_coordinate_fallback_fail(adapter):
    """click() should still return TIMEOUT if both driver click paths and coordinate fallback fail."""
    mock_el = _prep_adapter(adapter)
    with patch("fsq_mac.adapters.appium_mac2.ActionChains") as MockAC:
        chain = MockAC.return_value.move_to_element.return_value.click.return_value
        chain.perform.side_effect = RuntimeError("primary failed")
        mock_el.click.side_effect = lambda: time.sleep(5)
        with patch.object(adapter, "input_click_at", return_value={"error_code": ErrorCode.INTERNAL_ERROR, "detail": "click-at failed"}):
            result = adapter.click("e0")
    assert result.get("error_code") == ErrorCode.TIMEOUT


def test_click_uses_cached_frame_for_coordinate_fallback(adapter):
    """click() should not re-read element frame after the driver click path has hung."""
    mock_el = _prep_adapter(adapter)
    cached_location = {"x": 10, "y": 10}
    cached_size = {"width": 20, "height": 20}
    mock_el.location = cached_location
    mock_el.size = cached_size
    with patch("fsq_mac.adapters.appium_mac2.ActionChains") as MockAC:
        chain = MockAC.return_value.move_to_element.return_value.click.return_value
        chain.perform.side_effect = lambda: time.sleep(5)
        mock_el.click.side_effect = lambda: time.sleep(5)
        with patch.object(adapter, "input_click_at", return_value={}) as mock_click_at:
            type(mock_el).location = PropertyMock(side_effect=[cached_location, RuntimeError("stale frame")])
            type(mock_el).size = PropertyMock(side_effect=[cached_size, RuntimeError("stale frame")])
            result = adapter.click("e0")
    assert result == {}
    mock_click_at.assert_called_once_with(20, 20)


def test_right_click_returns_timeout(adapter):
    """right_click() should return TIMEOUT when context_click blocks."""
    _prep_adapter(adapter)
    with patch("fsq_mac.adapters.appium_mac2.ActionChains") as MockAC:
        chain = MockAC.return_value.context_click.return_value
        chain.perform.side_effect = lambda: time.sleep(5)
        result = adapter.right_click("e0")
    assert result.get("error_code") == ErrorCode.TIMEOUT


def test_double_click_returns_timeout(adapter):
    """double_click() should return TIMEOUT when tap operations block."""
    mock_el = _prep_adapter(adapter)
    adapter._driver.tap.side_effect = lambda *a, **k: time.sleep(5)
    result = adapter.double_click("e0")
    assert result.get("error_code") == ErrorCode.TIMEOUT


def test_hover_returns_timeout(adapter):
    """hover() should return TIMEOUT when move_to_element blocks."""
    _prep_adapter(adapter)
    with patch("fsq_mac.adapters.appium_mac2.ActionChains") as MockAC:
        chain = MockAC.return_value.move_to_element.return_value
        chain.perform.side_effect = lambda: time.sleep(5)
        result = adapter.hover("e0")
    assert result.get("error_code") == ErrorCode.TIMEOUT


def test_type_text_returns_timeout(adapter):
    """type_text() should return TIMEOUT when el.click/send_keys blocks."""
    mock_el = _prep_adapter(adapter)
    mock_el.click.side_effect = lambda: time.sleep(5)
    result = adapter.type_text("e0", "hello")
    assert result.get("error_code") == ErrorCode.TIMEOUT


def test_drag_returns_timeout(adapter):
    """drag() should return TIMEOUT when drag_and_drop blocks."""
    adapter._invalidate_refs = MagicMock()
    src = MagicMock()
    tgt = MagicMock()
    adapter._resolve_ref = MagicMock(side_effect=[(src, None), (tgt, None)])
    adapter._wait_for_actionable = MagicMock(return_value=None)
    with patch("fsq_mac.adapters.appium_mac2.ActionChains") as MockAC:
        chain = MockAC.return_value.drag_and_drop.return_value
        chain.perform.side_effect = lambda: time.sleep(5)
        result = adapter.drag("e0", "e1")
    assert result.get("error_code") == ErrorCode.TIMEOUT


def test_input_click_at_returns_timeout(adapter):
    """input_click_at() should return TIMEOUT when macos: click blocks."""
    with patch.object(adapter, "_run_with_timeout", side_effect=TimeoutError("Driver operation timed out after 0.5s")):
        result = adapter.input_click_at(100, 200)
    assert result.get("error_code") == ErrorCode.TIMEOUT


# ---------------------------------------------------------------------------
# _resolve_query timeout
# ---------------------------------------------------------------------------

def test_resolve_query_returns_timeout_on_slow_find(mock_config, mock_driver):
    """_resolve_query returns TIMEOUT when find_elements blocks."""
    from fsq_mac.models import LocatorQuery
    mock_config["command_timeout"] = 0.2
    a = AppiumMac2Adapter(mock_config)
    a._driver = mock_driver
    mock_driver.find_elements.side_effect = lambda *a, **k: time.sleep(5)
    query = LocatorQuery(role="AXButton", name="OK")
    _, err = a._resolve_query(query)
    assert err == ErrorCode.TIMEOUT


# ---------------------------------------------------------------------------
# configure_driver_timeouts
# ---------------------------------------------------------------------------

def test_configure_driver_timeouts_sets_implicit_wait(adapter, mock_driver):
    """_configure_driver_timeouts sets implicitly_wait on the driver."""
    adapter._configure_driver_timeouts()
    mock_driver.implicitly_wait.assert_called_once_with(adapter._command_timeout)


def test_configure_driver_timeouts_noop_without_driver(mock_config):
    """_configure_driver_timeouts is a no-op when _driver is None."""
    a = AppiumMac2Adapter(mock_config)
    a._configure_driver_timeouts()  # should not raise

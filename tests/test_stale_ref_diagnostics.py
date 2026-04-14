# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for improved stale ref diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
from fsq_mac.models import ErrorCode


def _setup_adapter_with_stale_ref(mock_config):
    """Set up an adapter with one element inspected, then made stale."""
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    adapter._driver = driver

    driver.page_source = (
        '<AppiumAUT>'
        '<XCUIElementTypeButton name="Submit" visible="true" enabled="true" '
        'x="0" y="0" width="80" height="30"/>'
        '</AppiumAUT>'
    )
    web_el = MagicMock(name="WebElement_0")
    web_el.location = {"x": 0, "y": 0}
    driver.find_elements.return_value = [web_el]

    adapter.inspect()

    # Invalidate refs to make e0 stale
    adapter._invalidate_refs()

    # Make re-find by name also fail so the stale error propagates.
    # find_elements returns [] and WebDriverWait raises TimeoutException
    driver.find_elements.return_value = []
    driver.find_elements.side_effect = Exception("element gone")

    return adapter


def test_stale_ref_includes_cached_identity(mock_config):
    """Stale ref errors should include cached name in the detail."""
    adapter = _setup_adapter_with_stale_ref(mock_config)

    result = adapter.click("e0")
    assert result["error_code"] == ErrorCode.ELEMENT_REFERENCE_STALE
    assert "detail" in result
    assert "Submit" in result["detail"]
    assert "e0" in result["detail"]


def test_stale_ref_error_includes_details_dict(mock_config):
    """Stale ref errors should include structured details dict."""
    adapter = _setup_adapter_with_stale_ref(mock_config)

    result = adapter.click("e0")
    assert result["error_code"] == ErrorCode.ELEMENT_REFERENCE_STALE
    assert "details" in result
    assert result["details"]["ref"] == "e0"
    assert result["details"]["cached_name"] == "Submit"

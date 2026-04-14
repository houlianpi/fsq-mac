# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for improved stale ref diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
from fsq_mac.core import AutomationCore
from fsq_mac.models import ErrorCode
from fsq_mac.session import SessionManager
import fsq_mac.session as session_module


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
    driver.find_elements.return_value = []
    driver.find_elements.side_effect = Exception("element gone")

    return adapter


# -- Adapter-level tests ---------------------------------------------------


def test_stale_ref_includes_cached_identity(mock_config):
    """Stale ref errors should include cached name and role in the detail."""
    adapter = _setup_adapter_with_stale_ref(mock_config)

    result = adapter.click("e0")
    assert result["error_code"] == ErrorCode.ELEMENT_REFERENCE_STALE
    assert "detail" in result
    assert "Submit" in result["detail"]
    assert "Button" in result["detail"]
    assert "e0" in result["detail"]


def test_stale_ref_error_includes_details_dict(mock_config):
    """Stale ref errors should include structured details dict with role."""
    adapter = _setup_adapter_with_stale_ref(mock_config)

    result = adapter.click("e0")
    assert result["error_code"] == ErrorCode.ELEMENT_REFERENCE_STALE
    assert "details" in result
    assert result["details"]["ref"] == "e0"
    assert result["details"]["cached_name"] == "Submit"
    assert result["details"]["cached_role"] == "Button"


# -- Core-level tests: element_type stale ref propagation ------------------


@pytest.fixture()
def mock_adapter_for_core():
    adapter = MagicMock(unsafe=True)
    adapter.connected = True
    return adapter


@pytest.fixture()
def core_with_session(tmp_path, monkeypatch, mock_adapter_for_core):
    monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
    config = {"server_url": "http://127.0.0.1:4723"}
    sm = SessionManager(config, adapter_factory=lambda c: mock_adapter_for_core)
    sm.start()
    core = AutomationCore(sm)
    return core, mock_adapter_for_core


def test_element_type_stale_ref_propagates_details(core_with_session):
    """element_type stale ref should include details and suggested_next_action."""
    core, adapter = core_with_session
    adapter.type_text.return_value = {
        "error_code": ErrorCode.ELEMENT_REFERENCE_STALE,
        "detail": "Ref 'e0' (Submit, Button) is stale; UI changed since the last inspect",
        "details": {"ref": "e0", "cached_name": "Submit", "cached_role": "Button", "reason": "generation_mismatch"},
    }
    resp = core.element_type("e0", "hello")
    assert resp.ok is False
    assert resp.error.code == ErrorCode.ELEMENT_REFERENCE_STALE
    assert resp.error.suggested_next_action == "mac element inspect"
    assert resp.error.details["ref"] == "e0"
    assert resp.error.details["cached_name"] == "Submit"
    assert resp.error.details["cached_role"] == "Button"


def test_element_drag_stale_ref_propagates_details(core_with_session):
    """element_drag stale ref should include details and suggested_next_action."""
    core, adapter = core_with_session
    adapter.drag.return_value = {
        "error_code": ErrorCode.ELEMENT_REFERENCE_STALE,
        "detail": "Ref 'e0' (Submit, Button) is stale; UI changed since the last inspect",
        "details": {"ref": "e0", "cached_name": "Submit", "cached_role": "Button", "reason": "generation_mismatch"},
    }
    resp = core.element_drag("e0", "e1")
    assert resp.ok is False
    assert resp.error.code == ErrorCode.ELEMENT_REFERENCE_STALE
    assert resp.error.suggested_next_action == "mac element inspect"
    assert resp.error.details["ref"] == "e0"
    assert resp.error.details["cached_role"] == "Button"

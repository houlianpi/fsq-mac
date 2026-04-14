# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for best-effort auto-snapshot after mutating actions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fsq_mac.core import AutomationCore
from fsq_mac.models import ErrorCode, LocatorQuery
from fsq_mac.session import SessionManager
import fsq_mac.session as session_module


@pytest.fixture()
def mock_adapter():
    adapter = MagicMock(unsafe=True)
    adapter.connected = True
    return adapter


@pytest.fixture()
def core_with_session(tmp_path, monkeypatch, mock_adapter):
    monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
    config = {"server_url": "http://127.0.0.1:4723"}
    sm = SessionManager(config, adapter_factory=lambda c: mock_adapter)
    sm.start()
    core = AutomationCore(sm)
    return core, mock_adapter


class TestAutoSnapshot:
    def test_click_attaches_snapshot_on_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {"x": 100, "y": 200}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "Button", "name": "Home", "ref_bound": True}
        ]
        resp = core.element_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"
        assert resp.data["snapshot"]["snapshot_id"].startswith("snap_")
        assert isinstance(resp.data["snapshot"]["generation"], int)
        assert resp.data["snapshot"]["backend"] == "appium_mac2"
        assert resp.data["snapshot"]["binding_mode"] == "bound"
        assert resp.data["snapshot"]["binding_warnings"] == []
        assert resp.data["snapshot"]["elements"][0]["name"] == "Home"
        assert resp.data["snapshot"]["count"] == 1

    def test_click_snapshot_marks_web_content_as_best_effort(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {"x": 100, "y": 200}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "WebArea", "name": "Page", "ref_bound": True, "ref_status": "bound"}
        ]
        resp = core.element_click("e0")
        assert resp.ok is True
        warnings = {warning["code"]: warning for warning in resp.data["snapshot"]["binding_warnings"]}
        assert warnings["WEB_CONTENT_BEST_EFFORT"]["count"] == 1

    def test_click_snapshot_failed_best_effort(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {"x": 100, "y": 200}
        adapter.inspect.side_effect = RuntimeError("driver gone")
        resp = core.element_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "failed_best_effort"
        assert "snapshot" not in resp.data

    def test_click_error_no_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {"error_code": ErrorCode.ELEMENT_NOT_FOUND}
        resp = core.element_click("e0")
        assert resp.ok is False
        # No snapshot attempted on failure
        adapter.inspect.assert_not_called()

    def test_hover_no_snapshot(self, core_with_session):
        """Hover is non-mutating — should NOT attach snapshot."""
        core, adapter = core_with_session
        adapter.hover.return_value = {"x": 50, "y": 60}
        resp = core.element_hover("e0")
        assert resp.ok is True
        assert "snapshot_status" not in resp.data
        adapter.inspect.assert_not_called()

    def test_right_click_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.right_click.return_value = {"x": 10, "y": 20}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "MenuItem", "name": "Copy", "ref_bound": True}
        ]
        resp = core.element_right_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"

    def test_double_click_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.double_click.return_value = {"x": 10, "y": 20}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "Button", "name": "MissingRef", "ref_bound": False, "ref_status": "unbound"}
        ]
        resp = core.element_double_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"
        assert resp.data["snapshot"]["binding_mode"] == "unbound_only"
        assert resp.data["snapshot"]["binding_warnings"][0]["code"] == "UNBOUND_ELEMENTS_PRESENT"
        assert resp.data["snapshot"]["count"] == 1

    def test_right_click_snapshot_failed_best_effort(self, core_with_session):
        core, adapter = core_with_session
        adapter.right_click.return_value = {"x": 10, "y": 20}
        adapter.inspect.side_effect = RuntimeError("driver gone")
        resp = core.element_right_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "failed_best_effort"
        assert "snapshot" not in resp.data

    def test_double_click_snapshot_failed_best_effort(self, core_with_session):
        core, adapter = core_with_session
        adapter.double_click.return_value = {"x": 10, "y": 20}
        adapter.inspect.side_effect = RuntimeError("driver gone")
        resp = core.element_double_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "failed_best_effort"
        assert "snapshot" not in resp.data

    def test_scroll_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.scroll.return_value = {}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "ScrollArea", "name": None, "ref_bound": True}
        ]
        resp = core.element_scroll("e0", "down")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"

    def test_type_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.type_text.return_value = {"verified": True, "typed_value": "hello", "expected": "hello"}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "TextField", "name": "Input", "ref_bound": True}
        ]
        resp = core.element_type("e0", "hello")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"

    def test_drag_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.drag.return_value = {}
        adapter.inspect.return_value = []
        resp = core.element_drag("e0", "e1")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"

    def test_scroll_snapshot_failed_best_effort(self, core_with_session):
        core, adapter = core_with_session
        adapter.scroll.return_value = {}
        adapter.inspect.side_effect = RuntimeError("driver gone")
        resp = core.element_scroll("e0", "down")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "failed_best_effort"
        assert "snapshot" not in resp.data

    def test_type_snapshot_failed_best_effort(self, core_with_session):
        core, adapter = core_with_session
        adapter.type_text.return_value = {"verified": True, "typed_value": "hello", "expected": "hello"}
        adapter.inspect.side_effect = RuntimeError("driver gone")
        resp = core.element_type("e0", "hello")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "failed_best_effort"
        assert "snapshot" not in resp.data

    def test_drag_snapshot_failed_best_effort(self, core_with_session):
        core, adapter = core_with_session
        adapter.drag.return_value = {}
        adapter.inspect.side_effect = RuntimeError("driver gone")
        resp = core.element_drag("e0", "e1")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "failed_best_effort"
        assert "snapshot" not in resp.data

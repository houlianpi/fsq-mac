# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for core.py — AutomationCore, safety checks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fsq_mac.core import AutomationCore, check_safety
from fsq_mac.models import ErrorCode, SafetyLevel
from fsq_mac.session import SessionManager
import fsq_mac.session as session_module


@pytest.fixture()
def mock_adapter():
    adapter = MagicMock()
    adapter.connected = True
    return adapter


@pytest.fixture()
def core_with_session(tmp_path, monkeypatch, mock_adapter):
    """Create a core with an active session using a mock adapter factory."""
    monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
    config = {"server_url": "http://127.0.0.1:4723"}
    sm = SessionManager(config, adapter_factory=lambda c: mock_adapter)
    sm.start()
    core = AutomationCore(sm)
    return core, mock_adapter


class TestCheckSafety:
    def test_safe_command(self):
        assert check_safety("session.start", False) is None

    def test_guarded_command(self):
        assert check_safety("app.launch", False) is None

    def test_dangerous_blocked(self):
        resp = check_safety("app.terminate", False)
        assert resp is not None
        assert resp.ok is False
        assert resp.error.code == ErrorCode.ACTION_BLOCKED

    def test_dangerous_allowed(self):
        assert check_safety("app.terminate", True) is None

    def test_unknown_defaults_guarded(self):
        assert check_safety("unknown.command", False) is None


class TestSessionOps:
    def test_session_start(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
        config = {"server_url": "http://127.0.0.1:4723"}
        sm = SessionManager(config, adapter_factory=lambda c: MagicMock())
        core = AutomationCore(sm)
        resp = core.session_start()
        assert resp.ok is True
        assert resp.data["session_id"].startswith("s")

    def test_session_get_active(self, core_with_session):
        core, _ = core_with_session
        resp = core.session_get()
        assert resp.ok is True

    def test_session_get_no_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
        sm = SessionManager({"server_url": "http://127.0.0.1:4723"})
        core = AutomationCore(sm)
        resp = core.session_get()
        assert resp.ok is False
        assert resp.error.code == ErrorCode.SESSION_NOT_FOUND

    def test_session_list(self, core_with_session):
        core, _ = core_with_session
        resp = core.session_list()
        assert resp.ok is True
        assert len(resp.data["sessions"]) == 1

    def test_session_end(self, core_with_session):
        core, _ = core_with_session
        resp = core.session_end()
        assert resp.ok is True

    def test_session_end_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
        sm = SessionManager({"server_url": "http://127.0.0.1:4723"})
        core = AutomationCore(sm)
        resp = core.session_end()
        assert resp.ok is False


class TestAppOps:
    def test_app_launch_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_launch.return_value = {"bundle_id": "com.apple.calculator", "name": "Calculator"}
        adapter.window_current.return_value = {"title": "Calculator"}
        resp = core.app_launch("com.apple.calculator")
        assert resp.ok is True

    def test_app_launch_error_dict(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_launch.return_value = {
            "error_code": ErrorCode.BACKEND_UNAVAILABLE,
            "detail": "connection refused",
        }
        resp = core.app_launch("com.apple.calculator")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.BACKEND_UNAVAILABLE

    def test_app_activate_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_activate.return_value = {"bundle_id": "com.apple.safari"}
        adapter.window_current.return_value = {"title": "Safari"}
        resp = core.app_activate("com.apple.safari")
        assert resp.ok is True

    def test_app_activate_error_dict(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_activate.return_value = {
            "error_code": ErrorCode.BACKEND_UNAVAILABLE,
            "detail": "No active session",
        }
        resp = core.app_activate("com.apple.safari")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.BACKEND_UNAVAILABLE

    def test_app_terminate_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_terminate.return_value = {"terminated": "com.apple.safari"}
        resp = core.app_terminate("com.apple.safari")
        assert resp.ok is True

    def test_app_terminate_error_dict(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_terminate.return_value = {
            "error_code": ErrorCode.BACKEND_UNAVAILABLE,
            "detail": "No active session",
        }
        resp = core.app_terminate("com.apple.safari")
        assert resp.ok is False

    def test_app_current(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_current.return_value = {"name": "Finder", "bundle_id": "com.apple.finder"}
        resp = core.app_current()
        assert resp.ok is True
        assert resp.data["name"] == "Finder"

    def test_app_list(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_list.return_value = [{"name": "Finder", "bundle_id": "com.apple.finder"}]
        resp = core.app_list()
        assert resp.ok is True

    def test_no_session_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
        sm = SessionManager({"server_url": "http://127.0.0.1:4723"})
        core = AutomationCore(sm)
        resp = core.app_launch("com.test")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.SESSION_NOT_FOUND


class TestElementOps:
    def test_element_click_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {}
        resp = core.element_click("e0")
        assert resp.ok is True

    def test_element_click_stale(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {"error_code": ErrorCode.ELEMENT_REFERENCE_STALE}
        resp = core.element_click("e0")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.ELEMENT_REFERENCE_STALE

    def test_element_inspect(self, core_with_session):
        core, adapter = core_with_session
        adapter.inspect.return_value = [{"element_id": "e0", "role": "Button"}]
        resp = core.element_inspect()
        assert resp.ok is True

    def test_element_find_no_match(self, core_with_session):
        core, adapter = core_with_session
        adapter.find.return_value = ("no_match", [])
        resp = core.element_find("nonexistent")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.ELEMENT_NOT_FOUND

    def test_element_find_multiple(self, core_with_session):
        core, adapter = core_with_session
        adapter.find.return_value = ("multiple_matches", [{"element_id": "e0"}, {"element_id": "e1"}])
        resp = core.element_find("button")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.ELEMENT_AMBIGUOUS

    def test_element_find_single(self, core_with_session):
        core, adapter = core_with_session
        adapter.find.return_value = ("exactly_one_match", [{"element_id": "e0"}])
        resp = core.element_find("button")
        assert resp.ok is True

    def test_element_right_click(self, core_with_session):
        core, adapter = core_with_session
        adapter.right_click.return_value = {}
        resp = core.element_right_click("e0")
        assert resp.ok is True

    def test_element_double_click(self, core_with_session):
        core, adapter = core_with_session
        adapter.double_click.return_value = {}
        resp = core.element_double_click("e0")
        assert resp.ok is True

    def test_element_scroll(self, core_with_session):
        core, adapter = core_with_session
        adapter.scroll.return_value = {}
        resp = core.element_scroll("e0", "down")
        assert resp.ok is True

    def test_element_hover(self, core_with_session):
        core, adapter = core_with_session
        adapter.hover.return_value = {}
        resp = core.element_hover("e0")
        assert resp.ok is True

    def test_element_drag(self, core_with_session):
        core, adapter = core_with_session
        adapter.drag.return_value = {}
        resp = core.element_drag("e0", "e1")
        assert resp.ok is True

    def test_element_drag_error(self, core_with_session):
        core, adapter = core_with_session
        adapter.drag.return_value = {"error_code": ErrorCode.ELEMENT_NOT_FOUND, "detail": "not found"}
        resp = core.element_drag("e0", "e1")
        assert resp.ok is False


class TestInputOps:
    def test_input_key(self, core_with_session):
        core, adapter = core_with_session
        adapter.input_key.return_value = {}
        resp = core.input_key("return")
        assert resp.ok is True

    def test_input_key_error(self, core_with_session):
        core, adapter = core_with_session
        adapter.input_key.return_value = {"error_code": ErrorCode.INTERNAL_ERROR, "detail": "fail"}
        resp = core.input_key("return")
        assert resp.ok is False

    def test_input_hotkey(self, core_with_session):
        core, adapter = core_with_session
        adapter.input_hotkey.return_value = {}
        resp = core.input_hotkey("command+c")
        assert resp.ok is True

    def test_input_text(self, core_with_session):
        core, adapter = core_with_session
        adapter.input_text.return_value = {}
        resp = core.input_text("hello")
        assert resp.ok is True


class TestCaptureOps:
    def test_screenshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.screenshot.return_value = {"path": "test.png", "size_bytes": 1000}
        resp = core.capture_screenshot("test.png")
        assert resp.ok is True

    def test_screenshot_element(self, core_with_session):
        core, adapter = core_with_session
        adapter.screenshot_element.return_value = {"path": "test.png", "size_bytes": 500}
        resp = core.capture_screenshot("test.png", ref="e0")
        assert resp.ok is True

    def test_screenshot_rect(self, core_with_session):
        core, adapter = core_with_session
        adapter.screenshot_rect.return_value = {"path": "test.png", "size_bytes": 500}
        resp = core.capture_screenshot("test.png", rect="0,0,100,100")
        assert resp.ok is True

    def test_screenshot_error(self, core_with_session):
        core, adapter = core_with_session
        adapter.screenshot.return_value = {"error_code": ErrorCode.INTERNAL_ERROR, "detail": "fail"}
        resp = core.capture_screenshot("test.png")
        assert resp.ok is False

    def test_ui_tree(self, core_with_session):
        core, adapter = core_with_session
        adapter.ui_tree.return_value = "<xml/>"
        resp = core.capture_ui_tree()
        assert resp.ok is True


class TestWindowOps:
    def test_window_current(self, core_with_session):
        core, adapter = core_with_session
        adapter.window_current.return_value = {"title": "Test", "app_bundle_id": "com.test"}
        resp = core.window_current()
        assert resp.ok is True

    def test_window_list(self, core_with_session):
        core, adapter = core_with_session
        adapter.window_list.return_value = [{"index": 0, "title": "Test"}]
        resp = core.window_list()
        assert resp.ok is True

    def test_window_focus_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.window_focus.return_value = {"focused": 0, "title": "Test"}
        resp = core.window_focus(0)
        assert resp.ok is True

    def test_window_focus_error(self, core_with_session):
        core, adapter = core_with_session
        adapter.window_focus.return_value = {"error_code": ErrorCode.WINDOW_NOT_FOUND, "detail": "bad index"}
        resp = core.window_focus(99)
        assert resp.ok is False


class TestWaitOps:
    def test_wait_element_found(self, core_with_session):
        core, adapter = core_with_session
        adapter.wait_element.return_value = True
        resp = core.wait_element("button")
        assert resp.ok is True

    def test_wait_element_timeout(self, core_with_session):
        core, adapter = core_with_session
        adapter.wait_element.return_value = False
        resp = core.wait_element("button")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.TIMEOUT

    def test_wait_window_found(self, core_with_session):
        core, adapter = core_with_session
        adapter.wait_window.return_value = True
        resp = core.wait_window("Test")
        assert resp.ok is True

    def test_wait_window_timeout(self, core_with_session):
        core, adapter = core_with_session
        adapter.wait_window.return_value = False
        resp = core.wait_window("Test")
        assert resp.ok is False

    def test_wait_app_found(self, core_with_session):
        core, adapter = core_with_session
        adapter.wait_app.return_value = True
        resp = core.wait_app("com.test")
        assert resp.ok is True

    def test_wait_app_timeout(self, core_with_session):
        core, adapter = core_with_session
        adapter.wait_app.return_value = False
        resp = core.wait_app("com.test")
        assert resp.ok is False

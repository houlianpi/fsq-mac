# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for core.py — AutomationCore, safety checks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fsq_mac.core import AutomationCore, check_safety
from fsq_mac.models import ErrorCode, LocatorQuery, SafetyLevel
from fsq_mac.session import SessionManager
import fsq_mac.session as session_module


@pytest.fixture()
def mock_adapter():
    adapter = MagicMock(unsafe=True)
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
        adapter.click.return_value = {
            "element_bounds": {"x": 10, "y": 20, "width": 80, "height": 40},
            "center": {"x": 50, "y": 40},
        }
        resp = core.element_click("e0")
        assert resp.ok is True
        assert resp.data["element_bounds"]["width"] == 80
        assert resp.data["center"] == {"x": 50, "y": 40}

    def test_element_click_lazy_locator(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {}
        resp = core.element_click(ref=None, role="AXButton", name="Submit")
        assert resp.ok is True
        query = adapter.click.call_args.args[0]
        assert isinstance(query, LocatorQuery)
        assert query.role == "AXButton"
        assert query.name == "Submit"

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
        adapter.right_click.return_value = {
            "element_bounds": {"x": 1, "y": 2, "width": 3, "height": 4},
            "center": {"x": 2, "y": 4},
        }
        resp = core.element_right_click("e0")
        assert resp.ok is True
        assert resp.data["element_bounds"]["height"] == 4

    def test_element_double_click(self, core_with_session):
        core, adapter = core_with_session
        adapter.double_click.return_value = {
            "element_bounds": {"x": 11, "y": 12, "width": 30, "height": 20},
            "center": {"x": 26, "y": 22},
        }
        resp = core.element_double_click("e0")
        assert resp.ok is True
        assert resp.data["center"] == {"x": 26, "y": 22}

    def test_element_scroll(self, core_with_session):
        core, adapter = core_with_session
        adapter.scroll.return_value = {}
        resp = core.element_scroll("e0", "down")
        assert resp.ok is True

    def test_element_hover(self, core_with_session):
        core, adapter = core_with_session
        adapter.hover.return_value = {
            "element_bounds": {"x": 4, "y": 5, "width": 10, "height": 12},
            "center": {"x": 9, "y": 11},
        }
        resp = core.element_hover("e0")
        assert resp.ok is True
        assert resp.data["element_bounds"]["x"] == 4

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


class TestAssertOps:
    def test_assert_visible_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.assert_visible.return_value = {}
        resp = core.assert_visible(role="AXButton", name="Submit")
        assert resp.ok is True

    def test_assert_app_running_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_list.return_value = [{"name": "Safari", "bundle_id": "com.apple.Safari"}]
        resp = core.assert_app_running("com.apple.Safari")
        assert resp.ok is True
        assert resp.data["bundle_id"] == "com.apple.Safari"

    def test_assert_app_running_failure(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_list.return_value = [{"name": "Finder", "bundle_id": "com.apple.finder"}]
        resp = core.assert_app_running("com.apple.Safari")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.ASSERTION_FAILED

    def test_assert_app_frontmost_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_current.return_value = {"name": "Safari", "bundle_id": "com.apple.Safari"}
        resp = core.assert_app_frontmost("com.apple.Safari")
        assert resp.ok is True
        assert resp.data["bundle_id"] == "com.apple.Safari"

    def test_assert_app_frontmost_failure(self, core_with_session):
        core, adapter = core_with_session
        adapter.app_current.return_value = {"name": "Finder", "bundle_id": "com.apple.finder"}
        resp = core.assert_app_frontmost("com.apple.Safari")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.ASSERTION_FAILED

    def test_assert_text_failure(self, core_with_session):
        core, adapter = core_with_session
        adapter.assert_text.return_value = {
            "error_code": ErrorCode.ASSERTION_FAILED,
            "detail": "expected text 'Ready' but got 'Busy'",
        }
        resp = core.assert_text("Ready", role="AXStaticText", name="Status")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.ASSERTION_FAILED


class TestInputOps:
    def test_input_key(self, core_with_session):
        core, adapter = core_with_session
        adapter.input_key.return_value = {
            "element_bounds": {"x": 3, "y": 4, "width": 20, "height": 10},
            "center": {"x": 13, "y": 9},
        }
        resp = core.input_key("return")
        assert resp.ok is True
        assert resp.data["element_bounds"]["x"] == 3

    def test_input_key_error(self, core_with_session):
        core, adapter = core_with_session
        adapter.input_key.return_value = {"error_code": ErrorCode.INTERNAL_ERROR, "detail": "fail"}
        resp = core.input_key("return")
        assert resp.ok is False

    def test_input_hotkey(self, core_with_session):
        core, adapter = core_with_session
        adapter.input_hotkey.return_value = {
            "element_bounds": {"x": 1, "y": 2, "width": 30, "height": 20},
            "center": {"x": 16, "y": 12},
        }
        resp = core.input_hotkey("command+c")
        assert resp.ok is True
        assert resp.data["center"] == {"x": 16, "y": 12}

    def test_input_text(self, core_with_session):
        core, adapter = core_with_session
        adapter.input_text.return_value = {
            "element_bounds": {"x": 10, "y": 20, "width": 50, "height": 18},
            "center": {"x": 35, "y": 29},
        }
        resp = core.input_text("hello")
        assert resp.ok is True
        assert resp.data["element_bounds"]["height"] == 18

    def test_input_click_at(self, core_with_session):
        core, adapter = core_with_session
        adapter.input_click_at.return_value = {}
        resp = core.input_click_at(100, 200)
        assert resp.ok is True


class TestMenuOps:
    def test_menu_click(self, core_with_session):
        core, adapter = core_with_session
        adapter.menu_click.return_value = {}
        resp = core.menu_click("File > Open")
        assert resp.ok is True


class TestTraceOps:
    def test_trace_start_stop_status(self, core_with_session, tmp_path):
        core, _ = core_with_session
        resp = core.trace_start(str(tmp_path / "trace-out"))
        assert resp.ok is True
        assert resp.data["active"] is True

        status = core.trace_status()
        assert status.ok is True
        assert status.data["active"] is True

        stopped = core.trace_stop()
        assert stopped.ok is True
        assert stopped.data["active"] is False

    def test_trace_start_persists_frontmost_app(self, core_with_session, tmp_path):
        core, _ = core_with_session
        session_id = core._sm.active_id()
        assert session_id is not None
        core._sm.update_state(session_id, frontmost_app="com.apple.calculator")

        resp = core.trace_start(str(tmp_path / "trace-out"), sid=session_id)
        assert resp.ok is True

        trace = core._trace_store.load_trace(str(tmp_path / "trace-out"))
        assert trace.frontmost_app == "com.apple.calculator"

    def test_trace_replay_missing_path_returns_error(self, core_with_session):
        core, _ = core_with_session
        resp = core.trace_replay("/tmp/does-not-exist")
        assert resp.ok is False
        assert resp.error.code == ErrorCode.INVALID_ARGUMENT

    def test_trace_replay_is_not_safe(self):
        resp = check_safety("trace.replay", False)
        assert resp is None
        from fsq_mac.core import _SAFETY
        assert _SAFETY["trace.replay"] != SafetyLevel.SAFE

    def test_trace_replay_failure_preserves_structured_context(self, core_with_session, tmp_path):
        core, _ = core_with_session
        trace_dir = tmp_path / "replay-test"
        trace_dir.mkdir(parents=True)
        (trace_dir / "steps").mkdir()
        (trace_dir / "viewer").mkdir()
        import json
        (trace_dir / "trace.json").write_text(json.dumps({
            "trace_id": "replay-test",
            "output_dir": str(trace_dir),
            "status": "stopped",
            "steps": [
                {"index": 1, "command": "app.launch", "args": {"bundle_id": "com.test"}, "replayable": True, "artifacts": {}},
                {"index": 2, "command": "element.click", "args": {"role": "AXButton"}, "replayable": True, "artifacts": {}},
            ],
        }))

        def _executor(command, args):
            if command == "element.click":
                return {"ok": False, "command": command, "error": {"code": "ELEMENT_NOT_FOUND", "message": "missing"}}
            return {"ok": True, "command": command}

        core.set_trace_replay_executor(_executor)
        resp = core.trace_replay(str(trace_dir))
        assert resp.ok is False
        assert resp.error.code == ErrorCode.ELEMENT_NOT_FOUND
        assert resp.data["completed_steps"] == 1
        assert resp.data["failing_step"]["index"] == 2
        assert resp.data["failing_step"]["command"] == "element.click"

    def test_trace_custom_path_artifacts_in_correct_dir(self, core_with_session, tmp_path):
        core, _ = core_with_session
        custom_dir = tmp_path / "my-custom-trace"
        resp = core.trace_start(str(custom_dir))
        assert resp.ok is True
        paths = core.trace_artifact_paths(1)
        for key in ("before_screenshot", "after_screenshot", "before_tree", "after_tree"):
            assert paths[key].startswith(str(custom_dir)), f"{key} should be under custom dir"


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


# ---------------------------------------------------------------------------
# Issue #1: element_inspect returns error when driver not connected
# ---------------------------------------------------------------------------

class TestNoDriverErrors:
    def test_element_inspect_no_driver(self, core_with_session):
        """element_inspect should return BACKEND_UNAVAILABLE, not crash."""
        core, adapter = core_with_session
        adapter.inspect.side_effect = RuntimeError("No active driver connection.")
        resp = core.element_inspect()
        assert resp.ok is False
        assert resp.error.code == ErrorCode.BACKEND_UNAVAILABLE
        assert "driver" in resp.error.message.lower()

    def test_capture_ui_tree_no_driver(self, core_with_session):
        """capture_ui_tree should return BACKEND_UNAVAILABLE, not crash."""
        core, adapter = core_with_session
        adapter.ui_tree.side_effect = RuntimeError("No active driver connection.")
        resp = core.capture_ui_tree()
        assert resp.ok is False
        assert resp.error.code == ErrorCode.BACKEND_UNAVAILABLE

    def test_element_inspect_page_source_timeout(self, core_with_session):
        core, adapter = core_with_session
        adapter.inspect.side_effect = RuntimeError("Timed out retrieving page source after 15.0s")
        resp = core.element_inspect()
        assert resp.ok is False
        assert resp.error.code == ErrorCode.TIMEOUT

    def test_capture_ui_tree_page_source_timeout(self, core_with_session):
        core, adapter = core_with_session
        adapter.ui_tree.side_effect = RuntimeError("Timed out retrieving page source after 15.0s")
        resp = core.capture_ui_tree()
        assert resp.ok is False
        assert resp.error.code == ErrorCode.TIMEOUT

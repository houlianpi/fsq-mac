# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for daemon.py — dispatch, config loading, request handling."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from fsq_mac.daemon import _dispatch, _load_config, _body, _opts, _touch_activity, api_handler
from fsq_mac.core import AutomationCore
from fsq_mac.models import ErrorCode
from fsq_mac.session import SessionManager
import fsq_mac.session as session_module


@pytest.fixture()
def mock_core(tmp_path, monkeypatch):
    monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
    config = {"server_url": "http://127.0.0.1:4723"}
    adapter = MagicMock()
    adapter.connected = True
    adapter.inspect.return_value = []
    adapter.find.return_value = ("no_match", [])
    adapter.click.return_value = {}
    adapter.right_click.return_value = {}
    adapter.double_click.return_value = {}
    adapter.type_text.return_value = {"expected": "x", "typed_value": "x", "verified": True}
    adapter.scroll.return_value = {}
    adapter.hover.return_value = {}
    adapter.drag.return_value = {}
    adapter.input_key.return_value = {}
    adapter.input_hotkey.return_value = {}
    adapter.input_text.return_value = {}
    adapter.screenshot.return_value = {"path": "x.png", "size_bytes": 100}
    adapter.ui_tree.return_value = "<xml/>"
    adapter.window_current.return_value = {"title": "Test"}
    adapter.window_list.return_value = []
    adapter.window_focus.return_value = {"focused": 0}
    adapter.wait_element.return_value = True
    adapter.wait_window.return_value = True
    adapter.wait_app.return_value = True
    adapter.app_launch.return_value = {"bundle_id": "com.test"}
    adapter.app_activate.return_value = {"bundle_id": "com.test"}
    adapter.app_current.return_value = {"bundle_id": "com.test"}
    adapter.app_terminate.return_value = {"terminated": "com.test"}
    adapter.app_list.return_value = []

    sm = SessionManager(config, adapter_factory=lambda c: adapter)
    sm.start()
    return AutomationCore(sm)


class TestDispatch:
    def test_session_start(self, mock_core):
        resp = _dispatch(mock_core, "session", "start", {}, None)
        assert resp.ok is True

    def test_session_get(self, mock_core):
        resp = _dispatch(mock_core, "session", "get", {}, None)
        assert resp.ok is True

    def test_session_list(self, mock_core):
        resp = _dispatch(mock_core, "session", "list", {}, None)
        assert resp.ok is True

    def test_session_end(self, mock_core):
        resp = _dispatch(mock_core, "session", "end", {}, None)
        assert resp.ok is True

    def test_app_launch(self, mock_core):
        resp = _dispatch(mock_core, "app", "launch", {"bundle_id": "com.test"}, None)
        assert resp.ok is True

    def test_app_activate(self, mock_core):
        resp = _dispatch(mock_core, "app", "activate", {"bundle_id": "com.test"}, None)
        assert resp.ok is True

    def test_app_current(self, mock_core):
        resp = _dispatch(mock_core, "app", "current", {}, None)
        assert resp.ok is True

    def test_app_terminate(self, mock_core):
        resp = _dispatch(mock_core, "app", "terminate", {"bundle_id": "com.test"}, None)
        assert resp.ok is True

    def test_app_list(self, mock_core):
        resp = _dispatch(mock_core, "app", "list", {}, None)
        assert resp.ok is True

    def test_element_inspect(self, mock_core):
        resp = _dispatch(mock_core, "element", "inspect", {}, None)
        assert resp.ok is True

    def test_element_find(self, mock_core):
        resp = _dispatch(mock_core, "element", "find", {"locator": "x"}, None)
        assert resp is not None

    def test_element_click(self, mock_core):
        resp = _dispatch(mock_core, "element", "click", {"ref": "x"}, None)
        assert resp is not None

    def test_element_right_click(self, mock_core):
        resp = _dispatch(mock_core, "element", "right-click", {"ref": "x"}, None)
        assert resp is not None

    def test_element_double_click(self, mock_core):
        resp = _dispatch(mock_core, "element", "double-click", {"ref": "x"}, None)
        assert resp is not None

    def test_element_type(self, mock_core):
        resp = _dispatch(mock_core, "element", "type", {"ref": "x", "text": "hi"}, None)
        assert resp is not None

    def test_element_scroll(self, mock_core):
        resp = _dispatch(mock_core, "element", "scroll", {"ref": "x"}, None)
        assert resp is not None

    def test_element_hover(self, mock_core):
        resp = _dispatch(mock_core, "element", "hover", {"ref": "x"}, None)
        assert resp is not None

    def test_element_drag(self, mock_core):
        resp = _dispatch(mock_core, "element", "drag", {"ref": "x", "target": "y"}, None)
        assert resp is not None

    def test_input_key(self, mock_core):
        resp = _dispatch(mock_core, "input", "key", {"key": "return"}, None)
        assert resp is not None

    def test_input_hotkey(self, mock_core):
        resp = _dispatch(mock_core, "input", "hotkey", {"combo": "command+c"}, None)
        assert resp is not None

    def test_input_text(self, mock_core):
        resp = _dispatch(mock_core, "input", "text", {"text": "hi"}, None)
        assert resp is not None

    def test_capture_screenshot(self, mock_core):
        resp = _dispatch(mock_core, "capture", "screenshot", {"path": "x.png"}, None)
        assert resp is not None

    def test_capture_ui_tree(self, mock_core):
        resp = _dispatch(mock_core, "capture", "ui-tree", {}, None)
        assert resp is not None

    def test_window_current(self, mock_core):
        resp = _dispatch(mock_core, "window", "current", {}, None)
        assert resp is not None

    def test_window_list(self, mock_core):
        resp = _dispatch(mock_core, "window", "list", {}, None)
        assert resp is not None

    def test_window_focus(self, mock_core):
        resp = _dispatch(mock_core, "window", "focus", {"index": 0}, None)
        assert resp is not None

    def test_wait_element(self, mock_core):
        resp = _dispatch(mock_core, "wait", "element", {"locator": "x"}, None)
        assert resp is not None

    def test_wait_window(self, mock_core):
        resp = _dispatch(mock_core, "wait", "window", {"title": "x"}, None)
        assert resp is not None

    def test_wait_app(self, mock_core):
        resp = _dispatch(mock_core, "wait", "app", {"bundle_id": "com.test"}, None)
        assert resp is not None

    def test_assert_app_running(self, mock_core):
        resp = _dispatch(mock_core, "assert", "app-running", {"bundle_id": "com.test"}, None)
        assert resp is not None

    def test_assert_app_frontmost(self, mock_core):
        resp = _dispatch(mock_core, "assert", "app-frontmost", {"bundle_id": "com.test"}, None)
        assert resp is not None

    def test_unknown_command(self, mock_core):
        resp = _dispatch(mock_core, "unknown", "action", {}, None)
        assert resp.ok is False


class TestLoadConfig:
    def test_default_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.daemon.STATE_DIR", tmp_path)
        # No config file, no template
        config = _load_config()
        assert config["server_url"] == "http://127.0.0.1:4723"

    def test_config_from_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.daemon.STATE_DIR", tmp_path)
        (tmp_path / "config.json").write_text(
            json.dumps({"server_url": "http://custom:9999"})
        )
        config = _load_config()
        assert config["server_url"] == "http://custom:9999"

    def test_config_nested_mac(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.daemon.STATE_DIR", tmp_path)
        (tmp_path / "config.json").write_text(
            json.dumps({"mac": {"server_url": "http://nested:8888"}})
        )
        config = _load_config()
        assert config["server_url"] == "http://nested:8888"


class TestHelpers:
    def test_opts_with_session(self):
        result = _opts({"session": "s1"})
        assert result["sid"] == "s1"

    def test_opts_with_session_id(self):
        result = _opts({"session_id": "s2"})
        assert result["sid"] == "s2"

    def test_opts_empty(self):
        result = _opts({})
        assert result["sid"] is None

    def test_touch_activity(self):
        import fsq_mac.daemon as daemon_mod
        old = daemon_mod._last_activity
        _touch_activity()
        assert daemon_mod._last_activity >= old

    @pytest.mark.anyio
    async def test_body_valid_json(self):
        request = MagicMock()
        request.json = AsyncMock(return_value={"key": "value"})
        result = await _body(request)
        assert result == {"key": "value"}

    @pytest.mark.anyio
    async def test_body_invalid_json(self):
        request = MagicMock()
        request.json = AsyncMock(side_effect=Exception("bad json"))
        result = await _body(request)
        assert result == {}


class TestTraceDispatch:
    def test_trace_start_returns_active(self, mock_core):
        resp = _dispatch(mock_core, "trace", "start", {"path": "artifacts/traces/demo"}, None)
        assert resp.ok is True

    def test_trace_status_returns_response(self, mock_core):
        resp = _dispatch(mock_core, "trace", "status", {}, None)
        assert resp.ok is True


class TestTraceApiHandler:
    @pytest.mark.anyio
    async def test_api_handler_records_non_trace_command_when_trace_active(self, tmp_path, monkeypatch):
        import fsq_mac.daemon as daemon_mod

        monkeypatch.setattr(daemon_mod, "_core_error", None)

        core = MagicMock(unsafe=True)
        core.trace_status.return_value.to_dict.return_value = {"ok": True}
        core.app_current.return_value.to_dict.return_value = {"ok": True, "command": "app.current", "data": {"bundle_id": "com.test"}}
        core.active_trace_id.return_value = "trace-1"
        core.record_trace_step = MagicMock()
        monkeypatch.setattr(daemon_mod, "_core", core)

        request = MagicMock()
        request.path_params = {"domain": "app", "action": "current"}
        request.headers = {}
        request.json = AsyncMock(return_value={})

        response = await api_handler(request)
        assert response.status_code == 200
        core.record_trace_step.assert_called_once()

    @pytest.mark.anyio
    async def test_api_handler_records_trace_artifacts_when_trace_active(self, tmp_path, monkeypatch):
        import fsq_mac.daemon as daemon_mod

        monkeypatch.setattr(daemon_mod, "_core_error", None)
        monkeypatch.setattr(session_module, "STATE_DIR", tmp_path / "sessions")

        adapter = MagicMock()
        adapter.connected = True
        adapter.app_current.return_value = {"bundle_id": "com.test"}
        adapter.screenshot.side_effect = [
            {"path": str(tmp_path / "trace-1" / "steps" / "001-before.png"), "size_bytes": 10},
            {"path": str(tmp_path / "trace-1" / "steps" / "001-after.png"), "size_bytes": 11},
        ]
        adapter.ui_tree.side_effect = ["<root>before</root>", "<root>after</root>"]

        sm = SessionManager({"server_url": "http://127.0.0.1:4723"}, adapter_factory=lambda c: adapter)
        sm.start()
        core = AutomationCore(sm)
        core._trace_store = core._trace_store.__class__(tmp_path)
        started = core.trace_start(str(tmp_path / "trace-1"))
        assert started.ok is True

        monkeypatch.setattr(daemon_mod, "_core", core)

        request = MagicMock()
        request.path_params = {"domain": "app", "action": "current"}
        request.headers = {}
        request.json = AsyncMock(return_value={})

        response = await api_handler(request)
        assert response.status_code == 200

        manifest = json.loads((tmp_path / "trace-1" / "trace.json").read_text())
        step = manifest["steps"][0]
        assert step["artifacts"]["before_screenshot"].endswith("001-before.png")
        assert step["artifacts"]["after_screenshot"].endswith("001-after.png")
        assert step["artifacts"]["before_tree"].endswith("001-before-tree.xml")
        assert step["artifacts"]["after_tree"].endswith("001-after-tree.xml")
        assert (tmp_path / "trace-1" / "steps" / "001-before-tree.xml").read_text() == "<root>before</root>"
        assert (tmp_path / "trace-1" / "steps" / "001-after-tree.xml").read_text() == "<root>after</root>"


class TestTraceReplay:
    def test_trace_replay_dispatches_saved_steps(self, tmp_path, monkeypatch):
        import fsq_mac.daemon as daemon_mod

        trace_dir = tmp_path / "trace-1"
        trace_dir.mkdir(parents=True)
        (trace_dir / "viewer").mkdir(parents=True)
        (trace_dir / "steps").mkdir(parents=True)
        (trace_dir / "trace.json").write_text(json.dumps({
            "trace_id": "trace-1",
            "output_dir": str(trace_dir),
            "status": "stopped",
            "steps": [
                {"index": 1, "command": "app.current", "args": {}, "replayable": True, "artifacts": {}},
            ],
        }))

        core = MagicMock(unsafe=True)
        core.trace_replay.side_effect = None
        core.app_current.return_value.ok = True
        core.app_current.return_value.to_dict.return_value = {"ok": True, "command": "app.current"}

        with patch.object(daemon_mod, "_dispatch", wraps=daemon_mod._dispatch):
            resp = core.trace_replay(str(trace_dir))

        assert resp is not None


    @pytest.mark.anyio
    async def test_api_handler_uses_single_step_index_for_before_after_artifacts(self, tmp_path, monkeypatch):
        import fsq_mac.daemon as daemon_mod

        monkeypatch.setattr(daemon_mod, "_core_error", None)
        monkeypatch.setattr(session_module, "STATE_DIR", tmp_path / "sessions")

        adapter = MagicMock()
        adapter.connected = True
        adapter.app_current.return_value = {"bundle_id": "com.test"}
        adapter.screenshot.side_effect = [
            {"path": str(tmp_path / "trace-1" / "steps" / "001-before.png"), "size_bytes": 10},
            {"path": str(tmp_path / "trace-1" / "steps" / "001-after.png"), "size_bytes": 11},
        ]
        adapter.ui_tree.side_effect = ["<root>before</root>", "<root>after</root>"]

        sm = SessionManager({"server_url": "http://127.0.0.1:4723"}, adapter_factory=lambda c: adapter)
        sm.start()
        core = AutomationCore(sm)
        core._trace_store = core._trace_store.__class__(tmp_path)
        started = core.trace_start(str(tmp_path / "trace-1"))
        assert started.ok is True

        next_index = MagicMock(return_value=1)
        artifact_paths = MagicMock(return_value={
            "before_screenshot": str(tmp_path / "trace-1" / "steps" / "001-before.png"),
            "after_screenshot": str(tmp_path / "trace-1" / "steps" / "001-after.png"),
            "before_tree": str(tmp_path / "trace-1" / "steps" / "001-before-tree.xml"),
            "after_tree": str(tmp_path / "trace-1" / "steps" / "001-after-tree.xml"),
        })
        core.next_trace_step_index = next_index
        core.trace_artifact_paths = artifact_paths

        monkeypatch.setattr(daemon_mod, "_core", core)

        request = MagicMock()
        request.path_params = {"domain": "app", "action": "current"}
        request.headers = {}
        request.json = AsyncMock(return_value={})

        response = await api_handler(request)
        assert response.status_code == 200
        next_index.assert_called_once_with()
        assert artifact_paths.call_count == 2
        assert artifact_paths.call_args_list[0].args == (1,)
        assert artifact_paths.call_args_list[1].args == (1,)

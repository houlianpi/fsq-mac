# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Verify all CLI commands have matching daemon dispatch routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fsq_mac.core import AutomationCore
from fsq_mac.daemon import _dispatch
from fsq_mac.models import ErrorCode, Response


# Every (domain, action) pair the CLI can generate
_ALL_COMMANDS = [
    # session
    ("session", "start"),
    ("session", "get"),
    ("session", "list"),
    ("session", "end"),
    # app
    ("app", "launch"),
    ("app", "activate"),
    ("app", "current"),
    ("app", "terminate"),
    ("app", "list"),
    # element
    ("element", "inspect"),
    ("element", "find"),
    ("element", "click"),
    ("element", "right-click"),
    ("element", "double-click"),
    ("element", "type"),
    ("element", "scroll"),
    ("element", "hover"),
    ("element", "drag"),
    # assert
    ("assert", "visible"),
    ("assert", "enabled"),
    ("assert", "text"),
    ("assert", "value"),
    # input
    ("input", "key"),
    ("input", "hotkey"),
    ("input", "text"),
    ("input", "click-at"),
    # menu
    ("menu", "click"),
    # trace
    ("trace", "start"),
    ("trace", "stop"),
    ("trace", "status"),
    ("trace", "replay"),
    ("trace", "viewer"),
    ("trace", "codegen"),
    # capture
    ("capture", "screenshot"),
    ("capture", "ui-tree"),
    # window
    ("window", "current"),
    ("window", "list"),
    ("window", "focus"),
    # wait
    ("wait", "element"),
    ("wait", "window"),
    ("wait", "app"),
    # doctor
    ("doctor", "all"),
    ("doctor", "permissions"),
    ("doctor", "backend"),
    ("doctor", "plugins"),
]


def _make_response(domain, action):
    return MagicMock(spec=Response, ok=True, error=None,
                     to_dict=lambda: {"ok": True, "command": f"{domain}.{action}"})


@pytest.mark.parametrize("domain,action", _ALL_COMMANDS)
def test_route_is_dispatched(domain, action):
    """Every CLI command should produce a response (not 'Unknown command')."""
    core = MagicMock(unsafe=True)
    resp = _make_response(domain, action)
    # Set return value on all likely core methods
    core.session_start.return_value = resp
    core.session_get.return_value = resp
    core.session_list.return_value = resp
    core.session_end.return_value = resp
    core.app_launch.return_value = resp
    core.app_activate.return_value = resp
    core.app_current.return_value = resp
    core.app_terminate.return_value = resp
    core.app_list.return_value = resp
    core.element_inspect.return_value = resp
    core.element_find.return_value = resp
    core.element_click.return_value = resp
    core.element_right_click.return_value = resp
    core.element_double_click.return_value = resp
    core.element_type.return_value = resp
    core.element_scroll.return_value = resp
    core.element_hover.return_value = resp
    core.element_drag.return_value = resp
    core.assert_visible.return_value = resp
    core.assert_enabled.return_value = resp
    core.assert_text.return_value = resp
    core.assert_value.return_value = resp
    core.input_key.return_value = resp
    core.input_hotkey.return_value = resp
    core.input_text.return_value = resp
    core.input_click_at.return_value = resp
    core.menu_click.return_value = resp
    core.trace_start.return_value = resp
    core.trace_stop.return_value = resp
    core.trace_status.return_value = resp
    core.trace_replay.return_value = resp
    core.trace_viewer.return_value = resp
    core.trace_codegen.return_value = resp
    core.capture_screenshot.return_value = resp
    core.capture_ui_tree.return_value = resp
    core.window_current.return_value = resp
    core.window_list.return_value = resp
    core.window_focus.return_value = resp
    core.wait_element.return_value = resp
    core.wait_window.return_value = resp
    core.wait_app.return_value = resp

    body = {
        "bundle_id": "com.test",
        "ref": "e0",
        "strategy": "accessibility_id",
        "locator": "test",
        "text": "hello",
        "target": "e1",
        "key": "return",
        "combo": "command+c",
        "x": 100,
        "y": 200,
        "direction": "down",
        "path": "/tmp/test.png",
        "role": "AXButton",
        "name": "Submit",
        "label": "Search",
        "xpath": "//XCUIElementTypeButton[@name='Submit']",
        "expected": "Ready",
        "timeout": 5000,
        "title": "Test",
        "index": 0,
        "first_match": False,
    }

    with patch("fsq_mac.doctor.run_checks", return_value=resp):
        result = _dispatch(core, domain, action, body, sid=None)

    # Should NOT be the fallback "Unknown command" error
    if hasattr(result, "error") and result.error:
        assert result.error.code != ErrorCode.INVALID_ARGUMENT, (
            f"Route {domain}.{action} is not dispatched"
        )

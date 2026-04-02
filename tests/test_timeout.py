# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Verify timeout ms→sec conversion in core wait methods."""

from __future__ import annotations

from unittest.mock import MagicMock

from fsq_mac.core import AutomationCore


def test_wait_element_converts_ms_to_sec(session_manager):
    core = AutomationCore(session_manager)
    state = session_manager.start()
    adapter = MagicMock()
    adapter.wait_element.return_value = True
    session_manager._adapters[state.session_id] = adapter

    core.wait_element("Submit", "accessibility_id", timeout=5000, sid=state.session_id)

    adapter.wait_element.assert_called_once()
    _, kwargs = adapter.wait_element.call_args
    # 5000ms should become 5.0s
    assert kwargs.get("timeout", adapter.wait_element.call_args[0][2]) == 5.0


def test_wait_element_clamps_small_timeout(session_manager):
    core = AutomationCore(session_manager)
    state = session_manager.start()
    adapter = MagicMock()
    adapter.wait_element.return_value = True
    session_manager._adapters[state.session_id] = adapter

    core.wait_element("Submit", "accessibility_id", timeout=100, sid=state.session_id)

    adapter.wait_element.assert_called_once()
    # 100ms → 0.1s, clamped to 1s minimum
    call_args = adapter.wait_element.call_args
    actual_timeout = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("timeout")
    assert actual_timeout >= 1.0

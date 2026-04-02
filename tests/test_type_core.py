# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Regression: core.element_type returns error when verified=False."""

from __future__ import annotations

from unittest.mock import MagicMock

from fsq_mac.core import AutomationCore
from fsq_mac.models import ErrorCode


def _make_core(adapter_result):
    """Build an AutomationCore with a mocked session manager + adapter."""
    adapter = MagicMock()
    adapter.type_text.return_value = adapter_result

    sm = MagicMock()
    sm.adapter.return_value = adapter
    sm.active_id.return_value = "s1"
    sm.get.return_value = MagicMock(frontmost_app=None, frontmost_window=None)

    return AutomationCore(sm)


def test_type_mismatch_returns_error():
    core = _make_core({
        "verified": False,
        "typed_value": "helo",
        "expected": "hello",
    })

    resp = core.element_type("e0", "hello", sid="s1")

    assert resp.ok is False
    assert resp.error is not None
    assert resp.error.code == ErrorCode.TYPE_VERIFICATION_FAILED
    assert resp.error.details["typed_value"] == "helo"
    assert resp.error.details["expected"] == "hello"


def test_type_match_returns_success():
    core = _make_core({
        "verified": True,
        "typed_value": "hello",
        "expected": "hello",
    })

    resp = core.element_type("e0", "hello", sid="s1")

    assert resp.ok is True
    assert resp.data["verified"] is True


def test_type_unverifiable_returns_success():
    core = _make_core({
        "verified": None,
        "expected": "hello",
    })

    resp = core.element_type("e0", "hello", sid="s1")

    assert resp.ok is True
    assert resp.data["verified"] is None

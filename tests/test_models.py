# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for models.py — response envelope, error codes, helpers."""

from __future__ import annotations

import json

from fsq_mac.models import (
    ErrorCode, SafetyLevel, CLIError, ResponseMeta, Response,
    ElementInfo, LocatorQuery, TraceArtifacts, TraceRun, TraceStep,
    success_response, error_response, _RETRYABLE,
)


class TestErrorCode:
    def test_retryable_codes(self):
        assert ErrorCode.BACKEND_UNAVAILABLE in _RETRYABLE
        assert ErrorCode.TIMEOUT in _RETRYABLE
        assert ErrorCode.ELEMENT_NOT_FOUND in _RETRYABLE

    def test_non_retryable_codes(self):
        assert ErrorCode.INTERNAL_ERROR not in _RETRYABLE
        assert ErrorCode.ACTION_BLOCKED not in _RETRYABLE
        assert ErrorCode.INVALID_ARGUMENT not in _RETRYABLE

    def test_error_code_values(self):
        assert ErrorCode.SESSION_NOT_FOUND.value == "SESSION_NOT_FOUND"
        assert ErrorCode.PERMISSION_DENIED.value == "PERMISSION_DENIED"
        assert ErrorCode.ASSERTION_FAILED.value == "ASSERTION_FAILED"
        assert ErrorCode.TRACE_STEP_NOT_REPLAYABLE.value == "TRACE_STEP_NOT_REPLAYABLE"


class TestCLIError:
    def test_retryable_property(self):
        err = CLIError(code=ErrorCode.TIMEOUT, message="timed out")
        assert err.retryable is True

    def test_non_retryable_property(self):
        err = CLIError(code=ErrorCode.INTERNAL_ERROR, message="boom")
        assert err.retryable is False

    def test_to_dict(self):
        err = CLIError(
            code=ErrorCode.ELEMENT_NOT_FOUND,
            message="not found",
            suggested_next_action="mac element inspect",
            doctor_hint="mac doctor backend",
            details={"ref": "e0"},
        )
        d = err.to_dict()
        assert d["code"] == "ELEMENT_NOT_FOUND"
        assert d["message"] == "not found"
        assert d["retryable"] is True
        assert d["suggested_next_action"] == "mac element inspect"
        assert d["doctor_hint"] == "mac doctor backend"
        assert d["details"] == {"ref": "e0"}


class TestResponseMeta:
    def test_to_dict(self):
        meta = ResponseMeta(duration_ms=42, timestamp="2024-01-01T00:00:00Z",
                            frontmost_app="com.apple.finder")
        d = meta.to_dict()
        assert d["backend"] == "appium_mac2"
        assert d["duration_ms"] == 42
        assert d["frontmost_app"] == "com.apple.finder"

    def test_defaults(self):
        meta = ResponseMeta()
        assert meta.backend == "appium_mac2"
        assert meta.duration_ms == 0


class TestResponse:
    def test_to_dict_success(self):
        resp = success_response("session.start", data={"session_id": "s1"}, session_id="s1")
        d = resp.to_dict()
        assert d["ok"] is True
        assert d["command"] == "session.start"
        assert d["data"]["session_id"] == "s1"
        assert d["error"] is None

    def test_to_dict_error(self):
        resp = error_response("app.launch", ErrorCode.BACKEND_UNAVAILABLE, "fail")
        d = resp.to_dict()
        assert d["ok"] is False
        assert d["error"]["code"] == "BACKEND_UNAVAILABLE"
        assert d["error"]["message"] == "fail"

    def test_to_json(self):
        resp = success_response("test")
        j = resp.to_json()
        parsed = json.loads(j)
        assert parsed["ok"] is True

    def test_to_json_pretty(self):
        resp = success_response("test")
        j = resp.to_json(pretty=True)
        assert "\n" in j  # pretty-printed has newlines


class TestElementInfo:
    def test_to_dict(self):
        el = ElementInfo(
            element_id="e0", role="Button", name="OK",
            label="OK", value="1", frame={"x": 0, "y": 0, "width": 100, "height": 50},
            locator_hint="accessibility_id:OK",
        )
        d = el.to_dict()
        assert d["element_id"] == "e0"
        assert d["role"] == "Button"
        assert d["name"] == "OK"
        assert d["frame"]["width"] == 100
        # doc_order_index is internal and should not be in dict
        assert "doc_order_index" not in d

    def test_defaults(self):
        el = ElementInfo(element_id="e0", role="Button")
        assert el.enabled is True
        assert el.visible is True
        assert el.focused is False
        assert el.doc_order_index == -1


class TestLocatorQuery:
    def test_to_dict_for_role_name(self):
        query = LocatorQuery(role="AXButton", name="Submit")
        assert query.to_dict() == {"role": "AXButton", "name": "Submit"}

    def test_to_dict_omits_empty_fields(self):
        query = LocatorQuery(ref="e0", label="", xpath=None)
        assert query.to_dict() == {"ref": "e0"}


class TestTraceModels:
    def test_trace_run_to_dict_contains_steps(self):
        step = TraceStep(index=1, command="element.click", args={"role": "AXButton"})
        run = TraceRun(trace_id="t1", output_dir="/tmp/t1", steps=[step])
        data = run.to_dict()
        assert data["trace_id"] == "t1"
        assert data["output_dir"] == "/tmp/t1"
        assert data["steps"][0]["command"] == "element.click"

    def test_trace_artifacts_to_dict_omits_empty_fields(self):
        artifacts = TraceArtifacts(before_screenshot="before.png")
        assert artifacts.to_dict() == {"before_screenshot": "before.png"}


class TestHelpers:
    def test_success_response_defaults(self):
        resp = success_response("test")
        assert resp.ok is True
        assert resp.data is None
        assert resp.meta.backend == "appium_mac2"

    def test_error_response_with_details(self):
        resp = error_response("test", ErrorCode.ELEMENT_AMBIGUOUS, "multi",
                              details={"candidates": ["e0", "e1"]})
        assert resp.ok is False
        assert resp.error.details["candidates"] == ["e0", "e1"]

    def test_safety_level_values(self):
        assert SafetyLevel.SAFE.value == "safe"
        assert SafetyLevel.GUARDED.value == "guarded"
        assert SafetyLevel.DANGEROUS.value == "dangerous"


# -- ref_bound field tests --------------------------------------------------

def test_element_info_ref_bound_default_true():
    el = ElementInfo(element_id="e0", role="Button")
    assert el.ref_bound is True


def test_element_info_ref_bound_in_to_dict():
    el = ElementInfo(element_id="e0", role="Button", ref_bound=True)
    d = el.to_dict()
    assert d["ref_bound"] is True


def test_element_info_ref_bound_false():
    el = ElementInfo(element_id="e0", role="Button", ref_bound=False)
    d = el.to_dict()
    assert d["ref_bound"] is False


def test_element_info_contract_fields_in_to_dict():
    el = ElementInfo(
        element_id="e0",
        role="Button",
        frame={"x": 10, "y": 20, "width": 80, "height": 40},
        ref_status="bound",
        state_source="xml",
    )
    d = el.to_dict()
    assert d["ref"] == "e0"
    assert d["element_bounds"] == {"x": 10, "y": 20, "width": 80, "height": 40}
    assert d["center"] == {"x": 50, "y": 40}
    assert d["ref_status"] == "bound"
    assert d["state_source"] == "xml"

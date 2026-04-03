# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for formatters.py — JSON and pretty output."""

from __future__ import annotations

from fsq_mac.formatters import format_json, format_pretty, output


def test_format_json_success():
    data = {"ok": True, "command": "session.start", "data": {"session_id": "s1"}}
    result = format_json(data)
    assert '"ok": true' in result
    assert '"session_id": "s1"' in result


def test_format_json_error():
    data = {"ok": False, "command": "app.launch", "error": {"code": "BACKEND_UNAVAILABLE", "message": "fail"}}
    result = format_json(data)
    assert '"ok": false' in result
    assert "BACKEND_UNAVAILABLE" in result


def test_format_pretty_error_with_hints():
    data = {
        "ok": False,
        "command": "app.launch",
        "error": {
            "code": "BACKEND_UNAVAILABLE",
            "message": "Cannot connect",
            "suggested_next_action": "mac doctor backend",
            "doctor_hint": "mac doctor backend",
        },
        "meta": {},
    }
    result = format_pretty(data)
    assert "ERROR [BACKEND_UNAVAILABLE]" in result
    assert "Cannot connect" in result
    assert "hint: mac doctor backend" in result
    assert "doctor: mac doctor backend" in result


def test_format_pretty_success_simple():
    data = {"ok": True, "command": "session.start", "data": None, "meta": {}}
    result = format_pretty(data)
    assert "OK  session.start" in result


def test_format_pretty_success_with_dict_data():
    data = {
        "ok": True,
        "command": "session.get",
        "data": {"session_id": "s1", "active": True, "nested": {"key": "val"}},
        "meta": {"duration_ms": 42},
    }
    result = format_pretty(data)
    assert "OK  session.get" in result
    assert "session_id: s1" in result
    assert "active: yes" in result
    assert "(42ms)" in result
    assert "key: val" in result


def test_format_pretty_success_with_list_data():
    data = {
        "ok": True,
        "command": "session.list",
        "data": [{"id": "s1"}, {"id": "s2"}],
        "meta": {},
    }
    result = format_pretty(data)
    assert "id: s1" in result
    assert "id: s2" in result


def test_format_pretty_success_with_scalar_data():
    data = {"ok": True, "command": "test", "data": "hello", "meta": {}}
    result = format_pretty(data)
    assert "hello" in result


def test_format_pretty_success_with_list_values():
    data = {
        "ok": True,
        "command": "test",
        "data": {"items": ["a", "b"], "nested_list": [{"x": 1}]},
        "meta": {},
    }
    result = format_pretty(data)
    assert "items: (2 items)" in result
    assert "a" in result
    assert "b" in result


def test_format_pretty_none_values_skipped():
    data = {"ok": True, "command": "test", "data": {"key": None, "other": "val"}, "meta": {}}
    result = format_pretty(data)
    assert "key" not in result
    assert "other: val" in result


def test_output_json_mode():
    data = {"ok": True, "command": "test"}
    result = output(data, pretty=False)
    assert result.startswith("{")


def test_output_pretty_mode():
    data = {"ok": True, "command": "test", "data": None, "meta": {}}
    result = output(data, pretty=True)
    assert "OK  test" in result


def test_format_pretty_error_no_hints():
    data = {
        "ok": False,
        "command": "test",
        "error": {"code": "INTERNAL_ERROR", "message": "oops"},
        "meta": {},
    }
    result = format_pretty(data)
    assert "ERROR [INTERNAL_ERROR]" in result
    assert "hint" not in result


def test_format_pretty_no_duration():
    data = {"ok": True, "command": "test", "data": None, "meta": {}}
    result = format_pretty(data)
    assert "ms)" not in result


def test_format_pretty_list_data_scalars():
    data = {"ok": True, "command": "test", "data": ["item1", "item2"], "meta": {}}
    result = format_pretty(data)
    assert "item1" in result
    assert "item2" in result

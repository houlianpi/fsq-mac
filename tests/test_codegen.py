# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for trace-to-shell-script code generation."""

from __future__ import annotations

import json
from pathlib import Path

from fsq_mac.codegen import generate_shell_script
from fsq_mac.models import TraceRun, TraceStep
from fsq_mac.trace import TraceStore


def _make_run(steps: list[TraceStep] | None = None) -> TraceRun:
    return TraceRun(
        trace_id="test-trace",
        output_dir="/tmp/test-trace",
        steps=steps or [],
    )


def test_generate_shell_script_basic():
    run = _make_run([
        TraceStep(
            index=1,
            command="element.click",
            locator_query={"role": "AXButton", "name": "OK"},
        ),
    ])
    script = generate_shell_script(run)
    assert script.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in script
    assert "mac session start" in script
    assert "mac element click --role AXButton --name OK" in script
    assert "mac session end" in script


def test_generate_shell_script_skips_non_replayable():
    run = _make_run([
        TraceStep(index=1, command="element.click", replayable=False, args={"ref": "e0"}),
    ])
    script = generate_shell_script(run)
    assert "# SKIPPED (not replayable):" in script
    assert "element.click" in script


def test_generate_shell_script_quotes_args():
    run = _make_run([
        TraceStep(
            index=1,
            command="element.type",
            args={"text": "hello world"},
            locator_query={"name": "My Field"},
        ),
    ])
    script = generate_shell_script(run)
    # text is a positional arg: mac element type 'hello world' --name 'My Field'
    assert "'hello world'" in script
    assert "'My Field'" in script
    assert "mac element type 'hello world'" in script


def test_generate_shell_script_unknown_command():
    run = _make_run([
        TraceStep(index=1, command="custom.unknown", args={"foo": "bar"}),
    ])
    script = generate_shell_script(run)
    assert "# TODO: manual step" in script
    assert "custom.unknown" in script


def test_generate_shell_script_multiple_steps():
    run = _make_run([
        TraceStep(index=1, command="app.launch", args={"bundle_id": "com.apple.calculator"}),
        TraceStep(index=2, command="element.click", locator_query={"role": "AXButton", "name": "5"}),
        TraceStep(index=3, command="input.key", args={"key": "return"}),
    ])
    script = generate_shell_script(run)
    lines = script.strip().splitlines()
    assert "mac app launch com.apple.calculator" in script
    assert "mac element click --role AXButton --name 5" in script
    assert "mac input key return" in script
    assert lines[0] == "#!/usr/bin/env bash"
    assert lines[-1] == "mac session end"


def test_generate_shell_script_empty_trace():
    run = _make_run([])
    script = generate_shell_script(run)
    assert "#!/usr/bin/env bash" in script
    assert "mac session start" in script
    assert "mac session end" in script
    # Only preamble/epilogue lines, no command lines between
    lines = [l for l in script.strip().splitlines() if l and not l.startswith("#")]
    assert lines == [
        "set -euo pipefail",
        "mac session start",
        "mac session end",
    ]


def test_codegen_locator_flags():
    run = _make_run([
        TraceStep(
            index=1,
            command="element.click",
            locator_query={"role": "AXButton", "name": "OK", "label": "Confirm", "id": "btn-ok", "xpath": "//button"},
        ),
    ])
    script = generate_shell_script(run)
    assert "--role AXButton" in script
    assert "--name OK" in script
    assert "--label Confirm" in script
    assert "--id btn-ok" in script
    assert "--xpath //button" in script


def test_core_trace_codegen_returns_success(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    store.append_step(
        run.trace_id,
        TraceStep(index=1, command="element.click", args={"role": "AXButton"}, locator_query={"role": "AXButton"}),
    )

    from fsq_mac.core import AutomationCore
    from fsq_mac.session import SessionManager

    config = {"server_url": "http://127.0.0.1:4723", "platformName": "mac", "automationName": "Mac2"}
    sm = SessionManager(config, backend="appium_mac2")
    core = AutomationCore(sm)
    # Point internal store at our tmp trace store
    core._trace_store = store

    resp = core.trace_codegen(str(tmp_path / run.trace_id))
    result = resp.to_dict()
    assert result["ok"] is True
    assert "script" in result["data"]
    assert result["data"]["trace_id"] == run.trace_id
    assert result["data"]["step_count"] == 1
    assert "mac element click" in result["data"]["script"]


# ---------------------------------------------------------------------------
# CLI positional-arg syntax verification
# ---------------------------------------------------------------------------

def test_codegen_element_type_positional():
    """element.type: text is a positional arg, not --text."""
    run = _make_run([TraceStep(index=1, command="element.type", args={"text": "hi"})])
    script = generate_shell_script(run)
    assert "mac element type hi" in script
    assert "--text" not in script


def test_codegen_element_scroll_positional():
    """element.scroll: direction is a positional arg, not --direction."""
    run = _make_run([TraceStep(index=1, command="element.scroll", args={"direction": "up"})])
    script = generate_shell_script(run)
    assert "mac element scroll up" in script
    assert "--direction" not in script


def test_codegen_menu_click_positional():
    """menu.click: path is a positional arg, not --path."""
    run = _make_run([TraceStep(index=1, command="menu.click", args={"path": "File > Open"})])
    script = generate_shell_script(run)
    assert "mac menu click" in script
    assert "--path" not in script
    assert "'File > Open'" in script


def test_codegen_assert_text_positional():
    """assert.text: expected is a positional arg, not --expected."""
    run = _make_run([
        TraceStep(index=1, command="assert.text", args={"expected": "Ready"}, locator_query={"name": "Status"}),
    ])
    script = generate_shell_script(run)
    assert "mac assert text Ready" in script
    assert "--expected" not in script


def test_codegen_assert_value_positional():
    """assert.value: expected is a positional arg, not --expected."""
    run = _make_run([
        TraceStep(index=1, command="assert.value", args={"expected": "100"}, locator_query={"name": "Slider"}),
    ])
    script = generate_shell_script(run)
    assert "mac assert value 100" in script
    assert "--expected" not in script


def test_codegen_wait_element_positional():
    """wait.element: locator is a positional arg; must not be missing."""
    run = _make_run([
        TraceStep(index=1, command="wait.element", args={"locator": "btn-ok"}, locator_query={"name": "OK"}),
    ])
    script = generate_shell_script(run)
    assert "mac wait element btn-ok" in script


def test_codegen_wait_window_positional():
    """wait.window: title is a positional arg, not --title."""
    run = _make_run([TraceStep(index=1, command="wait.window", args={"title": "My Window"})])
    script = generate_shell_script(run)
    assert "mac wait window" in script
    assert "--title" not in script
    assert "'My Window'" in script


def test_codegen_wait_app_positional():
    """wait.app: bundle_id is a positional arg, not --bundle-id."""
    run = _make_run([TraceStep(index=1, command="wait.app", args={"bundle_id": "com.test"})])
    script = generate_shell_script(run)
    assert "mac wait app com.test" in script
    assert "--bundle-id" not in script


def test_codegen_input_click_at_positional():
    """input.click-at: x y are positional args, not --x/--y."""
    run = _make_run([TraceStep(index=1, command="input.click-at", args={"x": 100, "y": 200})])
    script = generate_shell_script(run)
    assert "mac input click-at 100 200" in script
    assert "--x" not in script
    assert "--y" not in script

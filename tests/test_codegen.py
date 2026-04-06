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
    assert "'hello world'" in script
    assert "'My Field'" in script


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

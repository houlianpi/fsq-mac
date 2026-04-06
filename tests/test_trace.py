# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for trace runtime and manifest persistence."""

from __future__ import annotations

import json
from pathlib import Path

from fsq_mac.models import TraceStep
from fsq_mac.trace import TraceStore


def test_start_trace_creates_directory_and_manifest(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    trace_dir = tmp_path / run.trace_id
    assert trace_dir.exists()
    assert (trace_dir / "trace.json").exists()


def test_load_trace_reads_existing_manifest(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    loaded = store.load_trace(str(tmp_path / run.trace_id))
    assert loaded.trace_id == run.trace_id


def test_append_step_persists_to_manifest(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    step = TraceStep(index=1, command="element.click", args={"role": "AXButton"})
    store.append_step(run.trace_id, step)
    manifest = json.loads((tmp_path / run.trace_id / "trace.json").read_text())
    assert manifest["steps"][0]["command"] == "element.click"


def test_stop_trace_marks_manifest_stopped(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    stopped = store.stop_trace(run.trace_id)
    assert stopped.status == "stopped"


def test_step_artifact_paths_are_numbered(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    paths = store.step_artifact_paths_for_dir(str(tmp_path / run.trace_id), 1)
    assert paths["before_screenshot"].endswith("steps/001-before.png")
    assert paths["after_tree"].endswith("steps/001-after-tree.xml")


def test_generate_viewer_creates_index_html(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    store.append_step(run.trace_id, TraceStep(index=1, command="element.click", args={"role": "AXButton"}))
    viewer_path = store.generate_viewer(run.trace_id)
    assert Path(viewer_path).exists()
    html = Path(viewer_path).read_text()
    assert "element.click" in html
    assert run.trace_id in html


def test_replay_fails_for_non_replayable_step(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    store.append_step(run.trace_id, TraceStep(index=1, command="element.click", replayable=False))
    result = store.replay(run.trace_id, lambda command, args: {"ok": True, "command": command})
    assert result["ok"] is False
    assert result["error"]["code"] == "TRACE_STEP_NOT_REPLAYABLE"


def test_replay_runs_steps_in_order(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    store.append_step(run.trace_id, TraceStep(index=1, command="app.launch", args={"bundle_id": "com.test"}))
    store.append_step(run.trace_id, TraceStep(index=2, command="element.click", args={"role": "AXButton"}))
    seen = []

    def _executor(command, args):
        seen.append((command, args))
        return {"ok": True, "command": command}

    result = store.replay(run.trace_id, _executor)
    assert result["ok"] is True
    assert seen == [
        ("app.launch", {"bundle_id": "com.test"}),
        ("element.click", {"role": "AXButton"}),
    ]

def test_generate_viewer_includes_artifact_paths_and_tree_diff_summary(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    trace_dir = tmp_path / run.trace_id
    steps_dir = trace_dir / "steps"
    (steps_dir / "001-before-tree.xml").write_text("line1\nline2\n")
    (steps_dir / "001-after-tree.xml").write_text("line1\nline3\n")
    store.append_step(
        run.trace_id,
        TraceStep(
            index=1,
            command="element.click",
            args={"role": "AXButton"},
            artifacts={
                "before_screenshot": str(steps_dir / "001-before.png"),
                "after_screenshot": str(steps_dir / "001-after.png"),
                "before_tree": str(steps_dir / "001-before-tree.xml"),
                "after_tree": str(steps_dir / "001-after-tree.xml"),
            },
        ),
    )
    viewer_path = store.generate_viewer(run.trace_id)
    html = Path(viewer_path).read_text()
    assert "001-before.png" in html
    assert "001-after.png" in html
    assert "first differing line" in html
    assert "2" in html


def test_replay_returns_failing_step_details_for_non_replayable_step(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    store.append_step(run.trace_id, TraceStep(index=3, command="element.click", replayable=False))
    result = store.replay(run.trace_id, lambda command, args: {"ok": True, "command": command})
    assert result["ok"] is False
    assert result["failing_step"]["index"] == 3
    assert result["error"]["code"] == "TRACE_STEP_NOT_REPLAYABLE"


def test_replay_returns_failed_command_details_when_executor_fails(tmp_path):
    store = TraceStore(tmp_path)
    run = store.start_trace()
    store.append_step(run.trace_id, TraceStep(index=1, command="app.launch", args={"bundle_id": "com.test"}))
    store.append_step(run.trace_id, TraceStep(index=2, command="element.click", args={"role": "AXButton"}))

    def _executor(command, args):
        if command == "element.click":
            return {
                "ok": False,
                "command": command,
                "error": {"code": "ELEMENT_NOT_FOUND", "message": "missing"},
            }
        return {"ok": True, "command": command}

    result = store.replay(run.trace_id, _executor)
    assert result["ok"] is False
    assert result["completed_steps"] == 1
    assert result["failing_step"]["index"] == 2
    assert result["failing_step"]["command"] == "element.click"
    assert result["error"]["code"] == "ELEMENT_NOT_FOUND"


def test_start_trace_with_custom_path_does_not_change_store_root(tmp_path):
    store = TraceStore(tmp_path / "root")
    custom_trace = tmp_path / "custom" / "trace-1"
    run = store.start_trace(str(custom_trace))
    assert run.output_dir == str(custom_trace)
    second = store.start_trace()
    assert second.output_dir.startswith(str(tmp_path / "root"))


def test_custom_path_artifact_paths_land_in_custom_dir(tmp_path):
    """step_artifact_paths_for_dir uses the real trace dir, not root/trace_id."""
    store = TraceStore(tmp_path / "default-root")
    custom_dir = tmp_path / "my-custom" / "my-trace"
    run = store.start_trace(str(custom_dir))
    paths = store.step_artifact_paths_for_dir(run.output_dir, 1)
    for key in ("before_screenshot", "after_screenshot", "before_tree", "after_tree"):
        assert paths[key].startswith(str(custom_dir)), f"{key} should be under custom dir"
    assert "default-root" not in paths["before_screenshot"]

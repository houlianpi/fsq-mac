# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Trace runtime — file-based trace manifests and viewer generation."""

from __future__ import annotations

import html
import json
import time
from pathlib import Path

from fsq_mac.models import ErrorCode, TraceArtifacts, TraceRun, TraceStep


class TraceStore:
    def __init__(self, root_dir: str | Path):
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _trace_dir(self, trace_id: str) -> Path:
        return self._root / trace_id

    def _manifest_path(self, trace_id: str) -> Path:
        return self._trace_dir(trace_id) / "trace.json"

    def _resolve_manifest_path(self, path_or_id: str) -> Path:
        candidate = Path(path_or_id)
        if candidate.name == "trace.json" and candidate.exists():
            return candidate
        if candidate.exists() and candidate.is_dir():
            return candidate / "trace.json"
        return self._manifest_path(path_or_id)

    def _write_manifest(self, run: TraceRun) -> None:
        path = self._manifest_path(run.trace_id)
        path.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))

    def _from_dict(self, data: dict) -> TraceRun:
        steps = []
        for item in data.get("steps", []):
            steps.append(
                TraceStep(
                    index=item["index"],
                    command=item["command"],
                    args=item.get("args", {}),
                    locator_query=item.get("locator_query", {}),
                    replayable=item.get("replayable", True),
                    started_at=item.get("started_at", ""),
                    duration_ms=item.get("duration_ms", 0),
                    ok=item.get("ok", True),
                    error=item.get("error"),
                    artifacts=item.get("artifacts", {}),
                )
            )
        return TraceRun(
            trace_id=data["trace_id"],
            output_dir=data["output_dir"],
            created_at=data.get("created_at", ""),
            backend=data.get("backend", "appium_mac2"),
            session_id=data.get("session_id"),
            status=data.get("status", "recording"),
            steps=steps,
        )

    def _tree_diff_summary(self, before_path: str | None, after_path: str | None) -> dict[str, int | bool | None]:
        before_text = Path(before_path).read_text() if before_path and Path(before_path).exists() else ""
        after_text = Path(after_path).read_text() if after_path and Path(after_path).exists() else ""
        before_lines = before_text.splitlines()
        after_lines = after_text.splitlines()
        first_diff = None
        max_len = max(len(before_lines), len(after_lines))
        for idx in range(max_len):
            before_line = before_lines[idx] if idx < len(before_lines) else None
            after_line = after_lines[idx] if idx < len(after_lines) else None
            if before_line != after_line:
                first_diff = idx + 1
                break
        return {
            "changed": before_text != after_text,
            "before_length": len(before_text),
            "after_length": len(after_text),
            "first_diff_line": first_diff,
        }

    def start_trace(self, path: str | None = None) -> TraceRun:
        trace_id = time.strftime("trace-%Y%m%d-%H%M%S", time.gmtime())
        trace_dir = Path(path) if path else self._trace_dir(trace_id)
        trace_dir.mkdir(parents=True, exist_ok=True)
        (trace_dir / "steps").mkdir(parents=True, exist_ok=True)
        (trace_dir / "viewer").mkdir(parents=True, exist_ok=True)
        run = TraceRun(
            trace_id=trace_dir.name,
            output_dir=str(trace_dir),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        (trace_dir / "trace.json").write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))
        return run

    def load_trace(self, path: str) -> TraceRun:
        manifest_path = self._resolve_manifest_path(path)
        return self._from_dict(json.loads(manifest_path.read_text()))

    def append_step(self, trace_id: str, step: TraceStep) -> TraceRun:
        run = self.load_trace(str(self._trace_dir(trace_id)))
        run.steps.append(step)
        self._write_manifest(run)
        return run

    def append_step_at_path(self, path: str, step: TraceStep) -> TraceRun:
        run = self.load_trace(path)
        run.steps.append(step)
        manifest_path = self._resolve_manifest_path(path)
        manifest_path.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))
        return run

    def stop_trace(self, trace_id: str) -> TraceRun:
        run = self.load_trace(str(self._trace_dir(trace_id)))
        run.status = "stopped"
        self._write_manifest(run)
        return run

    def stop_trace_at_path(self, path: str) -> TraceRun:
        run = self.load_trace(path)
        run.status = "stopped"
        manifest_path = self._resolve_manifest_path(path)
        manifest_path.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False))
        return run

    def step_artifact_paths(self, trace_id: str, step_index: int) -> dict[str, str]:
        trace_dir = self._trace_dir(trace_id)
        steps_dir = trace_dir / "steps"
        prefix = f"{step_index:03d}"
        return {
            "before_screenshot": str(steps_dir / f"{prefix}-before.png"),
            "after_screenshot": str(steps_dir / f"{prefix}-after.png"),
            "before_tree": str(steps_dir / f"{prefix}-before-tree.xml"),
            "after_tree": str(steps_dir / f"{prefix}-after-tree.xml"),
        }

    def generate_viewer(self, trace_id: str) -> str:
        manifest_path = self._resolve_manifest_path(trace_id)
        run = self.load_trace(str(manifest_path))
        viewer_dir = manifest_path.parent / "viewer"
        viewer_dir.mkdir(parents=True, exist_ok=True)
        viewer_path = viewer_dir / "index.html"
        step_rows: list[str] = []
        for step in run.steps:
            diff = self._tree_diff_summary(step.artifacts.before_tree, step.artifacts.after_tree)
            artifacts_html = "".join(
                f'<li>{name}: {html.escape(Path(path).name)}</li>'
                for name, path in step.artifacts.to_dict().items()
            )
            diff_html = (
                f'<p>tree changed: {str(diff["changed"]).lower()}, '
                f'before length: {diff["before_length"]}, '
                f'after length: {diff["after_length"]}, '
                f'first differing line: {diff["first_diff_line"]}</p>'
            )
            step_rows.append(
                '<li>'
                f'<strong>{step.index}</strong> {html.escape(step.command)}'
                f'<div><ul>{artifacts_html}</ul></div>'
                f'{diff_html}'
                '</li>'
            )
        page = (
            '<html><body>'
            f'<h1>{html.escape(run.trace_id)}</h1>'
            f'<p>Status: {html.escape(run.status)}</p>'
            f'<ul>{"".join(step_rows)}</ul>'
            '</body></html>'
        )
        viewer_path.write_text(page)
        return str(viewer_path)

    def replay(self, trace_id: str, executor) -> dict:
        run = self.load_trace(trace_id)
        completed = 0
        for step in run.steps:
            step_ref = {"index": step.index, "command": step.command}
            if not step.replayable:
                return {
                    "ok": False,
                    "trace_id": run.trace_id,
                    "completed_steps": completed,
                    "failing_step": step_ref,
                    "error": {
                        "code": ErrorCode.TRACE_STEP_NOT_REPLAYABLE.value,
                        "message": f"Step {step.index} is not replayable",
                    },
                }
            result = executor(step.command, step.args)
            if not result.get("ok", False):
                return {
                    "ok": False,
                    "trace_id": run.trace_id,
                    "completed_steps": completed,
                    "failing_step": step_ref,
                    "error": result.get(
                        "error",
                        {"code": ErrorCode.INTERNAL_ERROR.value, "message": "Replay failed"},
                    ),
                }
            completed += 1
        return {"ok": True, "completed_steps": completed, "trace_id": run.trace_id}

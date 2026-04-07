# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Trace -> shell script code generation."""

from __future__ import annotations

import shlex
from typing import Any

from fsq_mac.models import TraceRun


# ---------------------------------------------------------------------------
# Locator flags
# ---------------------------------------------------------------------------

_LOCATOR_KEYS = ("role", "name", "label", "id", "xpath")


def _locator_flags(locator_query: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in _LOCATOR_KEYS:
        val = locator_query.get(key)
        if val is not None:
            parts.append(f"--{key} {shlex.quote(str(val))}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Command -> CLI line
# ---------------------------------------------------------------------------

def _emit_step(command: str, args: dict[str, Any], locator_query: dict[str, Any]) -> str | None:
    loc = _locator_flags(locator_query)

    # -- app --
    if command == "app.launch":
        return f"mac app launch {shlex.quote(str(args.get('bundle_id', '')))}"
    if command == "app.activate":
        return f"mac app activate {shlex.quote(str(args.get('bundle_id', '')))}"
    if command == "app.terminate":
        return f"mac app terminate {shlex.quote(str(args.get('bundle_id', '')))} --allow-dangerous"
    if command == "app.current":
        return "mac app current"
    if command == "app.list":
        return "mac app list"

    # -- element --
    if command == "element.click":
        return f"mac element click {loc}".strip()
    if command == "element.right-click":
        return f"mac element right-click {loc}".strip()
    if command == "element.double-click":
        return f"mac element double-click {loc}".strip()
    if command == "element.type":
        text = shlex.quote(str(args.get("text", "")))
        return f"mac element type {text} {loc}".strip()
    if command == "element.scroll":
        direction = shlex.quote(str(args.get("direction", "down")))
        return f"mac element scroll {direction} {loc}".strip()
    if command == "element.hover":
        return f"mac element hover {loc}".strip()
    if command == "element.drag":
        parts = ["mac element drag"]
        if loc:
            parts.append(loc)
        for tkey in _LOCATOR_KEYS:
            tval = args.get(f"target_{tkey}") or args.get(f"target.{tkey}")
            if tval is not None:
                parts.append(f"--target-{tkey} {shlex.quote(str(tval))}")
        return " ".join(parts)

    # -- input --
    if command == "input.key":
        return f"mac input key {shlex.quote(str(args.get('key', '')))}"
    if command == "input.hotkey":
        return f"mac input hotkey {shlex.quote(str(args.get('combo', '')))}"
    if command == "input.text":
        return f"mac input text {shlex.quote(str(args.get('text', '')))}"
    if command == "input.click-at":
        x = shlex.quote(str(args.get("x", 0)))
        y = shlex.quote(str(args.get("y", 0)))
        return f"mac input click-at {x} {y}"

    # -- menu --
    if command == "menu.click":
        return f"mac menu click {shlex.quote(str(args.get('path', '')))}"

    # -- window --
    if command == "window.current":
        return "mac window current"
    if command == "window.list":
        return "mac window list"
    if command == "window.focus":
        return f"mac window focus {shlex.quote(str(args.get('index', 0)))}"

    # -- capture --
    if command == "capture.screenshot":
        path = args.get("path", "./screenshot.png")
        return f"mac capture screenshot {shlex.quote(str(path))}"
    if command == "capture.ui-tree":
        return "mac capture ui-tree"

    # -- element (read-only) --
    if command == "element.inspect":
        return "mac element inspect"

    # -- assert --
    if command == "assert.visible":
        return f"mac assert visible {loc}".strip()
    if command == "assert.enabled":
        return f"mac assert enabled {loc}".strip()
    if command == "assert.text":
        expected = shlex.quote(str(args.get("expected", "")))
        return f"mac assert text {expected} {loc}".strip()
    if command == "assert.value":
        expected = shlex.quote(str(args.get("expected", "")))
        return f"mac assert value {expected} {loc}".strip()

    # -- wait --
    if command == "wait.element":
        locator_val = args.get("locator", "")
        if not locator_val and loc:
            # Derive a locator value from locator_query for the positional arg
            for k in _LOCATOR_KEYS:
                v = locator_query.get(k)
                if v is not None:
                    locator_val = str(v)
                    break
        parts = [f"mac wait element {shlex.quote(str(locator_val))}"]
        if loc:
            parts.append(loc)
        if args.get("timeout") is not None:
            parts.append(f"--timeout {shlex.quote(str(args['timeout']))}")
        return " ".join(parts)
    if command == "wait.window":
        title = shlex.quote(str(args.get("title", "")))
        parts = [f"mac wait window {title}"]
        if args.get("timeout") is not None:
            parts.append(f"--timeout {shlex.quote(str(args['timeout']))}")
        return " ".join(parts)
    if command == "wait.app":
        bundle_id = shlex.quote(str(args.get("bundle_id", "")))
        parts = [f"mac wait app {bundle_id}"]
        if args.get("timeout") is not None:
            parts.append(f"--timeout {shlex.quote(str(args['timeout']))}")
        return " ".join(parts)

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_shell_script(trace_run: TraceRun) -> str:
    """Convert a TraceRun into a bash script of ``mac`` CLI commands."""
    lines: list[str] = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "mac session start",
    ]

    if trace_run.frontmost_app:
        lines.append(f"mac app launch {shlex.quote(str(trace_run.frontmost_app))}")

    lines.append("")

    for step in trace_run.steps:
        if not step.replayable:
            lines.append(f"# SKIPPED (not replayable): {step.command} {step.args}")
            continue

        cli_line = _emit_step(step.command, step.args, step.locator_query)
        if cli_line is None:
            lines.append(f"# TODO: manual step — {step.command} {step.args}")
        else:
            lines.append(cli_line)

    lines.append("")
    lines.append("mac session end")
    lines.append("")
    return "\n".join(lines)

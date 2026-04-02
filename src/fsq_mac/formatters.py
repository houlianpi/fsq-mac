# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Output formatters — JSON (default) and pretty (human-friendly)."""

from __future__ import annotations

import json


def format_json(data: dict) -> str:
    """Compact single-line JSON (default for agent consumption)."""
    return json.dumps(data, ensure_ascii=False)


def format_pretty(data: dict) -> str:
    """Human-friendly output with key information highlighted."""
    ok = data.get("ok", False)
    command = data.get("command", "")
    error = data.get("error")
    payload = data.get("data")
    meta = data.get("meta", {})

    lines: list[str] = []

    if not ok and error:
        code = error.get("code", "ERROR")
        msg = error.get("message", "")
        lines.append(f"ERROR [{code}]: {msg}")
        hint = error.get("suggested_next_action")
        if hint:
            lines.append(f"  hint: {hint}")
        doctor = error.get("doctor_hint")
        if doctor:
            lines.append(f"  doctor: {doctor}")
        return "\n".join(lines)

    # Success path
    lines.append(f"OK  {command}")

    if payload is None:
        pass
    elif isinstance(payload, dict):
        _format_dict(payload, lines, indent=2)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                _format_dict(item, lines, indent=2)
                lines.append("")
            else:
                lines.append(f"  {item}")
    else:
        lines.append(f"  {payload}")

    duration = meta.get("duration_ms")
    if duration:
        lines.append(f"  ({duration}ms)")

    return "\n".join(lines)


def _format_dict(d: dict, lines: list[str], indent: int = 0) -> None:
    """Recursively format a dict into indented key: value lines."""
    prefix = " " * indent
    for key, val in d.items():
        if val is None:
            continue
        if isinstance(val, dict):
            lines.append(f"{prefix}{key}:")
            _format_dict(val, lines, indent + 2)
        elif isinstance(val, list):
            lines.append(f"{prefix}{key}: ({len(val)} items)")
            for item in val:
                if isinstance(item, dict):
                    _format_dict(item, lines, indent + 4)
                    lines.append("")
                else:
                    lines.append(f"{prefix}    {item}")
        elif isinstance(val, bool):
            lines.append(f"{prefix}{key}: {'yes' if val else 'no'}")
        else:
            lines.append(f"{prefix}{key}: {val}")


def output(data: dict, pretty: bool = False) -> str:
    """Format and return the output string."""
    if pretty:
        return format_pretty(data)
    return format_json(data)

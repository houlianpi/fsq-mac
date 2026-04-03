# Phase 0: User-Perceivable Foundation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make fsq-mac usable as a real tool: add `--version`, create a Claude Code skill file, and add region/element screenshot support.

**Architecture:** Three independent tasks. Task 0a modifies CLI only. Task 0b creates a new skill file. Task 0c threads new parameters through CLI → daemon → core → adapter.

**Tech Stack:** Python 3.10+, argparse, Starlette, Appium Mac2 WebDriver, macOS `screencapture`

---

### Task 1: Add `--version` flag to CLI

**Files:**
- Modify: `src/fsq_mac/cli.py:18-29` (add version argument to parser)
- Test: `tests/test_cli_version.py` (new)

**Step 1: Write the test**

Create `tests/test_cli_version.py`:

```python
"""Test --version flag."""
from __future__ import annotations

import pytest
from fsq_mac.cli import main


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "fsq-mac" in captured.out
    assert "0.1.0" in captured.out
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_version.py -v`
Expected: FAIL — argparse doesn't know `--version` yet

**Step 3: Add `--version` to the parser**

In `src/fsq_mac/cli.py`, add after line 22 (after `prog="mac"` description line), inside `_build_parser()`:

```python
from fsq_mac import __version__
```

Add to the top imports section. Then inside `_build_parser()`, after `p = argparse.ArgumentParser(...)`:

```python
    p.add_argument("--version", action="version",
                   version=f"fsq-mac {__version__}")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_version.py -v`
Expected: PASS

**Step 5: Run all existing tests to verify no regressions**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add tests/test_cli_version.py src/fsq_mac/cli.py
git commit -m "Add --version flag to CLI"
```

---

### Task 2: Create Claude Code skill file

**Files:**
- Create: `.claude/skills/mac-automation.md` (new)

> **Note:** This task creates the skill file using the /skill-creator pattern. The skill teaches Claude Code how to use the `mac` CLI for macOS automation.

**Step 1: Create the skill file**

Create `.claude/skills/mac-automation.md` with the full skill definition. The file should contain:

```markdown
# macOS Automation with fsq-mac

Use when the user asks to automate, interact with, test, or control a macOS native application. Triggers: mac automation, click button, UI testing, accessibility, element inspect, screenshot, app launch, macOS app, native app automation.

## Prerequisites

- Appium server running (`appium` in a terminal)
- Mac2 driver installed (`appium driver install mac2`)
- macOS Accessibility permissions granted
- Run `mac doctor` to verify setup

## Core Workflow

Every automation session follows this pattern:

1. **Start session** — `mac session start`
2. **Launch/activate app** — `mac app launch <bundle_id>`
3. **Inspect UI** — `mac element inspect` to discover elements
4. **Act** — click, type, scroll, etc. using element refs (e0, e1, ...)
5. **Verify** — `mac capture screenshot` or re-inspect to confirm result
6. **End session** — `mac session end`

## Command Reference

### Session
| Command | Description |
|---------|-------------|
| `mac session start` | Start a new automation session |
| `mac session get` | Get current session info |
| `mac session list` | List all sessions |
| `mac session end` | End current session |

### Application
| Command | Description |
|---------|-------------|
| `mac app launch <bundle_id>` | Launch app (e.g. `com.apple.calculator`) |
| `mac app activate <bundle_id>` | Bring app to front |
| `mac app current` | Get frontmost app info |
| `mac app list` | List running apps |
| `mac app terminate <bundle_id>` | Terminate app (requires `--allow-dangerous`) |

### Element
| Command | Description |
|---------|-------------|
| `mac element inspect` | List all visible UI elements with refs (e0, e1, ...) |
| `mac element find <locator>` | Find element by locator value |
| `mac element click <ref>` | Click element (e.g. `e5`) |
| `mac element right-click <ref>` | Right-click element |
| `mac element double-click <ref>` | Double-click element |
| `mac element type <ref> <text>` | Type text into element |
| `mac element scroll <ref> [up\|down\|left\|right]` | Scroll element |
| `mac element hover <ref>` | Hover over element |
| `mac element drag <source> <target>` | Drag from source to target element |

### Input (no element target)
| Command | Description |
|---------|-------------|
| `mac input key <key>` | Press key (return, space, tab, escape, etc.) |
| `mac input hotkey <combo>` | Key combo (e.g. `command+c`, `command+shift+s`) |
| `mac input text <text>` | Type text to focused element |

### Capture
| Command | Description |
|---------|-------------|
| `mac capture screenshot [path]` | Take screenshot (default: ./screenshot.png) |
| `mac capture screenshot --element <ref> [path]` | Screenshot a specific element |
| `mac capture screenshot --rect x,y,w,h [path]` | Screenshot a region |
| `mac capture ui-tree` | Get raw UI element tree (XML) |

### Window
| Command | Description |
|---------|-------------|
| `mac window current` | Get frontmost window info |
| `mac window list` | List windows of managed app |
| `mac window focus <index>` | Focus window by index |

### Wait
| Command | Description |
|---------|-------------|
| `mac wait element <locator>` | Wait for element to appear |
| `mac wait window <title>` | Wait for window to appear |
| `mac wait app <bundle_id>` | Wait for app to start |

### Doctor
| Command | Description |
|---------|-------------|
| `mac doctor` | Run all diagnostics |
| `mac doctor permissions` | Check Accessibility permissions |
| `mac doctor backend` | Check Appium server and Mac2 driver |

## Global Options

| Option | Description |
|--------|-------------|
| `--session <id>` | Target a specific session (default: most recent) |
| `--strategy <strategy>` | Locator strategy: accessibility_id, name, xpath, class_name, ios_predicate |
| `--timeout <ms>` | Timeout in milliseconds (default: 120000) |
| `--pretty` | Human-friendly output (default: compact JSON for agents) |
| `--allow-dangerous` | Allow dangerous operations (e.g. app terminate) |
| `--version` | Show version |

## Response Format

Every command returns a JSON envelope:

```json
{
  "ok": true,
  "command": "element.click",
  "session_id": "s1",
  "data": {},
  "error": null,
  "meta": {
    "backend": "appium_mac2",
    "duration_ms": 1234,
    "timestamp": "2026-04-03T10:00:00Z",
    "frontmost_app": "com.apple.calculator",
    "frontmost_window": "Calculator"
  }
}
```

On error:

```json
{
  "ok": false,
  "command": "element.click",
  "error": {
    "code": "ELEMENT_NOT_FOUND",
    "message": "Element 'e5' not found",
    "retryable": true,
    "suggested_next_action": "mac element inspect",
    "doctor_hint": null
  }
}
```

## Error Recovery

When a command fails, check `error.code` and follow this recovery strategy:

| Error Code | Recovery |
|------------|----------|
| `SESSION_NOT_FOUND` | Run `mac session start` |
| `BACKEND_UNAVAILABLE` | Run `mac doctor backend`, ensure Appium is running |
| `ELEMENT_NOT_FOUND` | Run `mac element inspect` to refresh elements, find correct ref |
| `ELEMENT_REFERENCE_STALE` | Run `mac element inspect` — refs are invalidated after mutations |
| `ELEMENT_AMBIGUOUS` | Use `--first-match` or refine the locator strategy |
| `TYPE_VERIFICATION_FAILED` | Typed value didn't match; re-type or verify the target field |
| `ACTION_BLOCKED` | Add `--allow-dangerous` flag for dangerous operations |
| `TIMEOUT` | Increase `--timeout` or check if the target exists |
| `PERMISSION_DENIED` | Run `mac doctor permissions` and grant Accessibility access |

## Element References

- `mac element inspect` assigns refs: `e0`, `e1`, `e2`, ...
- Refs are **scoped to the last inspect/find** — a new inspect invalidates all previous refs
- After any mutation (click, type, etc.), refs may become stale
- Pattern: **inspect → act → re-inspect** for multi-step flows

## Safety Model

Commands are classified into three safety levels:

- **SAFE** — read-only operations (inspect, screenshot, list, wait, doctor)
- **GUARDED** — operations that modify state (click, type, launch, activate)
- **DANGEROUS** — destructive operations (terminate) — requires `--allow-dangerous`

## Common Patterns

### Calculator: 5 + 3

```bash
mac session start
mac app launch com.apple.calculator
mac element inspect                  # discover elements
mac element click e5                 # click "5"
mac element inspect                  # re-inspect after mutation
mac element click e2                 # click "+"
mac element inspect
mac element click e3                 # click "3"
mac element inspect
mac element click e8                 # click "="
mac capture screenshot ./result.png  # verify result
mac session end
```

### Type text into a search field

```bash
mac session start
mac app activate com.apple.safari
mac element inspect                      # find the search field
mac element type e12 "hello world"       # type into it
mac input hotkey command+a               # select all
mac capture screenshot ./typed.png
```

### Tips

- Always run `mac element inspect` before interacting with elements
- After any click/type, run `mac element inspect` again — refs are invalidated
- Use `mac capture screenshot` to visually verify results between steps
- Use `--pretty` when debugging interactively, omit for agent consumption
- Common bundle IDs: `com.apple.calculator`, `com.apple.Safari`, `com.apple.finder`, `com.apple.TextEdit`, `com.apple.systempreferences`
```

**Step 2: Verify the file is well-formed**

Read the file back and confirm it renders correctly as markdown.

**Step 3: Commit**

```bash
git add .claude/skills/mac-automation.md
git commit -m "Add Claude Code skill file for mac automation"
```

---

### Task 3: Add `--element` screenshot (element-level via Mac2 driver)

**Files:**
- Modify: `src/fsq_mac/adapters/appium_mac2.py:697-706` (add `screenshot_element` method)
- Modify: `src/fsq_mac/core.py:356-365` (add element param routing)
- Modify: `src/fsq_mac/daemon.py:199-201` (pass ref param)
- Modify: `src/fsq_mac/cli.py:99-100` (add `--element` arg)
- Test: `tests/test_screenshot.py` (new)

**Step 1: Write the adapter test**

Create `tests/test_screenshot.py`:

```python
"""Test screenshot variants: full, element, rect."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
from fsq_mac.models import ErrorCode


@pytest.fixture()
def adapter_with_refs(adapter, mock_driver):
    """Adapter with a stored element ref e0."""
    mock_el = MagicMock()
    mock_el.location = {"x": 100, "y": 200}
    mock_el.screenshot_as_png.return_value = b"\x89PNG_fake_data"
    adapter._store_ref("e0", mock_el)
    return adapter


def test_screenshot_element_ok(adapter_with_refs, tmp_path):
    path = str(tmp_path / "el.png")
    result = adapter_with_refs.screenshot_element("e0", path)
    assert "error_code" not in result
    assert result["path"] == path
    assert result["size_bytes"] > 0
    assert os.path.exists(path)


def test_screenshot_element_not_found(adapter, tmp_path):
    path = str(tmp_path / "el.png")
    result = adapter.screenshot_element("e99", path)
    assert result["error_code"] == ErrorCode.ELEMENT_NOT_FOUND
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_screenshot.py -v`
Expected: FAIL — `screenshot_element` method doesn't exist yet

**Step 3: Implement `screenshot_element` in adapter**

In `src/fsq_mac/adapters/appium_mac2.py`, add after the existing `screenshot` method (after line 706):

```python
    def screenshot_element(self, ref: str, path: str, strategy: str = "accessibility_id") -> dict:
        el, err = self._resolve_ref(ref, strategy)
        if err:
            return {"error_code": err, "detail": f"Element '{ref}' not found"}
        try:
            png = el.screenshot_as_png()
            with open(path, "wb") as f:
                f.write(png)
            return {"path": path, "size_bytes": len(png)}
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_screenshot.py -v`
Expected: PASS

**Step 5: Wire through core layer**

In `src/fsq_mac/core.py`, modify `capture_screenshot` (line 356) to accept and route the new `ref` parameter:

Replace the existing method with:

```python
    def capture_screenshot(self, path: str, sid: str | None = None,
                           ref: str | None = None, rect: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("capture.screenshot", sid)
        if err:
            return err
        if ref:
            result = adapter.screenshot_element(ref, path)
        elif rect:
            result = adapter.screenshot_rect(rect, path)
        else:
            result = adapter.screenshot(path)
        if result.get("error_code"):
            return error_response("capture.screenshot", result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("capture.screenshot", data=result, session_id=active, meta=self._meta(t, active))
```

**Step 6: Wire through daemon dispatch**

In `src/fsq_mac/daemon.py`, update the screenshot dispatch (line 200-201):

Replace:
```python
        if action == "screenshot":
            return core.capture_screenshot(body.get("path", "./screenshot.png"), sid)
```

With:
```python
        if action == "screenshot":
            return core.capture_screenshot(
                body.get("path", "./screenshot.png"), sid,
                ref=body.get("ref"), rect=body.get("rect"),
            )
```

**Step 7: Wire through CLI**

In `src/fsq_mac/cli.py`, add args to the screenshot subparser. After line 100 (`ss.add_argument("path", ...)`), add:

```python
    ss_group = ss.add_mutually_exclusive_group()
    ss_group.add_argument("--element", metavar="REF", help="Screenshot a specific element (e.g. e0)")
    ss_group.add_argument("--rect", metavar="x,y,w,h", help="Screenshot a region")
```

Then in the `_run()` function, update the capture section (around line 163-165):

Replace:
```python
    elif domain == "capture":
        if action == "screenshot":
            params["path"] = args.path
```

With:
```python
    elif domain == "capture":
        if action == "screenshot":
            params["path"] = args.path
            if getattr(args, "element", None):
                params["ref"] = args.element
            if getattr(args, "rect", None):
                params["rect"] = args.rect
```

**Step 8: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

**Step 9: Commit**

```bash
git add src/fsq_mac/cli.py src/fsq_mac/daemon.py src/fsq_mac/core.py src/fsq_mac/adapters/appium_mac2.py tests/test_screenshot.py
git commit -m "Add element-level screenshot via --element flag"
```

---

### Task 4: Add `--rect` screenshot (region via macOS screencapture)

**Files:**
- Modify: `src/fsq_mac/adapters/appium_mac2.py` (add `screenshot_rect` method)
- Test: `tests/test_screenshot.py` (add rect tests)

**Step 1: Add rect tests**

Append to `tests/test_screenshot.py`:

```python
def test_screenshot_rect_ok(adapter, tmp_path):
    path = str(tmp_path / "rect.png")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # Create a fake file so size_bytes works
        with open(path, "wb") as f:
            f.write(b"\x89PNG_fake")
        result = adapter.screenshot_rect("100,200,300,400", path)
    assert "error_code" not in result
    assert result["path"] == path
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "screencapture" in call_args
    assert "-R100,200,300,400" in call_args or "-R" in call_args


def test_screenshot_rect_invalid_format(adapter, tmp_path):
    path = str(tmp_path / "rect.png")
    result = adapter.screenshot_rect("invalid", path)
    assert result["error_code"] == ErrorCode.INVALID_ARGUMENT
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_screenshot.py::test_screenshot_rect_ok -v`
Expected: FAIL — `screenshot_rect` method doesn't exist yet

**Step 3: Implement `screenshot_rect` in adapter**

In `src/fsq_mac/adapters/appium_mac2.py`, add after the `screenshot_element` method:

```python
    def screenshot_rect(self, rect: str, path: str) -> dict:
        parts = rect.split(",")
        if len(parts) != 4:
            return {"error_code": ErrorCode.INVALID_ARGUMENT,
                    "detail": f"Expected x,y,w,h but got: {rect}"}
        try:
            x, y, w, h = [int(p.strip()) for p in parts]
        except ValueError:
            return {"error_code": ErrorCode.INVALID_ARGUMENT,
                    "detail": f"Non-integer values in rect: {rect}"}
        try:
            result = subprocess.run(
                ["screencapture", f"-R{x},{y},{w},{h}", path],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if result.returncode != 0:
                return {"error_code": ErrorCode.INTERNAL_ERROR,
                        "detail": f"screencapture failed: {result.stderr.strip()}"}
            size = os.path.getsize(path) if os.path.exists(path) else 0
            return {"path": path, "size_bytes": size}
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}
```

Also add `import os` at the top of the file if not already present (it is not — check line 10-17). Add it in the imports section:

```python
import os
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_screenshot.py -v`
Expected: All screenshot tests PASS

**Step 5: Run all tests for regressions**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/fsq_mac/adapters/appium_mac2.py tests/test_screenshot.py
git commit -m "Add region screenshot via --rect flag using screencapture"
```

---

### Task 5: Update route tests for screenshot variants

**Files:**
- Modify: `tests/test_routes.py` (update screenshot body to include new params)

**Step 1: Verify existing route test still passes**

The existing `test_routes.py` already tests `("capture", "screenshot")` with `body` containing `"path": "/tmp/test.png"`. The modified `capture_screenshot` core method now accepts `ref` and `rect` as optional params (defaulting to `None`), so the existing test should still pass.

Run: `uv run pytest tests/test_routes.py -v`
Expected: All 33 route tests PASS

**Step 2: Commit (only if changes were needed)**

If tests pass with no changes, skip this commit. The backward-compatible signature (`ref=None, rect=None`) means nothing needs to change.

---

### Task 6: Final verification

**Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

**Step 2: Verify `--version` works**

Run: `uv run mac --version`
Expected: `fsq-mac 0.1.0`

**Step 3: Verify `--element` and `--rect` appear in help**

Run: `uv run mac capture screenshot --help`
Expected: Shows `--element REF` and `--rect x,y,w,h` options

**Step 4: Verify skill file exists**

Run: `cat .claude/skills/mac-automation.md | head -5`
Expected: Shows the skill file header

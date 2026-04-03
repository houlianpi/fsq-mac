# Phase 0: User-Perceivable Foundation — Design Document

> Date: 2026-04-03
> Status: Approved

## Goal

Make fsq-mac usable as a real tool, not just a script. Three deliverables:

1. **0a** — CLI packaging polish (`--version`, verify install paths)
2. **0b** — Claude Code skill file for agent-first usage
3. **0c** — Region and element screenshots

---

## 0a: CLI Packaging Polish

### Changes

- Add `--version` flag to argparse root parser → `fsq-mac 0.1.0`
- Ensure `prog="mac"` in argparse so help text shows `mac` not `cli.py`
- Verify: `uv tool install .`, `pipx install .`, `pip install -e .` all produce a working `mac` command

### Files

- `src/fsq_mac/cli.py` — add `--version` argument

---

## 0b: Claude Code Skill File

### Deliverable

Create `.claude/skills/mac-automation.md` — a skill file that teaches Claude Code how to use the `mac` CLI.

### Contents

- Overview: what fsq-mac does, when to use it
- Workflow pattern: `session start` → `element inspect` → act → verify → `session end`
- Command reference: all domains/actions with arguments
- Error recovery strategies: map each `error.code` to a recovery action
  - `ELEMENT_REFERENCE_STALE` → re-inspect
  - `ELEMENT_NOT_FOUND` → re-inspect, check target exists
  - `BACKEND_UNAVAILABLE` → `mac doctor backend`
  - `SESSION_NOT_FOUND` → `mac session start`
- Common flow templates: calculator, form filling, app launch + interact
- Safety model: SAFE / GUARDED / DANGEROUS
- Tips: `--pretty` for human debugging, raw JSON for agent consumption

### Files

- `.claude/skills/mac-automation.md` (new)

---

## 0c: Region Screenshot

### Approach

Two new options for `mac capture screenshot`:

| Option | Implementation | Dependencies |
|--------|---------------|--------------|
| `--element <ref>` | `WebElement.screenshot_as_png()` via W3C WebDriver protocol | None (Appium Mac2 supports it) |
| `--rect x,y,w,h` | macOS `screencapture -R x,y,w,h` | None (native macOS command) |

### Data Flow: `--element e0`

1. CLI sends `{ref: "e0", path: "./result.png"}`
2. Core calls `adapter.screenshot_element("e0", path)`
3. Adapter resolves ref → WebElement, calls `element.screenshot_as_png()`
4. Writes PNG, returns `{path, size_bytes}`

### Data Flow: `--rect 100,200,300,400`

1. CLI sends `{rect: "100,200,300,400", path: "./result.png"}`
2. Core calls `adapter.screenshot_rect(100, 200, 300, 400, path)`
3. Adapter runs `screencapture -R 100,200,300,400 <path>`
4. Returns `{path, size_bytes}`

### Files

- `src/fsq_mac/cli.py` — add `--element` and `--rect` args
- `src/fsq_mac/daemon.py` — pass new params through dispatch
- `src/fsq_mac/core.py` — route to appropriate screenshot method
- `src/fsq_mac/adapters/appium_mac2.py` — add `screenshot_element()` and `screenshot_rect()`

### Mutual Exclusion

`--element` and `--rect` are mutually exclusive. If both are provided, CLI returns an error.

---

## Non-Goals (Phase 0)

- No lazy locators (Phase 2)
- No auto-wait (Phase 2)
- No adapter abstraction (Phase 1)
- No test coverage improvements (Phase 1)
- No CI/CD (Phase 3)

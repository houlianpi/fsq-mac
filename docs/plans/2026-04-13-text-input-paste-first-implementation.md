# Text Input Paste-First Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement paste-first text input for `input_text()` and `type_text()` with explicit `keys|paste|auto` control, tests, and docs.

**Architecture:** Thread a new `input_method` parameter from CLI to daemon to core to the Appium Mac2 adapter. Keep strategy selection entirely inside `AppiumMac2Adapter`, where `paste` and first-version `auto` use clipboard plus paste hotkey, while `keys` preserves the existing key-injection behavior.

**Tech Stack:** Python 3.10+, argparse, Starlette, Appium Mac2 WebDriver, subprocess clipboard helpers, pytest, unittest.mock

---

### Task 1: Add failing CLI and core tests for `input_method`

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_core.py`

**Steps:**
1. Add parser tests proving `mac input text` and `mac element type` accept `--input-method`.
2. Add run/core tests proving the parsed value is passed through to daemon/core/adapter.
3. Run the targeted tests and confirm they fail because the argument does not exist yet.

### Task 2: Add failing adapter tests for paste-first behavior

**Files:**
- Modify: `tests/test_adapter_methods.py`

**Steps:**
1. Add targeted tests for `input_text(..., input_method="paste")` and `type_text(..., input_method="paste")`.
2. Assert clipboard save/write/restore helpers are used and `command+v` is sent.
3. Add a test that default `input_text()` behavior uses paste.
4. Add a test that `input_method="keys"` preserves the existing key-injection path.
5. Run the targeted adapter tests and confirm they fail first.

### Task 3: Implement `input_method` in CLI, daemon, and core

**Files:**
- Modify: `src/fsq_mac/cli.py`
- Modify: `src/fsq_mac/daemon.py`
- Modify: `src/fsq_mac/core.py`

**Steps:**
1. Extend CLI parsers for `input text` and `element type` with `--input-method` defaulting to `paste`.
2. Pass the new field through `_run()`.
3. Update daemon dispatch and core methods to forward `input_method` unchanged.
4. Run the targeted CLI/core tests and make them pass.

### Task 4: Implement paste-first adapter behavior

**Files:**
- Modify: `src/fsq_mac/adapters/appium_mac2.py`

**Steps:**
1. Add minimal clipboard helper methods in the adapter.
2. Add a paste helper that saves clipboard content, writes target text, sends paste hotkey, and restores clipboard in `finally`.
3. Update `input_text()` to default to `paste`, keep `keys`, and map first-version `auto` to `paste`.
4. Update `type_text()` to support the same `input_method` contract while preserving verification and geometry behavior.
5. Run targeted adapter tests and make them pass.

### Task 5: Update docs

**Files:**
- Modify: `docs/cli-reference.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/architecture.md`

**Steps:**
1. Document `--input-method paste|keys|auto` for text-writing commands.
2. Explain that default text entry is now stable final-text insertion via paste.
3. Note that `keys` remains available when callers need key-event semantics.

### Task 6: Verify and ship

**Files:**
- Review only

**Steps:**
1. Run narrow tests first.
2. Run the full test suite.
3. Review the diff for accidental scope growth.
4. Commit implementation, tests, and docs together.
5. Push the branch.

# Phase 3 Checkpoint 1: Trace Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a full file-based trace loop for `fsq-mac`: start recording, execute commands, stop recording, replay the saved trace, and generate a static viewer.

**Architecture:** Introduce a dedicated `trace.py` runtime module and on-disk manifest models. Thread a new `trace` command surface through CLI and daemon, and wrap normal command execution in daemon-managed trace capture so existing product semantics remain the single execution path.

**Tech Stack:** Python 3.10+, argparse, dataclasses, pathlib, json, Starlette, pytest, unittest.mock, static HTML generation

---

### Task 1: Add trace models and manifest helpers

**Files:**
- Modify: `src/fsq_mac/models.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

Add tests for:

```python
def test_trace_run_to_dict_contains_steps():
    run = TraceRun(trace_id="t1", output_dir="/tmp/t1")
    assert run.to_dict()["trace_id"] == "t1"


def test_trace_step_not_replayable_error_code_value():
    assert ErrorCode.TRACE_STEP_NOT_REPLAYABLE.value == "TRACE_STEP_NOT_REPLAYABLE"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -q`
Expected: FAIL because trace models and error code do not exist yet.

**Step 3: Write minimal implementation**

Add:

- `ErrorCode.TRACE_STEP_NOT_REPLAYABLE`
- `TraceArtifacts`
- `TraceStep`
- `TraceRun`

Keep serialization minimal and transport-friendly.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/models.py tests/test_models.py
git commit -m "Add trace manifest models"
```

---

### Task 2: Add CLI and route support for `trace.*`

**Files:**
- Modify: `src/fsq_mac/cli.py`
- Modify: `src/fsq_mac/daemon.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_routes.py`

**Step 1: Write the failing test**

Add parser and `_run()` tests for:

- `mac trace start`
- `mac trace start /tmp/my-trace`
- `mac trace stop`
- `mac trace status`
- `mac trace replay artifacts/traces/t1`
- `mac trace viewer artifacts/traces/t1`

Add route coverage for:

- `trace.start`
- `trace.stop`
- `trace.status`
- `trace.replay`
- `trace.viewer`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py tests/test_routes.py -q`
Expected: FAIL because the CLI and routes do not know the `trace` domain.

**Step 3: Write minimal implementation**

Add the `trace` domain and map arguments through `_run()` and daemon dispatch.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py tests/test_routes.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/cli.py src/fsq_mac/daemon.py tests/test_cli.py tests/test_routes.py
git commit -m "Add trace command surface"
```

---

### Task 3: Create `trace.py` runtime for manifest persistence

**Files:**
- Create: `src/fsq_mac/trace.py`
- Test: `tests/test_trace.py`

**Step 1: Write the failing test**

Add tests for:

- creating a trace directory and manifest
- loading an existing manifest
- appending a step to `trace.json`
- computing artifact file paths

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_trace.py -q`
Expected: FAIL because the module does not exist yet.

**Step 3: Write minimal implementation**

Create `trace.py` with a `TraceStore` or equivalent helper that manages:

- `start_trace()`
- `stop_trace()`
- `load_trace()`
- `append_step()`
- `viewer_path()`

Persist `trace.json` after every step append.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_trace.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/trace.py tests/test_trace.py
git commit -m "Add trace store runtime"
```

---

### Task 4: Implement daemon-managed recording lifecycle

**Files:**
- Modify: `src/fsq_mac/daemon.py`
- Modify: `tests/test_daemon.py`
- Modify: `tests/test_routes.py`
- Test: `tests/test_trace.py`

**Step 1: Write the failing test**

Add tests for:

- `trace.start` creates active trace state
- `trace.status` reports active trace metadata
- `trace.stop` finalizes the current trace
- product commands are recorded while tracing is active
- `trace.*` commands do not record themselves

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_daemon.py tests/test_trace.py tests/test_routes.py -q`
Expected: FAIL because daemon does not manage trace state yet.

**Step 3: Write minimal implementation**

Add daemon-level active trace state and wrap recordable command execution with:

- pre-capture artifact attempt
- command execution
- post-capture artifact attempt
- manifest append

Artifact capture should be best-effort only.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_daemon.py tests/test_trace.py tests/test_routes.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/daemon.py tests/test_daemon.py tests/test_trace.py tests/test_routes.py
git commit -m "Record commands into trace runs"
```

---

### Task 5: Add replay execution

**Files:**
- Modify: `src/fsq_mac/trace.py`
- Modify: `src/fsq_mac/daemon.py`
- Modify: `tests/test_trace.py`
- Modify: `tests/test_daemon.py`

**Step 1: Write the failing test**

Add tests for:

- replaying a trace with one replayable step
- failing on a non-replayable step with `TRACE_STEP_NOT_REPLAYABLE`
- stopping replay on first execution error

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_trace.py tests/test_daemon.py -q`
Expected: FAIL because replay is not implemented.

**Step 3: Write minimal implementation**

Add replay helpers that:

- load the manifest
- iterate steps in order
- map commands back through daemon/core dispatch
- stop on first failure

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_trace.py tests/test_daemon.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/trace.py src/fsq_mac/daemon.py tests/test_trace.py tests/test_daemon.py
git commit -m "Add trace replay"
```

---

### Task 6: Add static viewer generation

**Files:**
- Modify: `src/fsq_mac/trace.py`
- Modify: `tests/test_trace.py`

**Step 1: Write the failing test**

Add tests for:

- generating `viewer/index.html`
- embedding trace metadata and step command names
- handling traces with missing optional artifacts

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_trace.py -q`
Expected: FAIL because viewer generation does not exist.

**Step 3: Write minimal implementation**

Generate a static HTML file from the manifest with:

- metadata header
- step list
- artifact links
- simple tree change summary

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_trace.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/trace.py tests/test_trace.py
git commit -m "Add static trace viewer"
```

---

### Task 7: Run focused and full verification

**Files:**
- Review: `src/fsq_mac/*.py`
- Review: `tests/*.py`

**Step 1: Run focused suites first**

Run:

```bash
pytest tests/test_models.py tests/test_cli.py tests/test_routes.py tests/test_trace.py tests/test_daemon.py -q
```

Expected: PASS.

**Step 2: Run broader relevant suites**

Run:

```bash
pytest tests/test_core.py tests/test_client.py tests/test_formatters.py -q
```

Expected: PASS.

**Step 3: Run full suite**

Run:

```bash
pytest -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add src tests docs/plans
git commit -m "Implement phase 3 trace loop checkpoint"
```

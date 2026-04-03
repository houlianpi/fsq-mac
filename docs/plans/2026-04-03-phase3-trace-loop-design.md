# Phase 3 Checkpoint 1: Trace Loop — Design Document

> Date: 2026-04-03
> Status: Approved

## Goal

Implement the first developer-experience checkpoint of Phase 3:

1. Operation recording
2. Trace replay
3. Minimal static trace viewer

This checkpoint deliberately excludes shell completion, CI/JUnit integration, and Space isolation. Those remain a second checkpoint after the trace loop is stable.

---

## Architecture Choice

Use a file-based trace run model.

Instead of introducing a long-lived in-memory recorder subsystem first, the daemon will own a small trace runtime that writes trace state and artifacts to disk as each command completes. Replay then consumes that on-disk trace directly. This keeps the implementation aligned with the current daemon-centered architecture and avoids inventing a separate execution engine.

The trace loop is therefore:

1. `trace.start` creates a trace directory and marks tracing active in daemon state
2. normal product commands run through the existing core
3. after each recordable command, the daemon appends a step to `trace.json`
4. `trace.stop` finalizes the trace run
5. `trace.replay` loads the saved steps and replays them via the same core methods
6. `trace.viewer` generates a static HTML report from the trace directory

---

## Scope

### Included

- `mac trace start [dir]`
- `mac trace stop`
- `mac trace status`
- `mac trace replay <trace_dir_or_json>`
- `mac trace viewer <trace_dir>`
- persisted JSON trace manifest
- per-step screenshots and UI tree captures
- replay that stops on first failure
- static HTML viewer generation

### Excluded

- low-level OS event recording
- code generation
- live web viewer server
- shell completion
- GitHub Actions and JUnit XML
- automatic Space isolation scripts

---

## Data Model

### Trace Directory Layout

Use a deterministic on-disk layout under a default root:

- `artifacts/traces/<trace_id>/trace.json`
- `artifacts/traces/<trace_id>/steps/001-before.png`
- `artifacts/traces/<trace_id>/steps/001-after.png`
- `artifacts/traces/<trace_id>/steps/001-before-tree.xml`
- `artifacts/traces/<trace_id>/steps/001-after-tree.xml`
- `artifacts/traces/<trace_id>/viewer/index.html`

Users may override the root directory through `trace start [dir]`.

### Trace Manifest

Add lightweight trace dataclasses to `models.py`:

- `TraceRun`
- `TraceStep`
- `TraceArtifacts`

Required top-level fields:

- `trace_id`
- `created_at`
- `backend`
- `session_id`
- `status`
- `output_dir`
- `steps`

Required step fields:

- `index`
- `command`
- `args`
- `locator_query`
- `replayable`
- `started_at`
- `duration_ms`
- `ok`
- `error`
- `artifacts`

---

## Recording Behavior

### What Gets Recorded

Only product commands are recordable. Trace control commands do not record themselves.

Recordable command families in checkpoint 1:

- `app.*`
- `window.*`
- `element.*`
- `input.*`
- `capture.screenshot`
- `assert.*`
- `menu.click`
- `wait.*`

`session.start` and `session.end` remain out of band for the first checkpoint to avoid recursive session lifecycle coupling inside replay.

### How Steps Are Captured

For each recordable command:

1. capture pre-state screenshot and UI tree when an active adapter exists
2. execute the command normally
3. capture post-state screenshot and UI tree when possible
4. append a serialized step to `trace.json`

If pre/post artifact capture fails, the original command result must still win. Artifact failures are recorded in trace metadata rather than breaking the user command.

### Locator Persistence

Replayable steps must prefer stable locator data.

Rules:

1. If the original command used explicit lazy locator fields, store them as `locator_query`
2. If the command used a static ref and the current response or arguments expose a stable `locator_hint`, convert it into a `locator_query`
3. If no stable locator can be derived, mark the step `replayable=false`

This avoids pretending that `e0` is replay-safe across runs.

---

## Replay Behavior

Replay is strict and deterministic.

Rules:

1. steps run in original order
2. non-replayable steps fail fast with a structured replay error
3. the first execution failure stops the replay
4. replay returns a structured summary with completed step count and the failing step when applicable

Replay uses the same `AutomationCore` methods rather than bypassing product semantics. This keeps response envelopes, safety handling, and adapter behavior consistent with normal execution.

---

## Viewer Behavior

The first viewer is static HTML generated into `viewer/index.html`.

It shows:

- trace metadata
- step list with status and duration
- before/after screenshots
- command name and normalized locator
- raw error summary when present
- a simple before/after tree change summary

The tree diff is intentionally shallow in checkpoint 1. It only reports:

- before and after text lengths
- whether content changed
- first differing line numbers when practical

This keeps the viewer lightweight while still being useful for post-failure debugging.

---

## Placement

### New Module

Create a dedicated `trace.py` module to keep trace runtime logic out of `core.py` and `daemon.py`.

Responsibilities:

- trace directory setup
- manifest load/save
- active trace state
- artifact path generation
- replay orchestration helpers
- viewer HTML generation

### Existing Modules

- `cli.py`: add `trace` domain
- `daemon.py`: manage trace lifecycle and wrap recordable commands
- `core.py`: expose replay helpers only if required by routing; avoid embedding trace persistence here
- `models.py`: trace dataclasses and serialization helpers

---

## Error Model

Checkpoint 1 can reuse existing error codes where possible:

- `INVALID_ARGUMENT` for bad paths or malformed manifests
- `INTERNAL_ERROR` for trace persistence or viewer generation failures
- `BACKEND_UNAVAILABLE` when replay requires an unavailable adapter/session

Add one dedicated error code for replay semantics:

- `TRACE_STEP_NOT_REPLAYABLE`

This keeps replay failure machine-readable without overloading `INVALID_ARGUMENT`.

---

## Testing Strategy

Implement in four TDD slices:

1. CLI and route surface for `trace.*`
2. trace models and manifest persistence
3. daemon/core recording and replay behavior
4. viewer generation and edge cases

Target tests:

- parser and `_run()` mapping tests
- route dispatch coverage
- manifest read/write unit tests
- record/no-record behavior tests
- replay success/failure tests
- viewer file generation tests

The first green bar should come from CLI and model tests before any daemon integration work.

---

## Non-Goals

- No live interactive trace server
- No code export or codegen
- No session auto-bootstrap from trace files beyond current daemon behavior
- No rich DOM-style structural diffing
- No CI artifact upload yet

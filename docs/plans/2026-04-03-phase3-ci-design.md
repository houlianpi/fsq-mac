# Phase 3 Checkpoint 2: CI + JUnit — Design Document

> Date: 2026-04-03
> Status: Approved

## Goal

Implement the next engineering checkpoint of Phase 3:

1. GitHub Actions workflow
2. JUnit XML test output
3. CI artifact upload for test diagnostics

This checkpoint does not attempt to run real macOS automation traces in CI. It focuses on stable repository-level validation and machine-readable test output.

---

## Architecture Choice

Use a single repository workflow with one primary test job.

The workflow will run on every `push` and `pull_request`, install dependencies with `uv`, execute the existing pytest suite, emit JUnit XML, and upload CI artifacts. This keeps the first CI integration small, reviewable, and aligned with the current repository shape.

---

## Scope

### Included

- `.github/workflows/ci.yml`
- `pytest --junitxml=test-results/junit.xml`
- upload of `test-results/junit.xml`
- upload of `artifacts/` when present
- README note documenting the CI behavior

### Excluded

- multi-version Python matrix
- lint / typecheck jobs
- real Appium or macOS automation execution in CI
- trace replay as a required CI step
- JUnit generation from trace replay results

---

## Workflow Behavior

### Triggers

Run on:

- `push`
- `pull_request`

### Environment

Use `ubuntu-latest`.

This repository's core automated tests are Python-level tests and do not require a real macOS Appium environment. Using Ubuntu keeps the workflow faster and cheaper while still covering the current automated validation surface.

### Steps

1. checkout repository
2. install `uv`
3. set up Python
4. run `uv sync --group dev`
5. run `uv run pytest tests/ --junitxml=test-results/junit.xml`
6. upload JUnit XML artifact
7. upload `artifacts/` directory if it exists

Artifact upload should run even when tests fail so CI preserves diagnostics.

---

## JUnit Output

Use pytest's built-in JUnit XML support.

Output path:

- `test-results/junit.xml`

This is sufficient for GitHub artifact retention and later integration with PR annotations or external test dashboards.

---

## Artifact Policy

Upload two artifact groups:

- `junit-results`
- `runtime-artifacts`

`runtime-artifacts` should be conditional on the local `artifacts/` directory existing. This avoids noise on runs that do not generate runtime traces.

---

## README Update

Add one short CI section covering:

- workflow location
- test command used in CI
- JUnit output path
- artifact upload behavior

Keep the documentation short. The workflow file should remain the source of truth.

---

## Testing Strategy

Implement in TDD slices:

1. tests for workflow file presence and key commands
2. tests or assertions for README CI documentation
3. workflow implementation
4. focused verification by inspecting workflow YAML and running the existing pytest suite locally

Because GitHub Actions cannot be executed inside the unit test suite, validation is structural rather than end-to-end.

---

## Risks

- Uploading `artifacts/` may produce empty or noisy uploads if future tests start generating many runtime files. The first version keeps this simple and conditional.
- Ubuntu CI does not validate real Mac2 runtime behavior. That remains acceptable because the current automated suite is already mocked and platform-independent.

---

## Non-Goals

- No workflow matrix
- No PR summary annotations
- No flaky integration tests against live Appium
- No trace-to-JUnit conversion yet

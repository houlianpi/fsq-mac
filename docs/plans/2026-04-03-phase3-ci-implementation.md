# Phase 3 Checkpoint 2: CI + JUnit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a repository GitHub Actions workflow that runs pytest in CI, emits JUnit XML, and uploads CI artifacts.

**Architecture:** Introduce a single `.github/workflows/ci.yml` job that uses `uv` for dependency installation and pytest's built-in JUnit XML output for machine-readable test results. Keep this checkpoint repository-level only and avoid live macOS automation dependencies.

**Tech Stack:** GitHub Actions, YAML, uv, Python 3.11, pytest, upload-artifact

---

### Task 1: Add structural tests for CI workflow expectations

**Files:**
- Modify: `tests/test_cli.py` or create a focused CI test file if cleaner
- Test: `tests/test_ci_workflow.py`

**Step 1: Write the failing test**

Add tests for:

```python
def test_ci_workflow_exists():
    assert Path('.github/workflows/ci.yml').exists()


def test_ci_workflow_runs_pytest_with_junit():
    text = Path('.github/workflows/ci.yml').read_text()
    assert '--junitxml=test-results/junit.xml' in text
    assert 'uv sync --group dev' in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ci_workflow.py -q`
Expected: FAIL because the workflow file does not exist yet.

**Step 3: Write minimal implementation**

Create the workflow file with placeholders sufficient to satisfy the test.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ci_workflow.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add .github/workflows/ci.yml tests/test_ci_workflow.py
git commit -m "Add CI workflow scaffold"
```

---

### Task 2: Add README documentation expectations

**Files:**
- Modify: `README.md`
- Modify: `tests/test_ci_workflow.py`

**Step 1: Write the failing test**

Add a test for:

```python
def test_readme_documents_ci_workflow():
    text = Path('README.md').read_text()
    assert 'GitHub Actions' in text
    assert 'test-results/junit.xml' in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ci_workflow.py -q`
Expected: FAIL because README does not mention CI yet.

**Step 3: Write minimal implementation**

Add a short CI section to README.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ci_workflow.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add README.md tests/test_ci_workflow.py
git commit -m "Document CI workflow"
```

---

### Task 3: Finalize workflow artifact upload behavior

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_ci_workflow.py`

**Step 1: Write the failing test**

Add tests asserting the workflow uploads:

- `test-results/junit.xml`
- `artifacts/`
- uses `if: always()` for JUnit upload

Example:

```python
def test_ci_workflow_uploads_junit_and_artifacts():
    text = Path('.github/workflows/ci.yml').read_text()
    assert 'test-results/junit.xml' in text
    assert 'artifacts/' in text
    assert 'if: always()' in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ci_workflow.py -q`
Expected: FAIL until artifact upload steps are present.

**Step 3: Write minimal implementation**

Complete the workflow with `actions/upload-artifact` steps.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ci_workflow.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add .github/workflows/ci.yml tests/test_ci_workflow.py
git commit -m "Add CI artifact uploads"
```

---

### Task 4: Run repository validation

**Files:**
- No new files

**Step 1: Run focused tests**

Run: `pytest tests/test_ci_workflow.py -q`
Expected: PASS.

**Step 2: Run broader suite**

Run: `pytest tests/test_models.py tests/test_cli.py tests/test_routes.py tests/test_trace.py tests/test_core.py tests/test_daemon.py tests/test_ci_workflow.py -q`
Expected: PASS.

**Step 3: Review workflow YAML manually**

Check that:

- triggers are `push` and `pull_request`
- `uv sync --group dev` is present
- pytest writes JUnit XML to `test-results/junit.xml`
- artifact upload always preserves results

**Step 4: Commit**

```bash
git add .github/workflows/ci.yml README.md tests/test_ci_workflow.py
git commit -m "Finalize phase 3 CI integration"
```

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path


def test_ci_workflow_exists():
    assert Path(".github/workflows/ci.yml").exists()


def test_ci_workflow_runs_pytest_with_junit():
    text = Path(".github/workflows/ci.yml").read_text()
    assert "uv sync --group dev" in text
    assert "--junitxml=test-results/junit.xml" in text


def test_ci_workflow_runs_on_main_only_for_pushes():
    text = Path(".github/workflows/ci.yml").read_text()
    assert "branches: [main]" in text



def test_readme_documents_ci_workflow():
    text = Path("README.md").read_text()
    assert "GitHub Actions" in text
    assert "test-results/junit.xml" in text


def test_ci_workflow_uploads_junit_and_artifacts():
    text = Path(".github/workflows/ci.yml").read_text()
    assert "if: always()" in text
    assert "test-results/junit.xml" in text
    assert "artifacts/" in text


def test_publish_workflow_exists():
    assert Path(".github/workflows/publish.yml").exists()


def test_publish_workflow_uses_tag_trigger_and_ci_gate():
    text = Path(".github/workflows/publish.yml").read_text()
    assert 'tags: ["v*"]' in text or "tags:\n      - 'v*'" in text or 'tags:\n      - "v*"' in text
    assert "needs: test" in text
    assert "strategy:" in text
    assert "python-version" in text


def test_publish_workflow_builds_and_publishes_to_pypi():
    text = Path(".github/workflows/publish.yml").read_text()
    assert "uv build" in text
    assert "uv sync --group dev" in text
    assert "uv run pytest tests/" in text
    assert "pypa/gh-action-pypi-publish" in text
    assert "id-token: write" in text

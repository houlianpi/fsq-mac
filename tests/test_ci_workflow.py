# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path


def test_ci_workflow_exists():
    assert Path(".github/workflows/ci.yml").exists()


def test_ci_workflow_runs_pytest_with_junit():
    text = Path(".github/workflows/ci.yml").read_text()
    assert "uv sync --group dev" in text
    assert "--junitxml=test-results/junit.xml" in text



def test_readme_documents_ci_workflow():
    text = Path("README.md").read_text()
    assert "GitHub Actions" in text
    assert "test-results/junit.xml" in text


def test_ci_workflow_uploads_junit_and_artifacts():
    text = Path(".github/workflows/ci.yml").read_text()
    assert "if: always()" in text
    assert "test-results/junit.xml" in text
    assert "artifacts/" in text

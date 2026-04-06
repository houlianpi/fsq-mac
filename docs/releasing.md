# Releasing To PyPI

This document describes how `fsq-mac` is published to PyPI.

## Overview

Publishing is automated by [publish.yml](../.github/workflows/publish.yml).

Release flow:

1. Push a Git tag matching `v*`, for example `v0.1.1`
2. GitHub Actions runs the full test matrix on Python `3.10`, `3.11`, and `3.12`
3. If all tests pass, the workflow builds the wheel and source distribution
4. The workflow publishes the package to PyPI using Trusted Publishing

## Prerequisites

Before the first release, configure PyPI Trusted Publishing for this repository.

You need:

- A PyPI project named `fsq-mac`
- Maintainer access to that PyPI project
- Admin access to the GitHub repository

## Configure PyPI Trusted Publishing

In PyPI:

1. Open the `fsq-mac` project
2. Go to `Manage` -> `Publishing`
3. Add a new trusted publisher
4. Set the GitHub owner/repository for this repo
5. Set the workflow file to `.github/workflows/publish.yml`
6. Set the environment name to `pypi`

The workflow already requests the required GitHub OIDC permission:

```yaml
permissions:
  contents: read
  id-token: write
```

## Create A Release

Choose the next version and make sure it matches `pyproject.toml`.

Then create and push the tag:

```bash
git tag v0.1.1
git push origin v0.1.1
```

Notes:

- The tag format must start with `v`
- The package version in `pyproject.toml` must not already exist on PyPI
- If the version already exists, PyPI will reject the upload

## What The Workflow Does

The publish workflow:

- runs on `push` of tags matching `v*`
- runs the same Python version matrix as CI
- installs dependencies with `uv sync --group dev`
- runs `uv run pytest tests/ ...`
- builds distributions with `uv build`
- publishes with `pypa/gh-action-pypi-publish`

## Verifying A Release

After the workflow completes:

1. Check the GitHub Actions run for the `Publish` workflow
2. Confirm the `test` job passed on all Python versions
3. Confirm the `publish` job completed successfully
4. Verify the new version appears on PyPI
5. In a clean environment, confirm installation works:

```bash
uv pip install fsq-mac
mac --version
```

## Common Failure Modes

### Version already exists on PyPI

Symptom:

- publish step fails with a duplicate file or duplicate version error

Fix:

- bump `version` in `pyproject.toml`
- commit the change
- create a new tag

### Trusted Publishing is not configured

Symptom:

- publish step fails during PyPI authentication

Fix:

- verify the PyPI trusted publisher configuration
- make sure the workflow path is `.github/workflows/publish.yml`
- make sure the environment name is `pypi`

### Tests fail on the tag

Symptom:

- `publish` job does not start because `test` failed

Fix:

- inspect the failed matrix job in GitHub Actions
- fix the issue on `main`
- create a new tag from the corrected commit

### Tag does not trigger publish

Symptom:

- no `Publish` workflow run appears

Fix:

- confirm the tag name starts with `v`
- confirm the tag was pushed to GitHub, not only created locally
- check that `.github/workflows/publish.yml` exists on the tagged commit

## Recommended Release Checklist

Before tagging:

- `pyproject.toml` version is updated
- local tests are green
- docs changes for the release are committed
- the release commit is on `main`

After tagging:

- `Publish` workflow passes
- package appears on PyPI
- fresh install works

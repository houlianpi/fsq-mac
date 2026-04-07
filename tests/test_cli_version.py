# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for the --version CLI flag."""

from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from fsq_mac import __version__
from fsq_mac.cli import main


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """--version prints the exported package version and exits."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == f"fsq-mac {__version__}"


def test_module_version_matches_pyproject() -> None:
    """The exported module version stays aligned with packaging metadata."""
    with Path("pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    assert __version__ == pyproject["project"]["version"]

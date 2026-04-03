# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for the --version CLI flag."""

from __future__ import annotations

import pytest

from fsq_mac.cli import main


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """--version prints 'fsq-mac 0.1.0' and exits."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "fsq-mac" in captured.out
    assert "0.1.0" in captured.out

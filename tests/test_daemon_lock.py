# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Daemon lock file prevents concurrent start race conditions."""

from __future__ import annotations

import fcntl
import os
import tempfile

import pytest


def test_fcntl_lock_blocks_concurrent():
    """An exclusive fcntl lock should prevent a second acquirer."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".lock") as f:
        lock_path = f.name

    try:
        fd1 = open(lock_path, "w")
        fcntl.flock(fd1, fcntl.LOCK_EX)

        fd2 = open(lock_path, "w")
        # Non-blocking attempt should fail (raise or return immediately)
        with pytest.raises(BlockingIOError):
            fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)

        fcntl.flock(fd1, fcntl.LOCK_UN)
        fd1.close()

        # Now it should succeed
        fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd2, fcntl.LOCK_UN)
        fd2.close()
    finally:
        os.unlink(lock_path)

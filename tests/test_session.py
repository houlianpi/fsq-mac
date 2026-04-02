# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Session lifecycle: monotonic IDs, stale cleanup, end nonexistent."""

from __future__ import annotations

import json

import fsq_mac.session as session_module


def test_monotonic_ids(session_manager):
    """Session IDs must be monotonically increasing."""
    s1 = session_manager.start()
    s2 = session_manager.start()
    # End s1, then start s3 — should not reuse s1's number
    session_manager.end(s1.session_id)
    s3 = session_manager.start()

    ids = [int(s.session_id[1:]) for s in [s1, s2, s3]]
    assert ids == sorted(ids)
    assert len(set(ids)) == 3  # all unique


def test_stale_cleanup_high_water(tmp_path, mock_config, monkeypatch):
    """Stale session files should set the high-water mark for next IDs."""
    monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
    # Pre-create a stale session file with id s10
    (tmp_path / "s10.json").write_text(json.dumps({"session_id": "s10"}))

    sm = session_module.SessionManager(mock_config)
    s = sm.start()
    # Should start at s11 or higher
    assert int(s.session_id[1:]) > 10
    # Stale file should have been cleaned up
    assert not (tmp_path / "s10.json").exists()


def test_end_nonexistent(session_manager):
    """Ending a nonexistent session should return None, not crash."""
    result = session_manager.end("s999")
    assert result is None

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Session Layer — multi-session management with local persistence."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

STATE_DIR = Path.home() / ".fsq-mac" / "sessions"


@dataclass
class SessionState:
    session_id: str
    backend_type: str = "appium_mac2"
    backend_connection: str = "http://127.0.0.1:4723"
    frontmost_app: str | None = None
    frontmost_window: str | None = None
    last_element_refs: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    last_error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class SessionManager:
    """Manages multiple automation sessions with local file persistence."""

    def __init__(self, config: dict, adapter_factory: Callable[[dict], Any] | None = None):
        self._config = config
        self._adapter_factory = adapter_factory
        self._sessions: dict[str, SessionState] = {}
        self._adapters: dict[str, Any] = {}
        self._active_session_id: str | None = None
        self._next_id: int = 0
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._cleanup_stale()

    def _cleanup_stale(self) -> None:
        """Remove stale session files and compute _next_id high-water mark.

        Appium sessions don't survive a daemon restart, so persisted files
        are always stale.  We only parse them to keep session IDs monotonic.
        """
        for f in STATE_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                sid = data.get("session_id", f.stem)
                # Extract numeric suffix to maintain high-water mark
                if sid.startswith("s") and sid[1:].isdigit():
                    self._next_id = max(self._next_id, int(sid[1:]))
            except Exception:
                pass
            # Delete the stale file regardless
            try:
                f.unlink()
            except Exception:
                pass

    def _persist(self, sid: str) -> None:
        state = self._sessions.get(sid)
        if state:
            (STATE_DIR / f"{sid}.json").write_text(
                json.dumps(state.to_dict(), indent=2, ensure_ascii=False)
            )

    def _now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # -- public API ---------------------------------------------------------

    def start(self) -> SessionState:
        self._next_id += 1
        sid = f"s{self._next_id}"
        state = SessionState(
            session_id=sid,
            backend_connection=self._config.get("server_url", "http://127.0.0.1:4723"),
            created_at=self._now(),
            updated_at=self._now(),
        )
        if self._adapter_factory:
            adapter = self._adapter_factory(self._config)
        else:
            from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
            adapter = AppiumMac2Adapter(self._config)
        self._sessions[sid] = state
        self._adapters[sid] = adapter
        self._active_session_id = sid
        self._persist(sid)
        return state

    def get(self, sid: str | None = None) -> SessionState | None:
        sid = sid or self._active_session_id
        return self._sessions.get(sid) if sid else None

    def list_sessions(self) -> list[dict]:
        return [s.to_dict() for s in self._sessions.values()]

    def end(self, sid: str | None = None) -> str | None:
        sid = sid or self._active_session_id
        if not sid or sid not in self._sessions:
            return None
        adapter = self._adapters.pop(sid, None)
        if adapter and adapter.connected:
            adapter.disconnect()
        self._sessions.pop(sid, None)
        state_file = STATE_DIR / f"{sid}.json"
        if state_file.exists():
            state_file.unlink()
        if self._active_session_id == sid:
            self._active_session_id = next(iter(self._sessions), None)
        return sid

    def adapter(self, sid: str | None = None) -> Any:
        sid = sid or self._active_session_id
        return self._adapters.get(sid) if sid else None

    def active_id(self) -> str | None:
        return self._active_session_id

    def update_state(self, sid: str, **kwargs) -> None:
        state = self._sessions.get(sid)
        if state:
            for k, v in kwargs.items():
                if hasattr(state, k):
                    setattr(state, k, v)
            state.updated_at = self._now()
            self._persist(sid)

    def end_all(self) -> None:
        for sid in list(self._sessions.keys()):
            self.end(sid)

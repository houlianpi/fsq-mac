# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""HTTP client — talks to the daemon process."""

from __future__ import annotations

import json
import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

STATE_DIR = Path.home() / ".fsq-mac"
PID_FILE = STATE_DIR / "daemon.pid"
PORT_FILE = STATE_DIR / "daemon.port"

DEFAULT_PORT = 19444
LOCK_FILE = STATE_DIR / "daemon.lock"


class DaemonClient:
    """Lightweight HTTP client that auto-starts the daemon if needed."""

    def __init__(self, timeout: float = 30.0, verbosity: str | None = None):
        self._timeout = timeout
        self._base_url: str | None = None
        self._client: httpx.Client | None = None
        self._verbosity = verbosity

    # -- daemon lifecycle ---------------------------------------------------

    def _read_port(self) -> int | None:
        try:
            return int(PORT_FILE.read_text().strip())
        except Exception:
            return None

    def _read_pid(self) -> int | None:
        try:
            return int(PID_FILE.read_text().strip())
        except Exception:
            return None

    def _is_alive(self) -> bool:
        pid = self._read_pid()
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        port = self._read_port() or DEFAULT_PORT
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def _start_daemon(self) -> int:
        """Fork a daemon process and wait for it to be ready (race-safe)."""
        port = DEFAULT_PORT
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        lock_fd = open(LOCK_FILE, "w")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            # Re-check after acquiring lock — another process may have started the daemon
            if self._is_alive():
                return self._read_port() or DEFAULT_PORT
            daemon_script = Path(__file__).parent / "daemon.py"
            cmd = [sys.executable, str(daemon_script), str(port)]
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            # Wait for daemon to become reachable
            for _ in range(30):
                time.sleep(0.5)
                try:
                    r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2)
                    if r.status_code == 200:
                        return port
                except Exception:
                    pass
            raise RuntimeError("Failed to start daemon within 15 seconds.")
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()

    def _ensure_daemon(self) -> str:
        """Return base URL, starting daemon if needed."""
        if self._base_url:
            return self._base_url
        if self._is_alive():
            port = self._read_port() or DEFAULT_PORT
        else:
            port = self._start_daemon()
        self._base_url = f"http://127.0.0.1:{port}"
        return self._base_url

    # -- API call -----------------------------------------------------------

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            headers = {}
            if self._verbosity:
                headers["X-Verbosity"] = self._verbosity
            self._client = httpx.Client(timeout=self._timeout, headers=headers)
        return self._client

    def call(self, domain: str, action: str, **params) -> dict:
        """Send a command to the daemon and return the parsed JSON response."""
        base = self._ensure_daemon()
        url = f"{base}/api/{domain}/{action}"
        try:
            r = self._get_client().post(url, json=params, timeout=self._timeout)
            if r.status_code >= 500:
                return {
                    "ok": False,
                    "command": f"{domain}.{action}",
                    "error": {
                        "code": "BACKEND_UNAVAILABLE",
                        "message": f"Daemon returned HTTP {r.status_code}",
                        "retryable": True,
                    },
                }
            return r.json()
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout):
            # Daemon may have died — try restart once
            self._base_url = None
            self._client = None
            try:
                base = self._ensure_daemon()
                url = f"{base}/api/{domain}/{action}"
                r = self._get_client().post(url, json=params, timeout=self._timeout)
                if r.status_code >= 500:
                    return {
                        "ok": False,
                        "command": f"{domain}.{action}",
                        "error": {
                            "code": "BACKEND_UNAVAILABLE",
                            "message": f"Daemon returned HTTP {r.status_code}",
                            "retryable": True,
                        },
                    }
                return r.json()
            except Exception as exc:
                return {
                    "ok": False,
                    "command": f"{domain}.{action}",
                    "error": {
                        "code": "BACKEND_UNAVAILABLE",
                        "message": f"Cannot reach daemon: {exc}",
                        "retryable": True,
                    },
                }
        except Exception as exc:
            return {
                "ok": False,
                "command": f"{domain}.{action}",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                    "retryable": False,
                },
            }

    # -- convenience --------------------------------------------------------

    def stop_daemon(self) -> None:
        """Send SIGTERM to the daemon."""
        pid = self._read_pid()
        if pid:
            try:
                os.kill(pid, 15)  # SIGTERM
            except OSError:
                pass
        self._base_url = None

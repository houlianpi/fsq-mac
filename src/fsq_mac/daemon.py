# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Daemon — long-running HTTP server that holds Appium sessions."""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from fsq_mac.core import AutomationCore, check_safety
from fsq_mac.models import ErrorCode, error_response
from fsq_mac.session import SessionManager

logger = logging.getLogger("mac-cli.daemon")

STATE_DIR = Path.home() / ".fsq-mac"
PID_FILE = STATE_DIR / "daemon.pid"
PORT_FILE = STATE_DIR / "daemon.port"

IDLE_TIMEOUT_SECONDS = 30 * 60  # 30 minutes

_last_activity: float = time.time()


def _touch_activity() -> None:
    global _last_activity
    _last_activity = time.time()


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    config_file = STATE_DIR / "config.json"
    template = Path(__file__).parent / "conf" / "config.template.json"
    if config_file.exists():
        raw = json.loads(config_file.read_text())
    elif template.exists():
        raw = json.loads(template.read_text())
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(raw, indent=2))
    else:
        return {"server_url": "http://127.0.0.1:4723", "platformName": "mac", "automationName": "Mac2"}
    # Support nested {"mac": {...}} or flat {...}
    if "mac" in raw and isinstance(raw["mac"], dict):
        return raw["mac"]
    return raw


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def _build_core() -> AutomationCore:
    config = _load_config()
    backend = config.get("backend", "appium_mac2")
    sm = SessionManager(config, backend=backend)
    return AutomationCore(sm)


# Global core instance — created once at startup
_core: AutomationCore | None = None


def _get_core() -> AutomationCore:
    global _core
    if _core is None:
        _core = _build_core()
    return _core


# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------

async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


def _opts(body: dict) -> dict:
    return {
        "sid": body.get("session") or body.get("session_id"),
    }


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "pid": os.getpid()})


async def api_handler(request: Request) -> JSONResponse:
    _touch_activity()
    domain = request.path_params["domain"]
    action = request.path_params["action"]
    command = f"{domain}.{action}"
    body = await _body(request)
    allow_dangerous = body.get("allow_dangerous", False)

    # Per-request verbosity from client
    verbosity = request.headers.get("x-verbosity", "")
    if verbosity == "debug":
        logging.getLogger("mac-cli.daemon").setLevel(logging.DEBUG)
        logging.getLogger("mac-cli.adapter").setLevel(logging.DEBUG)
    elif verbosity == "verbose":
        logging.getLogger("mac-cli.daemon").setLevel(logging.INFO)
        logging.getLogger("mac-cli.adapter").setLevel(logging.INFO)

    logger.debug("→ %s %s", command, body)

    # Safety check
    blocked = check_safety(command, allow_dangerous)
    if blocked:
        return JSONResponse(blocked.to_dict())

    core = _get_core()
    opts = _opts(body)
    sid = opts["sid"]

    try:
        resp = _dispatch(core, domain, action, body, sid)
    except Exception as exc:
        resp = error_response(command, ErrorCode.INTERNAL_ERROR, str(exc))

    return JSONResponse(resp.to_dict())


def _dispatch(core: AutomationCore, domain: str, action: str, body: dict, sid: str | None):
    """Route domain.action to the correct core method."""

    # -- session --
    if domain == "session":
        if action == "start":
            return core.session_start()
        if action == "get":
            return core.session_get(sid)
        if action == "list":
            return core.session_list()
        if action == "end":
            return core.session_end(sid)

    # -- app --
    if domain == "app":
        bundle_id = body.get("bundle_id", "")
        if action == "launch":
            return core.app_launch(bundle_id, sid)
        if action == "activate":
            return core.app_activate(bundle_id, sid)
        if action == "current":
            return core.app_current(sid)
        if action == "terminate":
            return core.app_terminate(bundle_id, sid)
        if action == "list":
            return core.app_list(sid)

    # -- element --
    if domain == "element":
        ref = body.get("ref", "")
        strategy = body.get("strategy", "accessibility_id")
        if action == "inspect":
            return core.element_inspect(sid)
        if action == "find":
            locator = body.get("locator", "")
            first_match = body.get("first_match", False)
            return core.element_find(locator, strategy, first_match, sid)
        if action == "click":
            return core.element_click(ref, strategy, sid)
        if action == "right-click":
            return core.element_right_click(ref, strategy, sid)
        if action == "double-click":
            return core.element_double_click(ref, strategy, sid)
        if action == "type":
            text = body.get("text", "")
            return core.element_type(ref, text, strategy, sid)
        if action == "scroll":
            direction = body.get("direction", "down")
            return core.element_scroll(ref, direction, strategy, sid)
        if action == "hover":
            return core.element_hover(ref, strategy, sid)
        if action == "drag":
            target = body.get("target", "")
            return core.element_drag(ref, target, strategy, sid)

    # -- input --
    if domain == "input":
        if action == "key":
            return core.input_key(body.get("key", ""), sid)
        if action == "hotkey":
            return core.input_hotkey(body.get("combo", ""), sid)
        if action == "text":
            return core.input_text(body.get("text", ""), sid)

    # -- capture --
    if domain == "capture":
        if action == "screenshot":
            return core.capture_screenshot(
                body.get("path", "./screenshot.png"), sid,
                ref=body.get("ref"), rect=body.get("rect"),
            )
        if action == "ui-tree":
            return core.capture_ui_tree(sid)

    # -- window --
    if domain == "window":
        if action == "current":
            return core.window_current(sid)
        if action == "list":
            return core.window_list(sid)
        if action == "focus":
            index = body.get("index", 0)
            return core.window_focus(index, sid)

    # -- wait --
    if domain == "wait":
        strategy = body.get("strategy", "accessibility_id")
        timeout = body.get("timeout", 10000)
        if action == "element":
            return core.wait_element(body.get("locator", ""), strategy, timeout, sid)
        if action == "window":
            title = body.get("title", "")
            return core.wait_window(title, timeout, sid)
        if action == "app":
            bundle_id = body.get("bundle_id", "")
            return core.wait_app(bundle_id, timeout, sid)

    # -- doctor --
    if domain == "doctor":
        from fsq_mac.doctor import run_checks
        if action == "all":
            return run_checks(core, "all")
        if action == "permissions":
            return run_checks(core, "permissions")
        if action == "backend":
            return run_checks(core, "backend")

    return error_response(f"{domain}.{action}", ErrorCode.INVALID_ARGUMENT,
                          f"Unknown command: {domain} {action}")


# ---------------------------------------------------------------------------
# Idle timeout
# ---------------------------------------------------------------------------

def _idle_watchdog() -> None:
    """Background thread: exit if no activity for IDLE_TIMEOUT_SECONDS."""
    import threading

    def _watch():
        while True:
            time.sleep(60)
            elapsed = time.time() - _last_activity
            if elapsed > IDLE_TIMEOUT_SECONDS:
                logger.info("Idle timeout reached (%d min). Shutting down.", IDLE_TIMEOUT_SECONDS // 60)
                _cleanup()
                os._exit(0)

    t = threading.Thread(target=_watch, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# PID / port management
# ---------------------------------------------------------------------------

def _write_pid(port: int) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    PORT_FILE.write_text(str(port))


def _cleanup() -> None:
    if _core:
        try:
            _core._sm.end_all()
        except Exception:
            pass
    for f in (PID_FILE, PORT_FILE):
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass


def _signal_handler(sig, frame) -> None:
    logger.info("Received signal %s, shutting down.", sig)
    _cleanup()
    sys.exit(0)


# ---------------------------------------------------------------------------
# ASGI app definition
# ---------------------------------------------------------------------------

routes = [
    Route("/health", health, methods=["GET"]),
    Route("/api/{domain}/{action}", api_handler, methods=["POST"]),
]

app = Starlette(routes=routes)


# ---------------------------------------------------------------------------
# Entry point: python -m fsq_mac.daemon [port]
# ---------------------------------------------------------------------------

def main(port: int = 19444) -> None:
    import uvicorn

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    _write_pid(port)
    _idle_watchdog()

    logger.info("Daemon starting on port %d (PID %d)", port, os.getpid())
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    finally:
        _cleanup()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 19444
    main(port)

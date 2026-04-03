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
from fsq_mac.models import ErrorCode, TraceArtifacts, error_response
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
    core = AutomationCore(sm)
    core.set_trace_replay_executor(lambda command, args: _execute_trace_step(core, command, args))
    return core


# Global core instance — created once at startup
_core: AutomationCore | None = None
_core_error: str | None = None


def _get_core() -> AutomationCore | None:
    global _core, _core_error
    if _core is None and _core_error is None:
        try:
            _core = _build_core()
        except ValueError as exc:
            _core_error = str(exc)
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


def _locator_kwargs(body: dict) -> dict:
    return {
        key: body.get(key)
        for key in ("id", "role", "name", "label", "xpath")
        if body.get(key) is not None
    }


def _is_recordable_command(command: str) -> bool:
    if command.startswith("trace."):
        return False
    if command.startswith("session."):
        return False
    return True


def _execute_trace_step(core: AutomationCore, command: str, args: dict) -> dict:
    if "." not in command:
        return error_response(command, ErrorCode.INVALID_ARGUMENT, f"Invalid trace command: {command}").to_dict()
    domain, action = command.split(".", 1)
    response = _dispatch(core, domain, action, args, args.get("session") or args.get("session_id"))
    return response.to_dict()


def _capture_trace_artifacts(core: AutomationCore, step_index: int) -> TraceArtifacts:
    artifacts = TraceArtifacts()
    trace_path = core.active_trace_path()
    if not trace_path or not hasattr(core, "trace_capture_adapter") or not hasattr(core, "trace_artifact_paths"):
        return artifacts
    try:
        adapter, _, err = core.trace_capture_adapter()
    except Exception:
        return artifacts
    if err or adapter is None:
        return artifacts

    paths = core.trace_artifact_paths(step_index)
    if not paths:
        return artifacts

    try:
        result = adapter.screenshot(paths["before_screenshot"])
        if not result.get("error_code"):
            artifacts.before_screenshot = result.get("path") or paths["before_screenshot"]
    except Exception:
        logger.exception("Failed to capture trace screenshot")

    try:
        tree = adapter.ui_tree()
        Path(paths["before_tree"]).write_text(tree)
        artifacts.before_tree = paths["before_tree"]
    except Exception:
        logger.exception("Failed to capture trace ui tree")

    return artifacts


def _capture_trace_artifacts_after(core: AutomationCore, step_index: int, artifacts: TraceArtifacts) -> TraceArtifacts:
    trace_path = core.active_trace_path()
    if not trace_path or not hasattr(core, "trace_capture_adapter") or not hasattr(core, "trace_artifact_paths"):
        return artifacts
    try:
        adapter, _, err = core.trace_capture_adapter()
    except Exception:
        return artifacts
    if err or adapter is None:
        return artifacts

    paths = core.trace_artifact_paths(step_index)
    if not paths:
        return artifacts

    try:
        result = adapter.screenshot(paths["after_screenshot"])
        if not result.get("error_code"):
            artifacts.after_screenshot = result.get("path") or paths["after_screenshot"]
    except Exception:
        logger.exception("Failed to capture trace screenshot")

    try:
        tree = adapter.ui_tree()
        Path(paths["after_tree"]).write_text(tree)
        artifacts.after_tree = paths["after_tree"]
    except Exception:
        logger.exception("Failed to capture trace ui tree")

    return artifacts


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
    if core is None:
        resp = error_response(command, ErrorCode.INVALID_ARGUMENT,
                              _core_error or "Backend initialization failed")
        return JSONResponse(resp.to_dict())
    opts = _opts(body)
    sid = opts["sid"]

    artifacts = TraceArtifacts()
    step_index = None
    if _is_recordable_command(command) and core.active_trace_id():
        if hasattr(core, "next_trace_step_index"):
            step_index = core.next_trace_step_index()
        if step_index is not None:
            artifacts = _capture_trace_artifacts(core, step_index)

    try:
        resp = _dispatch(core, domain, action, body, sid)
    except Exception as exc:
        resp = error_response(command, ErrorCode.INTERNAL_ERROR, str(exc))

    try:
        if _is_recordable_command(command) and core.active_trace_id():
            if step_index is None and hasattr(core, "next_trace_step_index"):
                step_index = core.next_trace_step_index()
            if step_index is not None:
                artifacts = _capture_trace_artifacts_after(core, step_index, artifacts)
            core.record_trace_step(command, body, resp.to_dict(), artifacts=artifacts)
    except Exception:
        logger.exception("Failed to record trace step for %s", command)

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
        locator = _locator_kwargs(body)
        if action == "inspect":
            return core.element_inspect(sid)
        if action == "find":
            locator = body.get("locator", "")
            first_match = body.get("first_match", False)
            return core.element_find(locator, strategy, first_match, sid)
        if action == "click":
            return core.element_click(ref or None, strategy, sid, **locator)
        if action == "right-click":
            return core.element_right_click(ref or None, strategy, sid, **locator)
        if action == "double-click":
            return core.element_double_click(ref or None, strategy, sid, **locator)
        if action == "type":
            text = body.get("text", "")
            return core.element_type(ref or None, text, strategy, sid, **locator)
        if action == "scroll":
            direction = body.get("direction", "down")
            return core.element_scroll(ref or None, direction, strategy, sid, **locator)
        if action == "hover":
            return core.element_hover(ref or None, strategy, sid, **locator)
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
        if action == "click-at":
            return core.input_click_at(body.get("x", 0), body.get("y", 0), sid)

    # -- assert --
    if domain == "assert":
        locator = _locator_kwargs(body)
        if action == "visible":
            return core.assert_visible(body.get("ref"), sid=sid, **locator)
        if action == "enabled":
            return core.assert_enabled(body.get("ref"), sid=sid, **locator)
        if action == "text":
            return core.assert_text(body.get("expected", ""), body.get("ref"), sid=sid, **locator)
        if action == "value":
            return core.assert_value(body.get("expected", ""), body.get("ref"), sid=sid, **locator)

    # -- menu --
    if domain == "menu":
        if action == "click":
            return core.menu_click(body.get("path", ""), sid)

    # -- trace --
    if domain == "trace":
        if action == "start":
            return core.trace_start(body.get("path"), sid)
        if action == "stop":
            return core.trace_stop(sid)
        if action == "status":
            return core.trace_status(sid)
        if action == "replay":
            return core.trace_replay(body.get("path", ""), sid)
        if action == "viewer":
            return core.trace_viewer(body.get("path", ""), sid)

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

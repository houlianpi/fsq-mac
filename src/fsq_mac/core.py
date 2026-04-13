# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Automation Core — product-level semantics, delegates to backend adapter."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from fsq_mac.models import (
    ErrorCode, Response, ResponseMeta, SafetyLevel,
    LocatorQuery, TraceArtifacts, TraceStep, success_response, error_response,
)
from fsq_mac.session import SessionManager
from fsq_mac.trace import TraceStore

# ---------------------------------------------------------------------------
# Safety classification
# ---------------------------------------------------------------------------

_SAFETY: dict[str, SafetyLevel] = {
    "session.start": SafetyLevel.SAFE,
    "session.get": SafetyLevel.SAFE,
    "session.list": SafetyLevel.SAFE,
    "session.end": SafetyLevel.SAFE,
    "app.launch": SafetyLevel.GUARDED,
    "app.activate": SafetyLevel.GUARDED,
    "app.list": SafetyLevel.SAFE,
    "app.current": SafetyLevel.SAFE,
    "app.terminate": SafetyLevel.DANGEROUS,
    "window.list": SafetyLevel.SAFE,
    "window.focus": SafetyLevel.GUARDED,
    "window.current": SafetyLevel.SAFE,
    "element.inspect": SafetyLevel.SAFE,
    "element.find": SafetyLevel.SAFE,
    "element.click": SafetyLevel.GUARDED,
    "element.right-click": SafetyLevel.GUARDED,
    "element.double-click": SafetyLevel.GUARDED,
    "element.type": SafetyLevel.GUARDED,
    "element.scroll": SafetyLevel.GUARDED,
    "element.hover": SafetyLevel.GUARDED,
    "element.drag": SafetyLevel.GUARDED,
    "input.key": SafetyLevel.GUARDED,
    "input.hotkey": SafetyLevel.GUARDED,
    "input.text": SafetyLevel.GUARDED,
    "input.click-at": SafetyLevel.GUARDED,
    "assert.visible": SafetyLevel.SAFE,
    "assert.enabled": SafetyLevel.SAFE,
    "assert.text": SafetyLevel.SAFE,
    "assert.value": SafetyLevel.SAFE,
    "menu.click": SafetyLevel.GUARDED,
    "trace.start": SafetyLevel.SAFE,
    "trace.stop": SafetyLevel.SAFE,
    "trace.status": SafetyLevel.SAFE,
    "trace.replay": SafetyLevel.GUARDED,
    "trace.viewer": SafetyLevel.SAFE,
    "trace.codegen": SafetyLevel.SAFE,
    "capture.screenshot": SafetyLevel.SAFE,
    "capture.ui-tree": SafetyLevel.SAFE,
    "wait.element": SafetyLevel.SAFE,
    "wait.window": SafetyLevel.SAFE,
    "wait.app": SafetyLevel.SAFE,
    "doctor": SafetyLevel.SAFE,
    "doctor.permissions": SafetyLevel.SAFE,
    "doctor.backend": SafetyLevel.SAFE,
    "doctor.plugins": SafetyLevel.SAFE,
}


def check_safety(command: str, allow_dangerous: bool) -> Response | None:
    level = _SAFETY.get(command, SafetyLevel.GUARDED)
    if level == SafetyLevel.DANGEROUS and not allow_dangerous:
        return error_response(
            command=command,
            code=ErrorCode.ACTION_BLOCKED,
            message=f"'{command}' is a dangerous operation. Use --allow-dangerous to proceed.",
            suggested_next_action=f"mac {command.replace('.', ' ')} --allow-dangerous",
        )
    return None


# ---------------------------------------------------------------------------
# Core executor
# ---------------------------------------------------------------------------

class AutomationCore:
    """Product-level orchestrator — thin layer between CLI and adapter."""

    def __init__(self, session_mgr: SessionManager):
        self._sm = session_mgr
        self._trace_root = Path.cwd() / "artifacts" / "traces"
        self._trace_store = TraceStore(self._trace_root)
        self._active_trace_id: str | None = None
        self._active_trace_path: str | None = None
        self._trace_replay_executor: Callable[[str, dict], dict] | None = None

    def _meta(self, start: float, sid: str | None = None) -> ResponseMeta:
        state = self._sm.get(sid)
        return ResponseMeta(
            duration_ms=int((time.time() - start) * 1000),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            frontmost_app=state.frontmost_app if state else None,
            frontmost_window=state.frontmost_window if state else None,
        )

    def _require_adapter(self, command: str, sid: str | None = None):
        adapter = self._sm.adapter(sid)
        active = sid or self._sm.active_id()
        if adapter is None or active is None:
            return None, active, error_response(
                command=command,
                code=ErrorCode.SESSION_NOT_FOUND,
                message="No active session. Run 'mac session start' first.",
                suggested_next_action="mac session start",
            )
        return adapter, active, None

    def _query_from_args(
        self,
        ref: str | None = None,
        id: str | None = None,
        role: str | None = None,
        name: str | None = None,
        label: str | None = None,
        xpath: str | None = None,
    ) -> LocatorQuery:
        return LocatorQuery(ref=ref, id=id, role=role, name=name, label=label, xpath=xpath)

    def set_trace_replay_executor(self, executor: Callable[[str, dict], dict]) -> None:
        self._trace_replay_executor = executor

    def active_trace_id(self) -> str | None:
        return self._active_trace_id

    def active_trace_path(self) -> str | None:
        return self._active_trace_path

    def next_trace_step_index(self) -> int | None:
        if not self._active_trace_path:
            return None
        run = self._trace_store.load_trace(self._active_trace_path)
        return len(run.steps) + 1

    def trace_artifact_paths(self, step_index: int) -> dict[str, str]:
        if not self._active_trace_path:
            return {}
        return self._trace_store.step_artifact_paths_for_dir(self._active_trace_path, step_index)

    def trace_capture_adapter(self, sid: str | None = None):
        return self._require_adapter("trace.capture", sid)

    def _derive_locator_query(self, args: dict) -> tuple[dict, bool]:
        locator = {key: args.get(key) for key in ("id", "role", "name", "label", "xpath") if args.get(key)}
        ref = args.get("ref")
        if locator:
            return locator, True
        if isinstance(ref, str) and ref.startswith("e") and ref[1:].isdigit():
            return {}, False
        return ({"ref": ref} if ref else {}), True

    def record_trace_step(
        self,
        command: str,
        args: dict,
        result: dict,
        artifacts: TraceArtifacts | dict | None = None,
    ) -> bool:
        if not self._active_trace_path:
            return False
        run = self._trace_store.load_trace(self._active_trace_path)
        locator_query, replayable = self._derive_locator_query(args)
        step = TraceStep(
            index=len(run.steps) + 1,
            command=command,
            args=args,
            locator_query=locator_query,
            replayable=replayable,
            started_at=result.get("meta", {}).get("timestamp", ""),
            duration_ms=result.get("meta", {}).get("duration_ms", 0),
            ok=result.get("ok", False),
            error=result.get("error"),
            artifacts=artifacts or TraceArtifacts(),
        )
        self._trace_store.append_step_at_path(self._active_trace_path, step)
        return True

    # -- session ------------------------------------------------------------

    def session_start(self) -> Response:
        t = time.time()
        state = self._sm.start()
        return success_response("session.start", data=state.to_dict(),
                                session_id=state.session_id, meta=self._meta(t, state.session_id))

    def session_get(self, sid: str | None = None) -> Response:
        t = time.time()
        state = self._sm.get(sid)
        if not state:
            return error_response("session.get", ErrorCode.SESSION_NOT_FOUND,
                                  "No active session.", suggested_next_action="mac session start")
        return success_response("session.get", data=state.to_dict(),
                                session_id=state.session_id, meta=self._meta(t, state.session_id))

    def session_list(self) -> Response:
        t = time.time()
        return success_response("session.list", data={"sessions": self._sm.list_sessions()},
                                meta=self._meta(t))

    def session_end(self, sid: str | None = None) -> Response:
        t = time.time()
        ended = self._sm.end(sid)
        if not ended:
            return error_response("session.end", ErrorCode.SESSION_NOT_FOUND, "Session not found.")
        return success_response("session.end", data={"ended": ended}, meta=self._meta(t))

    # -- app ----------------------------------------------------------------

    def app_launch(self, bundle_id: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("app.launch", sid)
        if err:
            return err
        info = adapter.app_launch(bundle_id)
        if info.get("error_code"):
            return error_response("app.launch", info["error_code"], info.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active),
                                  doctor_hint="mac doctor backend")
        self._sm.update_state(active, frontmost_app=bundle_id)
        # Update frontmost_window metadata (#8)
        try:
            win_info = adapter.window_current()
            if win_info.get("title"):
                self._sm.update_state(active, frontmost_window=win_info["title"])
        except Exception:
            pass
        return success_response("app.launch", data=info, session_id=active, meta=self._meta(t, active))

    def app_activate(self, bundle_id: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("app.activate", sid)
        if err:
            return err
        info = adapter.app_activate(bundle_id)
        if info.get("error_code"):
            return error_response("app.activate", info["error_code"], info.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        self._sm.update_state(active, frontmost_app=bundle_id)
        # Update frontmost_window metadata (#8)
        try:
            win_info = adapter.window_current()
            if win_info.get("title"):
                self._sm.update_state(active, frontmost_window=win_info["title"])
        except Exception:
            pass
        return success_response("app.activate", data=info, session_id=active, meta=self._meta(t, active))

    def app_current(self, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("app.current", sid)
        if err:
            return err
        info = adapter.app_current()
        self._sm.update_state(active, frontmost_app=info.get("bundle_id"))
        return success_response("app.current", data=info, session_id=active, meta=self._meta(t, active))

    def app_terminate(self, bundle_id: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("app.terminate", sid)
        if err:
            return err
        info = adapter.app_terminate(bundle_id)
        if info.get("error_code"):
            return error_response("app.terminate", info["error_code"], info.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("app.terminate", data=info, session_id=active, meta=self._meta(t, active))

    def app_list(self, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("app.list", sid)
        if err:
            return err
        apps = adapter.app_list()
        return success_response("app.list", data={"apps": apps},
                                session_id=active, meta=self._meta(t, active))

    # -- element ------------------------------------------------------------

    def element_inspect(self, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("element.inspect", sid)
        if err:
            return err
        try:
            elements = adapter.inspect()
        except RuntimeError as exc:
            message = str(exc)
            if "Timed out retrieving page source" in message:
                return error_response("element.inspect", ErrorCode.TIMEOUT,
                                      message,
                                      session_id=active, meta=self._meta(t, active))
            return error_response("element.inspect", ErrorCode.BACKEND_UNAVAILABLE,
                                  message,
                                  suggested_next_action="mac app launch <bundle_id>",
                                  session_id=active, meta=self._meta(t, active))
        return success_response("element.inspect", data={
            "elements": elements,
            "note": "Element refs (e0, e1, ...) are scoped to this result. A new find or inspect invalidates previous refs.",
        },
                                session_id=active, meta=self._meta(t, active))

    def element_find(self, locator: str, strategy: str = "accessibility_id",
                     first_match: bool = False, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("element.find", sid)
        if err:
            return err
        status, elements = adapter.find(locator, strategy)
        if status == "no_match":
            return error_response("element.find", ErrorCode.ELEMENT_NOT_FOUND,
                                  f"Element '{locator}' not found",
                                  session_id=active, meta=self._meta(t, active),
                                  suggested_next_action="mac element inspect")
        if status == "multiple_matches" and not first_match:
            return error_response("element.find", ErrorCode.ELEMENT_AMBIGUOUS,
                                  f"Multiple matches for '{locator}'. Use --first-match or refine locator.",
                                  session_id=active, meta=self._meta(t, active),
                                  details={"candidates": elements})
        return success_response("element.find", data={
            "match_status": status, "elements": elements,
            "note": "Element refs (e0, e1, ...) are scoped to this result. A new find or inspect invalidates previous refs.",
        },
                                session_id=active, meta=self._meta(t, active))

    def _element_action(self, command: str, query: LocatorQuery, action_fn, strategy: str,
                        sid: str | None = None, **extra) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter(command, sid)
        if err:
            return err
        result = action_fn(query, strategy=strategy, **extra)
        err_code = result.get("error_code")
        if err_code:
            ref = query.ref or query.to_dict()
            msg = result.get("detail", f"Action failed on '{ref}'")
            suggested = "mac element inspect" if err_code == ErrorCode.ELEMENT_REFERENCE_STALE else None
            return error_response(command, err_code, msg, session_id=active,
                                  meta=self._meta(t, active), suggested_next_action=suggested)
        return success_response(command, data=result or {}, session_id=active, meta=self._meta(t, active))

    def element_click(self, ref: str | None = None, strategy: str = "accessibility_id", sid: str | None = None,
                      **locator) -> Response:
        adapter, _, err = self._require_adapter("element.click", sid)
        if err:
            return err
        query = self._query_from_args(ref=ref, **locator)
        return self._element_action("element.click", query, adapter.click, strategy, sid)

    def element_right_click(self, ref: str | None = None, strategy: str = "accessibility_id", sid: str | None = None,
                            **locator) -> Response:
        adapter, _, err = self._require_adapter("element.right-click", sid)
        if err:
            return err
        query = self._query_from_args(ref=ref, **locator)
        return self._element_action("element.right-click", query, adapter.right_click, strategy, sid)

    def element_double_click(self, ref: str | None = None, strategy: str = "accessibility_id", sid: str | None = None,
                             **locator) -> Response:
        adapter, _, err = self._require_adapter("element.double-click", sid)
        if err:
            return err
        query = self._query_from_args(ref=ref, **locator)
        return self._element_action("element.double-click", query, adapter.double_click, strategy, sid)

    def element_type(self, ref: str | None, text: str, strategy: str = "accessibility_id",
                     sid: str | None = None, **locator) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("element.type", sid)
        if err:
            return err
        query = self._query_from_args(ref=ref, **locator)
        result = adapter.type_text(query, text, strategy=strategy)
        err_code = result.get("error_code")
        if err_code:
            return error_response("element.type", err_code, result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        data = {}
        for key in ("verified", "typed_value", "expected", "element_bounds", "center"):
            if key in result:
                data[key] = result[key]
        # verified=False → typing succeeded but value doesn't match
        if result.get("verified") is False:
            msg = (f"Typed value {result.get('typed_value')!r} "
                   f"does not match expected {result.get('expected')!r}")
            return error_response("element.type", ErrorCode.TYPE_VERIFICATION_FAILED, msg,
                                  session_id=active, meta=self._meta(t, active),
                                  details=data)
        return success_response("element.type", data=data or None,
                                session_id=active, meta=self._meta(t, active))

    def element_scroll(self, ref: str | None, direction: str = "down", strategy: str = "accessibility_id",
                       sid: str | None = None, **locator) -> Response:
        adapter, _, err = self._require_adapter("element.scroll", sid)
        if err:
            return err
        query = self._query_from_args(ref=ref, **locator)
        return self._element_action("element.scroll", query, adapter.scroll, strategy, sid, direction=direction)

    def element_hover(self, ref: str | None = None, strategy: str = "accessibility_id", sid: str | None = None,
                      **locator) -> Response:
        adapter, _, err = self._require_adapter("element.hover", sid)
        if err:
            return err
        query = self._query_from_args(ref=ref, **locator)
        return self._element_action("element.hover", query, adapter.hover, strategy, sid)

    def element_drag(self, source: str, target: str, strategy: str = "accessibility_id", sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("element.drag", sid)
        if err:
            return err
        result = adapter.drag(self._query_from_args(ref=source), self._query_from_args(ref=target), strategy=strategy)
        err_code = result.get("error_code")
        if err_code:
            return error_response("element.drag", err_code, result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("element.drag", session_id=active, meta=self._meta(t, active))

    # -- input --------------------------------------------------------------

    def input_key(self, key: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("input.key", sid)
        if err:
            return err
        result = adapter.input_key(key)
        if result.get("error_code"):
            return error_response("input.key", result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("input.key", data=result or None, session_id=active, meta=self._meta(t, active))

    def input_hotkey(self, combo: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("input.hotkey", sid)
        if err:
            return err
        result = adapter.input_hotkey(combo)
        if result.get("error_code"):
            return error_response("input.hotkey", result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("input.hotkey", data=result or None, session_id=active, meta=self._meta(t, active))

    def input_text(self, text: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("input.text", sid)
        if err:
            return err
        result = adapter.input_text(text)
        if result.get("error_code"):
            return error_response("input.text", result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("input.text", data=result or None, session_id=active, meta=self._meta(t, active))

    def input_click_at(self, x: int, y: int, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("input.click-at", sid)
        if err:
            return err
        result = adapter.input_click_at(x, y)
        if result.get("error_code"):
            return error_response("input.click-at", result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("input.click-at", session_id=active, meta=self._meta(t, active))

    def _assert_element(self, command: str, method_name: str, expected: str | None = None,
                        sid: str | None = None, ref: str | None = None, **locator) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter(command, sid)
        if err:
            return err
        query = self._query_from_args(ref=ref, **locator)
        action_fn = getattr(adapter, method_name)
        result = action_fn(query) if expected is None else action_fn(query, expected)
        if result.get("error_code"):
            return error_response(command, result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response(command, data=result or {}, session_id=active, meta=self._meta(t, active))

    def assert_visible(self, ref: str | None = None, sid: str | None = None, **locator) -> Response:
        return self._assert_element("assert.visible", "assert_visible", sid=sid, ref=ref, **locator)

    def assert_enabled(self, ref: str | None = None, sid: str | None = None, **locator) -> Response:
        return self._assert_element("assert.enabled", "assert_enabled", sid=sid, ref=ref, **locator)

    def assert_text(self, expected: str, ref: str | None = None, sid: str | None = None, **locator) -> Response:
        return self._assert_element("assert.text", "assert_text", expected=expected, sid=sid, ref=ref, **locator)

    def assert_value(self, expected: str, ref: str | None = None, sid: str | None = None, **locator) -> Response:
        return self._assert_element("assert.value", "assert_value", expected=expected, sid=sid, ref=ref, **locator)

    def assert_app_running(self, bundle_id: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("assert.app-running", sid)
        if err:
            return err
        apps = adapter.app_list()
        for app in apps:
            if app.get("bundle_id") == bundle_id:
                return success_response("assert.app-running", data={"bundle_id": bundle_id, "running": True},
                                        session_id=active, meta=self._meta(t, active))
        return error_response("assert.app-running", ErrorCode.ASSERTION_FAILED,
                              f"App {bundle_id!r} is not running",
                              session_id=active, meta=self._meta(t, active),
                              details={"bundle_id": bundle_id, "running": False})

    def assert_app_frontmost(self, bundle_id: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("assert.app-frontmost", sid)
        if err:
            return err
        info = adapter.app_current()
        if info.get("bundle_id") == bundle_id:
            return success_response("assert.app-frontmost", data=info, session_id=active, meta=self._meta(t, active))
        actual = info.get("bundle_id")
        return error_response("assert.app-frontmost", ErrorCode.ASSERTION_FAILED,
                              f"App {bundle_id!r} is not frontmost",
                              session_id=active, meta=self._meta(t, active),
                              details={"expected_bundle_id": bundle_id, "actual_bundle_id": actual})

    def menu_click(self, path: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("menu.click", sid)
        if err:
            return err
        result = adapter.menu_click(path)
        if result.get("error_code"):
            return error_response("menu.click", result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("menu.click", data=result or {}, session_id=active, meta=self._meta(t, active))

    def trace_start(self, path: str | None = None, sid: str | None = None) -> Response:
        t = time.time()
        run = self._trace_store.start_trace(path)
        active = sid or self._sm.active_id()
        state = self._sm.get(active) if active else None
        if state and state.frontmost_app:
            run.frontmost_app = state.frontmost_app
            self._trace_store._resolve_manifest_path(run.output_dir).write_text(
                json.dumps(run.to_dict(), indent=2, ensure_ascii=False)
            )
        self._active_trace_id = run.trace_id
        self._active_trace_path = run.output_dir
        return success_response("trace.start", data={
            "path": run.output_dir,
            "trace_id": run.trace_id,
            "active": True,
        }, session_id=sid, meta=self._meta(t, sid))

    def trace_stop(self, sid: str | None = None) -> Response:
        t = time.time()
        if not self._active_trace_id:
            return success_response("trace.stop", data={"active": False},
                                    session_id=sid, meta=self._meta(t, sid))
        run = self._trace_store.stop_trace_at_path(self._active_trace_path or str(self._trace_root / self._active_trace_id))
        self._active_trace_id = None
        self._active_trace_path = None
        return success_response("trace.stop", data={
            "active": False,
            "trace_id": run.trace_id,
            "path": run.output_dir,
        }, session_id=sid, meta=self._meta(t, sid))

    def trace_status(self, sid: str | None = None) -> Response:
        t = time.time()
        data = {"active": False}
        if self._active_trace_id:
            run = self._trace_store.load_trace(self._active_trace_path or str(self._trace_root / self._active_trace_id))
            data = {
                "active": True,
                "trace_id": run.trace_id,
                "path": run.output_dir,
                "status": run.status,
                "steps": len(run.steps),
            }
        return success_response("trace.status", data=data,
                                session_id=sid, meta=self._meta(t, sid))

    def trace_replay(self, path: str, sid: str | None = None) -> Response:
        t = time.time()
        trace_path = Path(path)
        manifest_path = trace_path if trace_path.name == "trace.json" else trace_path / "trace.json"
        if not manifest_path.exists():
            return error_response("trace.replay", ErrorCode.INVALID_ARGUMENT,
                                  f"Trace manifest not found: {path}",
                                  session_id=sid, meta=self._meta(t, sid))
        if self._trace_replay_executor is None:
            return error_response("trace.replay", ErrorCode.INTERNAL_ERROR,
                                  "Trace replay executor is not configured",
                                  session_id=sid, meta=self._meta(t, sid))
        result = self._trace_store.replay(str(manifest_path), self._trace_replay_executor)
        if not result.get("ok", False):
            error = result.get("error", {})
            code_value = error.get("code", ErrorCode.INTERNAL_ERROR.value)
            code = ErrorCode(code_value)
            data = {
                "completed_steps": result.get("completed_steps", 0),
                "trace_id": result.get("trace_id"),
            }
            failing_step = result.get("failing_step")
            if failing_step:
                data["failing_step"] = failing_step
            return error_response("trace.replay", code, error.get("message", "Replay failed"),
                                  session_id=sid, meta=self._meta(t, sid), data=data)
        return success_response("trace.replay", data=result,
                                session_id=sid, meta=self._meta(t, sid))

    def trace_viewer(self, path: str, sid: str | None = None) -> Response:
        t = time.time()
        trace_path = Path(path)
        manifest_path = trace_path if trace_path.name == "trace.json" else trace_path / "trace.json"
        if not manifest_path.exists():
            return error_response("trace.viewer", ErrorCode.INVALID_ARGUMENT,
                                  f"Trace manifest not found: {path}",
                                  session_id=sid, meta=self._meta(t, sid))
        viewer_path = self._trace_store.generate_viewer(str(manifest_path))
        return success_response("trace.viewer", data={"path": viewer_path},
                                session_id=sid, meta=self._meta(t, sid))

    def trace_codegen(self, path: str, sid: str | None = None) -> Response:
        t = time.time()
        if not path:
            return error_response("trace.codegen", ErrorCode.INVALID_ARGUMENT,
                                  "path is required",
                                  session_id=sid, meta=self._meta(t, sid))
        try:
            run = self._trace_store.load_trace(path)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            return error_response("trace.codegen", ErrorCode.INVALID_ARGUMENT,
                                  str(exc), session_id=sid, meta=self._meta(t, sid))
        from fsq_mac.codegen import generate_shell_script
        script = generate_shell_script(run)
        return success_response("trace.codegen", data={
            "script": script,
            "trace_id": run.trace_id,
            "step_count": len(run.steps),
        }, session_id=sid, meta=self._meta(t, sid))

    # -- capture ------------------------------------------------------------

    def capture_screenshot(self, path: str, sid: str | None = None,
                           ref: str | None = None, rect: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("capture.screenshot", sid)
        if err:
            return err
        if ref:
            result = adapter.screenshot_element(ref, path)
        elif rect:
            result = adapter.screenshot_rect(rect, path)
        else:
            result = adapter.screenshot(path)
        if result.get("error_code"):
            return error_response("capture.screenshot", result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("capture.screenshot", data=result, session_id=active, meta=self._meta(t, active))

    def capture_ui_tree(self, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("capture.ui-tree", sid)
        if err:
            return err
        try:
            tree = adapter.ui_tree()
        except RuntimeError as exc:
            message = str(exc)
            if "Timed out retrieving page source" in message:
                return error_response("capture.ui-tree", ErrorCode.TIMEOUT,
                                      message,
                                      session_id=active, meta=self._meta(t, active))
            return error_response("capture.ui-tree", ErrorCode.BACKEND_UNAVAILABLE,
                                  message,
                                  suggested_next_action="mac app launch <bundle_id>",
                                  session_id=active, meta=self._meta(t, active))
        return success_response("capture.ui-tree", data={"ui_tree": tree},
                                session_id=active, meta=self._meta(t, active))

    # -- window -------------------------------------------------------------

    def window_current(self, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("window.current", sid)
        if err:
            return err
        info = adapter.window_current()
        # Update frontmost metadata
        if info.get("title"):
            self._sm.update_state(active, frontmost_window=info["title"])
        if info.get("app_bundle_id"):
            self._sm.update_state(active, frontmost_app=info["app_bundle_id"])
        return success_response("window.current", data=info, session_id=active, meta=self._meta(t, active))

    def window_list(self, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("window.list", sid)
        if err:
            return err
        windows = adapter.window_list()
        return success_response("window.list", data={"windows": windows},
                                session_id=active, meta=self._meta(t, active))

    def window_focus(self, index: int, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("window.focus", sid)
        if err:
            return err
        result = adapter.window_focus(index)
        err_code = result.get("error_code")
        if err_code:
            return error_response("window.focus", err_code, result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        if result.get("title"):
            self._sm.update_state(active, frontmost_window=result["title"])
        return success_response("window.focus", data=result, session_id=active, meta=self._meta(t, active))

    # -- wait ---------------------------------------------------------------

    def wait_element(self, locator: str, strategy: str = "accessibility_id",
                     timeout: int = 10000, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("wait.element", sid)
        if err:
            return err
        timeout_sec = max(timeout / 1000, 1)
        found = adapter.wait_element(locator, strategy, timeout_sec)
        if not found:
            return error_response("wait.element", ErrorCode.TIMEOUT,
                                  f"Element '{locator}' not found within {timeout}ms",
                                  session_id=active, meta=self._meta(t, active),
                                  suggested_next_action="mac element inspect")
        return success_response("wait.element", data={"found": True},
                                session_id=active, meta=self._meta(t, active))

    def wait_window(self, title: str, timeout: int = 10000, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("wait.window", sid)
        if err:
            return err
        timeout_sec = max(timeout / 1000, 1)
        found = adapter.wait_window(title, timeout_sec)
        if not found:
            return error_response("wait.window", ErrorCode.TIMEOUT,
                                  f"Window '{title}' not found within {timeout}ms",
                                  session_id=active, meta=self._meta(t, active))
        return success_response("wait.window", data={"found": True, "title": title},
                                session_id=active, meta=self._meta(t, active))

    def wait_app(self, bundle_id: str, timeout: int = 10000, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("wait.app", sid)
        if err:
            return err
        timeout_sec = max(timeout / 1000, 1)
        found = adapter.wait_app(bundle_id, timeout_sec)
        if not found:
            return error_response("wait.app", ErrorCode.TIMEOUT,
                                  f"App '{bundle_id}' not found within {timeout}ms",
                                  session_id=active, meta=self._meta(t, active))
        return success_response("wait.app", data={"found": True, "bundle_id": bundle_id},
                                session_id=active, meta=self._meta(t, active))

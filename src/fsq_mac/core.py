# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Automation Core — product-level semantics, delegates to backend adapter."""

from __future__ import annotations

import time

from fsq_mac.models import (
    ErrorCode, Response, ResponseMeta, SafetyLevel,
    success_response, error_response,
)
from fsq_mac.session import SessionManager

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
    "capture.screenshot": SafetyLevel.SAFE,
    "capture.ui-tree": SafetyLevel.SAFE,
    "wait.element": SafetyLevel.SAFE,
    "wait.window": SafetyLevel.SAFE,
    "wait.app": SafetyLevel.SAFE,
    "doctor": SafetyLevel.SAFE,
    "doctor.permissions": SafetyLevel.SAFE,
    "doctor.backend": SafetyLevel.SAFE,
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
        try:
            info = adapter.app_launch(bundle_id)
            self._sm.update_state(active, frontmost_app=bundle_id)
            # Update frontmost_window metadata (#8)
            try:
                win_info = adapter.window_current()
                if win_info.get("title"):
                    self._sm.update_state(active, frontmost_window=win_info["title"])
            except Exception:
                pass
            return success_response("app.launch", data=info, session_id=active, meta=self._meta(t, active))
        except Exception as exc:
            return error_response("app.launch", ErrorCode.BACKEND_UNAVAILABLE, str(exc),
                                  session_id=active, meta=self._meta(t, active),
                                  doctor_hint="mac doctor backend")

    def app_activate(self, bundle_id: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("app.activate", sid)
        if err:
            return err
        try:
            info = adapter.app_activate(bundle_id)
            self._sm.update_state(active, frontmost_app=bundle_id)
            # Update frontmost_window metadata (#8)
            try:
                win_info = adapter.window_current()
                if win_info.get("title"):
                    self._sm.update_state(active, frontmost_window=win_info["title"])
            except Exception:
                pass
            return success_response("app.activate", data=info, session_id=active, meta=self._meta(t, active))
        except Exception as exc:
            return error_response("app.activate", ErrorCode.APP_NOT_FOUND, str(exc),
                                  session_id=active, meta=self._meta(t, active))

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
        try:
            info = adapter.app_terminate(bundle_id)
            return success_response("app.terminate", data=info, session_id=active, meta=self._meta(t, active))
        except Exception as exc:
            return error_response("app.terminate", ErrorCode.APP_NOT_FOUND, str(exc),
                                  session_id=active, meta=self._meta(t, active))

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
        elements = adapter.inspect()
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

    def _element_action(self, command: str, ref: str, action_fn, strategy: str,
                        sid: str | None = None, **extra) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter(command, sid)
        if err:
            return err
        result = action_fn(ref, strategy=strategy, **extra)
        err_code = result.get("error_code")
        if err_code:
            msg = result.get("detail", f"Action failed on '{ref}'")
            suggested = "mac element inspect" if err_code == ErrorCode.ELEMENT_REFERENCE_STALE else None
            return error_response(command, err_code, msg, session_id=active,
                                  meta=self._meta(t, active), suggested_next_action=suggested)
        return success_response(command, data=result or {}, session_id=active, meta=self._meta(t, active))

    def element_click(self, ref: str, strategy: str = "accessibility_id", sid: str | None = None) -> Response:
        adapter, _, err = self._require_adapter("element.click", sid)
        if err:
            return err
        return self._element_action("element.click", ref, adapter.click, strategy, sid)

    def element_right_click(self, ref: str, strategy: str = "accessibility_id", sid: str | None = None) -> Response:
        adapter, _, err = self._require_adapter("element.right-click", sid)
        if err:
            return err
        return self._element_action("element.right-click", ref, adapter.right_click, strategy, sid)

    def element_double_click(self, ref: str, strategy: str = "accessibility_id", sid: str | None = None) -> Response:
        adapter, _, err = self._require_adapter("element.double-click", sid)
        if err:
            return err
        return self._element_action("element.double-click", ref, adapter.double_click, strategy, sid)

    def element_type(self, ref: str, text: str, strategy: str = "accessibility_id", sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("element.type", sid)
        if err:
            return err
        result = adapter.type_text(ref, text, strategy=strategy)
        err_code = result.get("error_code")
        if err_code:
            return error_response("element.type", err_code, result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        data = {}
        for key in ("verified", "typed_value", "expected"):
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

    def element_scroll(self, ref: str, direction: str = "down", strategy: str = "accessibility_id", sid: str | None = None) -> Response:
        adapter, _, err = self._require_adapter("element.scroll", sid)
        if err:
            return err
        return self._element_action("element.scroll", ref, adapter.scroll, strategy, sid, direction=direction)

    def element_hover(self, ref: str, strategy: str = "accessibility_id", sid: str | None = None) -> Response:
        adapter, _, err = self._require_adapter("element.hover", sid)
        if err:
            return err
        return self._element_action("element.hover", ref, adapter.hover, strategy, sid)

    def element_drag(self, source: str, target: str, strategy: str = "accessibility_id", sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("element.drag", sid)
        if err:
            return err
        result = adapter.drag(source, target, strategy=strategy)
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
        return success_response("input.key", session_id=active, meta=self._meta(t, active))

    def input_hotkey(self, combo: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("input.hotkey", sid)
        if err:
            return err
        result = adapter.input_hotkey(combo)
        if result.get("error_code"):
            return error_response("input.hotkey", result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("input.hotkey", session_id=active, meta=self._meta(t, active))

    def input_text(self, text: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("input.text", sid)
        if err:
            return err
        result = adapter.input_text(text)
        if result.get("error_code"):
            return error_response("input.text", result["error_code"], result.get("detail", ""),
                                  session_id=active, meta=self._meta(t, active))
        return success_response("input.text", session_id=active, meta=self._meta(t, active))

    # -- capture ------------------------------------------------------------

    def capture_screenshot(self, path: str, sid: str | None = None) -> Response:
        t = time.time()
        adapter, active, err = self._require_adapter("capture.screenshot", sid)
        if err:
            return err
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
        tree = adapter.ui_tree()
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

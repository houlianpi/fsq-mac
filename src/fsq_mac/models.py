# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Data models: response envelope, error codes, element model, safety levels."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

class ErrorCode(str, Enum):
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_CONFLICT = "SESSION_CONFLICT"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    APP_NOT_FOUND = "APP_NOT_FOUND"
    WINDOW_NOT_FOUND = "WINDOW_NOT_FOUND"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ELEMENT_AMBIGUOUS = "ELEMENT_AMBIGUOUS"
    ELEMENT_REFERENCE_STALE = "ELEMENT_REFERENCE_STALE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ACTION_BLOCKED = "ACTION_BLOCKED"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    TYPE_VERIFICATION_FAILED = "TYPE_VERIFICATION_FAILED"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


_RETRYABLE = {
    ErrorCode.SESSION_CONFLICT,
    ErrorCode.BACKEND_UNAVAILABLE,
    ErrorCode.WINDOW_NOT_FOUND,
    ErrorCode.ELEMENT_NOT_FOUND,
    ErrorCode.ELEMENT_REFERENCE_STALE,
    ErrorCode.TIMEOUT,
}


# ---------------------------------------------------------------------------
# Safety levels
# ---------------------------------------------------------------------------

class SafetyLevel(str, Enum):
    SAFE = "safe"
    GUARDED = "guarded"
    DANGEROUS = "dangerous"


# ---------------------------------------------------------------------------
# Error object
# ---------------------------------------------------------------------------

@dataclass
class CLIError:
    code: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    suggested_next_action: str | None = None
    doctor_hint: str | None = None

    @property
    def retryable(self) -> bool:
        return self.code in _RETRYABLE

    def to_dict(self) -> dict:
        return {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
            "suggested_next_action": self.suggested_next_action,
            "doctor_hint": self.doctor_hint,
        }


# ---------------------------------------------------------------------------
# Response meta
# ---------------------------------------------------------------------------

@dataclass
class ResponseMeta:
    backend: str = "appium_mac2"
    duration_ms: int = 0
    timestamp: str = ""
    frontmost_app: str | None = None
    frontmost_window: str | None = None

    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "frontmost_app": self.frontmost_app,
            "frontmost_window": self.frontmost_window,
        }


# ---------------------------------------------------------------------------
# Unified response envelope
# ---------------------------------------------------------------------------

@dataclass
class Response:
    ok: bool
    command: str
    session_id: str | None = None
    data: Any = None
    error: CLIError | None = None
    meta: ResponseMeta = field(default_factory=ResponseMeta)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "command": self.command,
            "session_id": self.session_id,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
            "meta": self.meta.to_dict(),
        }

    def to_json(self, pretty: bool = False) -> str:
        d = self.to_dict()
        if pretty:
            return json.dumps(d, indent=2, ensure_ascii=False)
        return json.dumps(d, ensure_ascii=False)


def success_response(
    command: str,
    data: Any = None,
    session_id: str | None = None,
    meta: ResponseMeta | None = None,
) -> Response:
    return Response(
        ok=True,
        command=command,
        session_id=session_id,
        data=data,
        meta=meta or ResponseMeta(),
    )


def error_response(
    command: str,
    code: ErrorCode,
    message: str,
    session_id: str | None = None,
    meta: ResponseMeta | None = None,
    suggested_next_action: str | None = None,
    doctor_hint: str | None = None,
    details: dict | None = None,
) -> Response:
    return Response(
        ok=False,
        command=command,
        session_id=session_id,
        error=CLIError(
            code=code,
            message=message,
            details=details or {},
            suggested_next_action=suggested_next_action,
            doctor_hint=doctor_hint,
        ),
        meta=meta or ResponseMeta(),
    )


# ---------------------------------------------------------------------------
# Element model
# ---------------------------------------------------------------------------

@dataclass
class ElementInfo:
    element_id: str
    role: str
    name: str | None = None
    label: str | None = None
    value: str | None = None
    enabled: bool = True
    visible: bool = True
    focused: bool = False
    frame: dict[str, int] | None = None
    locator_hint: str | None = None
    doc_order_index: int = -1  # internal: position in document-order traversal

    def to_dict(self) -> dict:
        return {
            "element_id": self.element_id,
            "role": self.role,
            "name": self.name,
            "label": self.label,
            "value": self.value,
            "enabled": self.enabled,
            "visible": self.visible,
            "focused": self.focused,
            "frame": self.frame,
            "locator_hint": self.locator_hint,
        }

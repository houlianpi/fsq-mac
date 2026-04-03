# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for adapter registry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fsq_mac.adapters import (
    register_adapter, get_adapter_factory, available_backends,
    _REGISTRY,
)
from fsq_mac.models import ErrorCode
import fsq_mac.session as session_module


class TestAdapterRegistry:
    def test_default_appium_mac2_registered(self):
        assert "appium_mac2" in available_backends()

    def test_get_adapter_factory_returns_callable(self):
        factory = get_adapter_factory("appium_mac2")
        assert callable(factory)

    def test_unknown_backend_raises_valueerror(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            get_adapter_factory("nonexistent_backend")

    def test_unknown_backend_lists_available(self):
        with pytest.raises(ValueError, match="appium_mac2"):
            get_adapter_factory("nonexistent_backend")

    def test_register_custom_backend(self):
        sentinel = object()
        register_adapter("test_backend", lambda c: sentinel)
        try:
            factory = get_adapter_factory("test_backend")
            assert factory({}) is sentinel
            assert "test_backend" in available_backends()
        finally:
            _REGISTRY.pop("test_backend", None)

    def test_available_backends_sorted(self):
        backends = available_backends()
        assert backends == sorted(backends)


class TestUnknownBackendSessionManager:
    def test_session_manager_unknown_backend(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
        with pytest.raises(ValueError, match="Unknown backend"):
            session_module.SessionManager(
                {"server_url": "http://127.0.0.1:4723"},
                backend="nonexistent",
            )

    def test_session_manager_factory_override_skips_registry(self, tmp_path, monkeypatch):
        """adapter_factory= kwarg bypasses the registry entirely."""
        monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
        mock = MagicMock()
        sm = session_module.SessionManager(
            {"server_url": "http://127.0.0.1:4723"},
            adapter_factory=lambda c: mock,
        )
        state = sm.start()
        assert state.session_id == "s1"


class TestUnknownBackendDaemon:
    def test_api_returns_structured_error(self, monkeypatch):
        """When config has an unknown backend, every API call returns INVALID_ARGUMENT."""
        import fsq_mac.daemon as daemon_module

        # Reset global state
        monkeypatch.setattr(daemon_module, "_core", None)
        monkeypatch.setattr(daemon_module, "_core_error", None)
        monkeypatch.setattr(daemon_module, "_load_config", lambda: {
            "server_url": "http://127.0.0.1:4723",
            "backend": "nonexistent_backend",
        })

        from starlette.testclient import TestClient
        client = TestClient(daemon_module.app)
        resp = client.post("/api/session/start", json={})
        data = resp.json()
        assert data["ok"] is False
        assert data["error"]["code"] == ErrorCode.INVALID_ARGUMENT.value
        assert "Unknown backend" in data["error"]["message"]

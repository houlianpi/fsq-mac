# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for adapter registry."""

from __future__ import annotations

import pytest

from fsq_mac.adapters import (
    register_adapter, get_adapter_factory, available_backends,
    _REGISTRY,
)


class TestAdapterRegistry:
    def test_default_appium_mac2_registered(self):
        assert "appium_mac2" in available_backends()

    def test_get_adapter_factory_returns_callable(self):
        factory = get_adapter_factory("appium_mac2")
        assert callable(factory)

    def test_unknown_backend_raises(self):
        with pytest.raises(KeyError):
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

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for plugin system via entry points."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pytest

from fsq_mac.adapters import (
    _REGISTRY,
    _discover_entry_points,
    available_backends,
    register_adapter,
)
from fsq_mac.doctor import check_plugins


@pytest.fixture(autouse=True)
def _restore_registry():
    """Save and restore _REGISTRY between tests."""
    saved = copy.copy(_REGISTRY)
    yield
    _REGISTRY.clear()
    _REGISTRY.update(saved)


def _make_entry_point(name: str, load_return=None, load_raises=None):
    ep = MagicMock()
    ep.name = name
    if load_raises:
        ep.load.side_effect = load_raises
    else:
        ep.load.return_value = load_return or (lambda cfg: None)
    return ep


def test_discover_entry_points_loads_adapter():
    factory = MagicMock()
    ep = _make_entry_point("test_adapter", load_return=factory)

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        _discover_entry_points()

    assert "test_adapter" in _REGISTRY
    assert _REGISTRY["test_adapter"] is factory


def test_discover_entry_points_skips_broken():
    ep = _make_entry_point("broken_adapter", load_raises=ImportError("boom"))

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        _discover_entry_points()

    assert "broken_adapter" not in _REGISTRY


def test_builtin_not_overridden_by_entrypoint():
    original_factory = _REGISTRY.get("appium_mac2")
    assert original_factory is not None

    fake_factory = MagicMock()
    ep = _make_entry_point("appium_mac2", load_return=fake_factory)

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        _discover_entry_points()

    assert _REGISTRY["appium_mac2"] is original_factory


def test_doctor_plugins_lists_adapters():
    result = check_plugins()
    assert "adapters" in result
    assert "doctor_plugins" in result
    assert "appium_mac2" in result["adapters"]
    assert isinstance(result["doctor_plugins"], list)


def test_available_backends_includes_entrypoint():
    factory = MagicMock()
    ep = _make_entry_point("ep_backend", load_return=factory)

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        _discover_entry_points()

    assert "ep_backend" in available_backends()

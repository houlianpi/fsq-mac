# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Adapter registry — maps backend names to factory callables."""

from __future__ import annotations

from typing import Any, Callable

_REGISTRY: dict[str, Callable[[dict], Any]] = {}


def register_adapter(name: str, factory: Callable[[dict], Any]) -> None:
    """Register a backend adapter factory by name."""
    _REGISTRY[name] = factory


def get_adapter_factory(name: str) -> Callable[[dict], Any]:
    """Look up an adapter factory by name.

    Raises ValueError with a descriptive message if the backend is unknown.
    """
    try:
        return _REGISTRY[name]
    except KeyError:
        available = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise ValueError(
            f"Unknown backend {name!r}. Available: {available}"
        ) from None


def available_backends() -> list[str]:
    """Return sorted list of registered backend names."""
    return sorted(_REGISTRY)


def _appium_mac2_factory(config: dict):
    from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
    return AppiumMac2Adapter(config)


register_adapter("appium_mac2", _appium_mac2_factory)


def _discover_entry_points():
    """Load adapters from 'fsq_mac.adapters' entry point group."""
    from importlib.metadata import entry_points
    eps = entry_points(group="fsq_mac.adapters")
    for ep in eps:
        if ep.name not in _REGISTRY:
            try:
                register_adapter(ep.name, ep.load())
            except Exception:
                pass  # skip broken plugins silently

_discover_entry_points()

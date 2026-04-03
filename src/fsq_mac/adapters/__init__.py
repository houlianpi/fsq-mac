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
    """Look up an adapter factory by name. Raises KeyError if unknown."""
    return _REGISTRY[name]


def available_backends() -> list[str]:
    """Return sorted list of registered backend names."""
    return sorted(_REGISTRY)


def _appium_mac2_factory(config: dict):
    from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
    return AppiumMac2Adapter(config)


register_adapter("appium_mac2", _appium_mac2_factory)

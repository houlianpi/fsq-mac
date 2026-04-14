# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Type verification: match, mismatch, and unverifiable cases."""

from __future__ import annotations

from unittest.mock import MagicMock

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter


def _setup_adapter(mock_config):
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    adapter._driver = driver

    el = MagicMock()
    # Store a ref for e0
    adapter._element_refs["e0"] = (adapter._snapshot_generation, el)
    # Mock paste-based input so tests work on Linux CI (no pbcopy/pbpaste)
    adapter._input_text_via_paste = MagicMock()
    return adapter, el


def test_type_verified_match(mock_config):
    adapter, el = _setup_adapter(mock_config)
    el.get_attribute.return_value = "hello"

    result = adapter.type_text("e0", "hello")

    assert result["verified"] is True
    assert result["typed_value"] == "hello"
    assert result["expected"] == "hello"


def test_type_verified_mismatch(mock_config):
    adapter, el = _setup_adapter(mock_config)
    el.get_attribute.return_value = "helo"  # typo

    result = adapter.type_text("e0", "hello")

    assert result["verified"] is False
    assert result["typed_value"] == "helo"
    assert result["expected"] == "hello"


def test_type_unverifiable(mock_config):
    adapter, el = _setup_adapter(mock_config)
    el.get_attribute.side_effect = Exception("attribute not supported")

    result = adapter.type_text("e0", "hello")

    assert result["verified"] is None
    assert result["expected"] == "hello"

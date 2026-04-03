# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for adapter helper functions that don't require a real Appium driver."""

from __future__ import annotations

import pytest

from fsq_mac.adapters.appium_mac2 import (
    parse_ui_tree, simplify_page_source,
    _safe_applescript_str, _is_visible, _parse_frame, _resolve_locator,
)


class TestSafeApplescriptStr:
    def test_safe_string(self):
        assert _safe_applescript_str("com.apple.finder") == "com.apple.finder"

    def test_double_quote_rejected(self):
        with pytest.raises(ValueError):
            _safe_applescript_str('com.test"app')

    def test_backslash_rejected(self):
        with pytest.raises(ValueError):
            _safe_applescript_str("com.test\\app")


class TestIsVisible:
    def test_visible(self):
        assert _is_visible({"visible": "true", "width": "100", "height": "50"}) is True

    def test_hidden_by_visible(self):
        assert _is_visible({"visible": "false"}) is False

    def test_hidden_by_displayed(self):
        assert _is_visible({"displayed": "false"}) is False

    def test_hidden_zero_width(self):
        assert _is_visible({"width": "0"}) is False

    def test_hidden_zero_height(self):
        assert _is_visible({"height": "0"}) is False

    def test_empty_attribs(self):
        assert _is_visible({}) is True


class TestParseFrame:
    def test_valid_frame(self):
        result = _parse_frame({"x": "10", "y": "20", "width": "100", "height": "50"})
        assert result == {"x": 10, "y": 20, "width": 100, "height": 50}

    def test_defaults(self):
        result = _parse_frame({})
        assert result == {"x": 0, "y": 0, "width": 0, "height": 0}

    def test_invalid_values(self):
        result = _parse_frame({"x": "abc"})
        assert result is None


class TestResolveLocator:
    def test_accessibility_id(self):
        by, val = _resolve_locator("accessibility_id", "myButton")
        assert val == "myButton"

    def test_xpath(self):
        by, val = _resolve_locator("xpath", "//XCUIElementTypeButton")
        assert val == "//XCUIElementTypeButton"

    def test_empty_defaults(self):
        by, val = _resolve_locator("", "test")
        assert val == "test"

    def test_unknown_strategy_defaults(self):
        by, val = _resolve_locator("nonexistent", "test")
        assert val == "test"


class TestParseUiTree:
    def test_empty_source(self):
        result = parse_ui_tree("")
        assert result == []

    def test_single_button(self):
        source = '<AppiumAUT><XCUIElementTypeButton name="OK" visible="true" width="50" height="30"/></AppiumAUT>'
        result = parse_ui_tree(source)
        assert len(result) == 1
        assert result[0].role == "Button"
        assert result[0].name == "OK"
        assert result[0].element_id == "e0"

    def test_hidden_elements_skipped(self):
        source = '<AppiumAUT><XCUIElementTypeButton name="Hidden" visible="false"/><XCUIElementTypeButton name="Visible" visible="true" width="50" height="30"/></AppiumAUT>'
        result = parse_ui_tree(source)
        assert len(result) == 1
        assert result[0].name == "Visible"

    def test_max_elements(self):
        buttons = "".join(f'<XCUIElementTypeButton name="b{i}" visible="true" width="10" height="10"/>' for i in range(10))
        source = f"<AppiumAUT>{buttons}</AppiumAUT>"
        result = parse_ui_tree(source, max_elements=3)
        assert len(result) == 3

    def test_hierarchy_skipped(self):
        source = '<hierarchy><XCUIElementTypeButton name="OK" visible="true" width="50" height="30"/></hierarchy>'
        result = parse_ui_tree(source)
        assert len(result) == 1

    def test_unnamed_group_skipped(self):
        source = '<AppiumAUT><XCUIElementTypeGroup visible="true" width="50" height="30"/></AppiumAUT>'
        result = parse_ui_tree(source)
        assert len(result) == 0

    def test_invalid_xml(self):
        result = parse_ui_tree("not xml at all")
        assert result == []


class TestSimplifyPageSource:
    def test_small_source_unchanged(self):
        source = "<root><child/></root>"
        result = simplify_page_source(source)
        assert result == source

    def test_invalid_xml_truncated(self):
        source = "x" * 300000
        result = simplify_page_source(source, max_size=200000)
        assert len(result) == 200000

    def test_large_valid_xml_filtered(self):
        # Build a large XML with visible and invisible elements
        visible = '<XCUIElementTypeButton name="OK" visible="true" width="50" height="30"/>'
        invisible = '<XCUIElementTypeButton name="Hidden" visible="false" width="0" height="0"/>'
        # Create enough content to exceed max_size threshold
        content = (visible + invisible) * 5000
        source = f"<AppiumAUT>{content}</AppiumAUT>"
        result = simplify_page_source(source, max_size=len(source) - 1)
        # Invisible elements should be removed, result should be smaller
        assert len(result) < len(source)
        assert "Hidden" not in result

    def test_large_xml_long_attributes_truncated(self):
        # Build XML with very long attribute values
        long_text = "a" * 200
        content = f'<XCUIElementTypeStaticText name="OK" visible="true" width="50" height="30" text="{long_text}"/>' * 2000
        source = f"<AppiumAUT>{content}</AppiumAUT>"
        result = simplify_page_source(source, max_size=len(source) - 1)
        # Long text attrs should be truncated to 100 chars
        assert "..." in result

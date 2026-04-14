# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Inspect ref binding: two buttons with the same name bind to different WebElements."""

from __future__ import annotations

from unittest.mock import MagicMock

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter


def test_duplicate_name_elements_get_distinct_refs(mock_config):
    """Two buttons named '5' should bind to different WebElements by doc-order index."""
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    adapter._driver = driver

    # Page source with two buttons having the same name
    driver.page_source = (
        '<AppiumAUT>'
        '<XCUIElementTypeButton name="5" visible="true" enabled="true" x="0" y="0" width="50" height="50"/>'
        '<XCUIElementTypeButton name="5" visible="true" enabled="true" x="60" y="0" width="50" height="50"/>'
        '</AppiumAUT>'
    )

    # Create two distinct mock WebElements
    web_el_0 = MagicMock(name="WebElement_0")
    web_el_0.location = {"x": 0, "y": 0}
    web_el_1 = MagicMock(name="WebElement_1")
    web_el_1.location = {"x": 60, "y": 0}

    # find_elements(//*) returns all elements in document order
    driver.find_elements.return_value = [web_el_0, web_el_1]

    elements = adapter.inspect()

    assert len(elements) == 2
    assert elements[0]["name"] == "5"
    assert elements[1]["name"] == "5"

    # The refs should point to different WebElements
    ref_e0 = adapter._element_refs.get("e0")
    ref_e1 = adapter._element_refs.get("e1")
    assert ref_e0 is not None
    assert ref_e1 is not None
    # Extract from (generation, element, name, frame, visible, enabled, role) tuple
    _, actual_e0, name_e0, frame_e0, vis_e0, en_e0, role_e0 = ref_e0
    _, actual_e1, name_e1, frame_e1, vis_e1, en_e1, role_e1 = ref_e1
    assert actual_e0 is web_el_0
    assert actual_e1 is web_el_1
    assert name_e0 == "5"
    assert name_e1 == "5"
    assert frame_e0 == {"x": 0, "y": 0, "width": 50, "height": 50}
    assert frame_e1 == {"x": 60, "y": 0, "width": 50, "height": 50}
    assert vis_e0 is True
    assert vis_e1 is True
    assert en_e0 is True
    assert en_e1 is True
    assert role_e0 == "Button"
    assert role_e1 == "Button"


def test_inspect_elements_include_ref_bound(mock_config):
    """inspect() output dicts should include ref_bound field."""
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    adapter._driver = driver

    driver.page_source = (
        '<AppiumAUT>'
        '<XCUIElementTypeButton name="OK" visible="true" enabled="true" x="0" y="0" width="50" height="50"/>'
        '</AppiumAUT>'
    )
    web_el = MagicMock(name="WebElement_0")
    web_el.location = {"x": 0, "y": 0}
    driver.find_elements.return_value = [web_el]

    elements = adapter.inspect()
    assert len(elements) >= 1
    assert elements[0]["ref_bound"] is True
    assert elements[0]["ref"] == "e0"
    assert elements[0]["element_bounds"] == {"x": 0, "y": 0, "width": 50, "height": 50}
    assert elements[0]["center"] == {"x": 25, "y": 25}
    assert elements[0]["ref_status"] == "bound"
    assert elements[0]["state_source"] == "xml"


def test_inspect_unbound_element_has_ref_bound_false(mock_config):
    """Elements beyond find_elements range should have ref_bound=False."""
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    adapter._driver = driver

    driver.page_source = (
        '<AppiumAUT>'
        '<XCUIElementTypeButton name="A" visible="true" enabled="true" x="0" y="0" width="50" height="50"/>'
        '<XCUIElementTypeButton name="B" visible="true" enabled="true" x="60" y="0" width="50" height="50"/>'
        '</AppiumAUT>'
    )
    # Only return 1 WebElement — second element can't be bound
    web_el = MagicMock(name="WebElement_0")
    web_el.location = {"x": 0, "y": 0}
    driver.find_elements.return_value = [web_el]

    elements = adapter.inspect()
    assert len(elements) == 2
    assert elements[0]["ref_bound"] is True
    assert elements[1]["ref_bound"] is False
    assert elements[1]["ref_status"] == "unbound"
    assert elements[1]["state_source"] == "xml"


def test_inspect_no_alignment_verification(mock_config):
    """After removing alignment verification, inspect should not call get_attribute on WebElements."""
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    adapter._driver = driver

    driver.page_source = (
        '<AppiumAUT>'
        '<XCUIElementTypeButton name="OK" visible="true" enabled="true" x="0" y="0" width="50" height="50"/>'
        '</AppiumAUT>'
    )
    web_el = MagicMock(name="WebElement_0")
    web_el.location = {"x": 0, "y": 0}
    driver.find_elements.return_value = [web_el]

    adapter.inspect()

    # After removing alignment verification, we should NOT query get_attribute("name")
    # on WebElements during inspect (that was the verification step)
    web_el.get_attribute.assert_not_called()

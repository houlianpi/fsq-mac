# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Element find returns separate name and label attributes."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter


def test_find_returns_name_and_label(mock_config):
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    adapter._driver = driver

    # Mock a WebElement with distinct name and label
    el = MagicMock()
    el.location = {"x": 10, "y": 20}
    el.size = {"width": 100, "height": 30}
    type(el).tag_name = PropertyMock(return_value="XCUIElementTypeButton")

    def _get_attr(attr):
        if attr == "name":
            return "myName"
        if attr == "label":
            return "myLabel"
        return ""

    el.get_attribute = _get_attr

    with patch("fsq_mac.adapters.appium_mac2.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.return_value = el
        driver.find_elements.return_value = [el]

        status, elements = adapter.find("myName", "accessibility_id")

    assert status == "exactly_one_match"
    assert len(elements) == 1
    assert elements[0]["name"] == "myName"
    assert elements[0]["label"] == "myLabel"

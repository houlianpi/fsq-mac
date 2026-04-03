"""Test screenshot variants: full, element, rect."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
from fsq_mac.models import ErrorCode


@pytest.fixture()
def mock_config():
    return {
        "server_url": "http://127.0.0.1:4723",
        "platformName": "mac",
        "automationName": "Mac2",
        "bundleId": "com.apple.calculator",
    }


@pytest.fixture()
def mock_driver():
    driver = MagicMock()
    driver.capabilities = {"bundleId": "com.apple.calculator"}
    return driver


@pytest.fixture()
def adapter(mock_config, mock_driver):
    a = AppiumMac2Adapter(mock_config)
    a._driver = mock_driver
    return a


def test_screenshot_element_ok(adapter, tmp_path):
    mock_el = MagicMock()
    mock_el.location = {"x": 100, "y": 200}
    type(mock_el).screenshot_as_png = PropertyMock(return_value=b"\x89PNG_fake_data")
    adapter._store_ref("e0", mock_el)

    path = str(tmp_path / "el.png")
    result = adapter.screenshot_element("e0", path)
    assert "error_code" not in result
    assert result["path"] == path
    assert result["size_bytes"] > 0
    assert os.path.exists(path)


def test_screenshot_element_not_found(adapter, tmp_path):
    path = str(tmp_path / "el.png")
    with patch.object(adapter, "_resolve_ref", return_value=(None, ErrorCode.ELEMENT_NOT_FOUND)):
        result = adapter.screenshot_element("e99", path)
    assert result["error_code"] == ErrorCode.ELEMENT_NOT_FOUND


def test_screenshot_rect_ok(adapter, tmp_path):
    path = str(tmp_path / "rect.png")
    with patch("fsq_mac.adapters.appium_mac2.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # Create a fake file so size_bytes works
        with open(path, "wb") as f:
            f.write(b"\x89PNG_fake")
        result = adapter.screenshot_rect("100,200,300,400", path)
    assert "error_code" not in result
    assert result["path"] == path
    mock_run.assert_called_once()


def test_screenshot_rect_invalid_format(adapter, tmp_path):
    path = str(tmp_path / "rect.png")
    result = adapter.screenshot_rect("invalid", path)
    assert result["error_code"] == ErrorCode.INVALID_ARGUMENT

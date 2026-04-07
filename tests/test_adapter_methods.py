# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for adapter methods using a mock driver (no real Appium)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter, AppiumBy
from fsq_mac.models import ErrorCode, LocatorQuery


@pytest.fixture()
def adapter_with_driver(mock_config, mock_driver):
    a = AppiumMac2Adapter(mock_config)
    a._driver = mock_driver
    return a


class TestLifecycle:
    def test_connected_true(self, adapter_with_driver):
        assert adapter_with_driver.connected is True

    def test_connected_false_no_driver(self):
        a = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        assert a.connected is False

    def test_connected_false_exception(self, adapter_with_driver):
        adapter_with_driver._driver.get_window_size.side_effect = Exception("dead")
        assert adapter_with_driver.connected is False

    def test_disconnect(self, adapter_with_driver):
        adapter_with_driver.disconnect()
        assert adapter_with_driver._driver is None

    def test_disconnect_no_driver(self):
        a = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        a.disconnect()  # should not raise


class TestElementRefs:
    def test_store_and_get(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        el, err = adapter_with_driver._get_ref("e0")
        assert el is mock_el
        assert err is None

    def test_get_nonexistent(self, adapter_with_driver):
        el, err = adapter_with_driver._get_ref("e99")
        assert el is None
        assert err == ErrorCode.ELEMENT_NOT_FOUND

    def test_stale_after_invalidate(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        adapter_with_driver._invalidate_refs()
        el, err = adapter_with_driver._get_ref("e0")
        assert el is None
        assert err == ErrorCode.ELEMENT_REFERENCE_STALE

    def test_stale_on_location_exception(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = property(lambda self: (_ for _ in ()).throw(Exception("stale")))
        type(mock_el).location = PropertyMock(side_effect=Exception("stale"))
        adapter_with_driver._store_ref("e0", mock_el)
        el, err = adapter_with_driver._get_ref("e0")
        assert el is None
        assert err == ErrorCode.ELEMENT_REFERENCE_STALE


class TestResolveRef:
    def test_resolve_by_element_id(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        el, err = adapter_with_driver._resolve_ref("e0")
        assert el is mock_el
        assert err is None

    def test_resolve_stale_returns_error(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        adapter_with_driver._invalidate_refs()
        el, err = adapter_with_driver._resolve_ref("e0")
        assert el is None
        assert err == ErrorCode.ELEMENT_REFERENCE_STALE

    def test_resolve_by_locator(self, adapter_with_driver):
        mock_el = MagicMock()
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        el, err = adapter_with_driver._resolve_ref("myButton", strategy="accessibility_id")
        assert el is mock_el
        assert err is None

    def test_resolve_not_found(self, adapter_with_driver):
        adapter_with_driver._driver.find_elements.return_value = []
        with patch("fsq_mac.adapters.appium_mac2.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = Exception("timeout")
            el, err = adapter_with_driver._resolve_ref("nonexistent")
        assert el is None
        assert err == ErrorCode.ELEMENT_NOT_FOUND

    def test_resolve_query_role_name(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        mock_el.size = {"width": 100, "height": 50}
        mock_el.get_attribute.side_effect = lambda attr: {
            "role": "AXButton",
            "name": "Submit",
            "label": "Submit",
        }.get(attr, "")
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        el, err = adapter_with_driver._resolve_ref(LocatorQuery(role="AXButton", name="Submit"))
        assert el is mock_el
        assert err is None

    def test_resolve_query_prefers_label_before_xpath(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        mock_el.size = {"width": 100, "height": 50}
        mock_el.get_attribute.side_effect = lambda attr: {
            "label": "Search",
            "name": "Ignored",
        }.get(attr, "")

        def _find_elements(by, value):
            if value == "//*[(@label='Search')]":
                return [mock_el]
            return []

        adapter_with_driver._driver.find_elements.side_effect = _find_elements
        el, err = adapter_with_driver._resolve_ref(LocatorQuery(label="Search", xpath="//wrong"))
        assert el is mock_el
        assert err is None

    def test_resolve_query_uses_direct_xpath_instead_of_full_tree_scan(self, adapter_with_driver):
        mock_el = MagicMock()
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        query = LocatorQuery(role="AXButton", label="5")
        el, err = adapter_with_driver._resolve_ref(query)
        assert el is mock_el
        assert err is None
        adapter_with_driver._driver.find_elements.assert_called_once_with(
            AppiumBy.XPATH,
            "//*[(self::XCUIElementTypeButton) and (@label='5')]",
        )


class TestClick:
    def test_click_success(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        with patch("time.sleep"), patch("fsq_mac.adapters.appium_mac2.ActionChains"):
            result = adapter_with_driver.click("e0")
        assert result == {}

    def test_click_not_found(self, adapter_with_driver):
        adapter_with_driver._driver.find_elements.return_value = []
        with patch("fsq_mac.adapters.appium_mac2.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = Exception("timeout")
            result = adapter_with_driver.click("nonexistent")
        assert result["error_code"] == ErrorCode.ELEMENT_NOT_FOUND

    def test_click_fallback(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        # ActionChains fails, falls back to el.click()
        with patch("fsq_mac.adapters.appium_mac2.ActionChains") as MockAC:
            MockAC.return_value.move_to_element.return_value.click.return_value.perform.side_effect = Exception("fail")
            with patch("time.sleep"):
                result = adapter_with_driver.click("e0")
        assert result == {}

    def test_click_falls_back_to_coordinate_click_when_driver_click_paths_fail(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 10, "y": 20}
        mock_el.size = {"width": 80, "height": 40}
        adapter_with_driver._store_ref("e0", mock_el)
        with patch("fsq_mac.adapters.appium_mac2.ActionChains") as MockAC:
            MockAC.return_value.move_to_element.return_value.click.return_value.perform.side_effect = Exception("hang path")
            mock_el.click.side_effect = Exception("element click failed")
            with patch.object(adapter_with_driver, "input_click_at", return_value={}) as mock_click_at:
                with patch("time.sleep"):
                    result = adapter_with_driver.click("e0")
        assert result == {}
        mock_click_at.assert_called_once_with(50, 40)

    def test_click_waits_for_actionable_query(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 10, "y": 20}
        mock_el.size = {"width": 80, "height": 30}
        mock_el.is_displayed.return_value = True
        mock_el.get_attribute.side_effect = lambda attr: {
            "enabled": "true",
            "visible": "true",
            "displayed": "true",
            "role": "AXButton",
            "name": "Submit",
        }.get(attr, "")
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        with patch("time.sleep"), patch("fsq_mac.adapters.appium_mac2.ActionChains"):
            result = adapter_with_driver.click(LocatorQuery(role="AXButton", name="Submit"))
        assert result == {}

    def test_click_timeout_when_disabled(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 10, "y": 20}
        mock_el.size = {"width": 80, "height": 30}
        mock_el.is_displayed.return_value = True
        mock_el.get_attribute.side_effect = lambda attr: {
            "enabled": "false",
            "visible": "true",
            "displayed": "true",
            "role": "AXButton",
            "name": "Submit",
        }.get(attr, "")
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        with patch("time.sleep"), patch("time.time") as mock_time:
            mock_time.side_effect = [0.0, 0.2, 0.4, 0.6, 1.2]
            result = adapter_with_driver.click(LocatorQuery(role="AXButton", name="Submit"), timeout=1)
        assert result["error_code"] == ErrorCode.TIMEOUT


class TestRightClick:
    def test_right_click_success(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        with patch("time.sleep"), patch("fsq_mac.adapters.appium_mac2.ActionChains"):
            result = adapter_with_driver.right_click("e0")
        assert result == {}

    def test_right_click_error(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        with patch("fsq_mac.adapters.appium_mac2.ActionChains") as MockAC:
            MockAC.return_value.context_click.return_value.perform.side_effect = Exception("fail")
            result = adapter_with_driver.right_click("e0")
        assert result["error_code"] == ErrorCode.ELEMENT_NOT_FOUND


class TestDoubleClick:
    def test_double_click_success(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 10, "y": 20}
        mock_el.size = {"width": 100, "height": 50}
        adapter_with_driver._store_ref("e0", mock_el)
        with patch("time.sleep"):
            result = adapter_with_driver.double_click("e0")
        assert result == {}


class TestHover:
    def test_hover_success(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        with patch("time.sleep"), patch("fsq_mac.adapters.appium_mac2.ActionChains"):
            result = adapter_with_driver.hover("e0", duration=0)
        assert result == {}


class TestTypeText:
    def test_type_verified(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        mock_el.get_attribute.return_value = "hello"
        adapter_with_driver._store_ref("e0", mock_el)
        result = adapter_with_driver.type_text("e0", "hello")
        assert result["verified"] is True

    def test_type_mismatch(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        mock_el.get_attribute.return_value = "wrong"
        adapter_with_driver._store_ref("e0", mock_el)
        result = adapter_with_driver.type_text("e0", "hello")
        assert result["verified"] is False


class TestScroll:
    def test_scroll_success(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        adapter_with_driver._store_ref("e0", mock_el)
        result = adapter_with_driver.scroll("e0", "down")
        assert result == {}


class TestDrag:
    def test_drag_success(self, adapter_with_driver):
        src = MagicMock()
        src.location = {"x": 0, "y": 0}
        tgt = MagicMock()
        tgt.location = {"x": 10, "y": 10}
        adapter_with_driver._store_ref("e0", src)
        adapter_with_driver._store_ref("e1", tgt)
        with patch("fsq_mac.adapters.appium_mac2.ActionChains"):
            result = adapter_with_driver.drag("e0", "e1")
        assert result == {}

    def test_drag_source_not_found(self, adapter_with_driver):
        result = adapter_with_driver.drag("e99", "e98")
        assert result["error_code"] == ErrorCode.ELEMENT_NOT_FOUND


class TestInputKey:
    def test_input_key_success(self, adapter_with_driver):
        result = adapter_with_driver.input_key("return")
        assert result == {}
        adapter_with_driver._driver.execute_script.assert_called()

    def test_input_key_space(self, adapter_with_driver):
        result = adapter_with_driver.input_key("space")
        assert result == {}

    def test_input_key_error(self, adapter_with_driver):
        adapter_with_driver._driver.execute_script.side_effect = Exception("fail")
        result = adapter_with_driver.input_key("return")
        assert result["error_code"] == ErrorCode.INTERNAL_ERROR


class TestInputHotkey:
    def test_hotkey_command_c(self, adapter_with_driver):
        with patch("time.sleep"):
            result = adapter_with_driver.input_hotkey("command+c")
        assert result == {}

    def test_hotkey_shift_alt_fn(self, adapter_with_driver):
        with patch("time.sleep"):
            result = adapter_with_driver.input_hotkey("shift+alt+fn+a")
        assert result == {}

    def test_hotkey_ctrl(self, adapter_with_driver):
        with patch("time.sleep"):
            result = adapter_with_driver.input_hotkey("ctrl+c")
        assert result == {}


class TestInputText:
    def test_input_text_success(self, adapter_with_driver):
        with patch("time.sleep"):
            result = adapter_with_driver.input_text("hello")
        assert result == {}


class TestPhase2Methods:
    def test_assert_visible_success(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        mock_el.size = {"width": 100, "height": 50}
        mock_el.is_displayed.return_value = True
        mock_el.get_attribute.side_effect = lambda attr: {
            "visible": "true",
            "displayed": "true",
            "enabled": "true",
            "role": "AXButton",
            "name": "Submit",
        }.get(attr, "")
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        result = adapter_with_driver.assert_visible(LocatorQuery(role="AXButton", name="Submit"))
        assert result == {}

    def test_assert_text_failure(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        mock_el.size = {"width": 100, "height": 50}
        mock_el.text = "Busy"
        mock_el.get_attribute.side_effect = lambda attr: {
            "value": "Busy",
            "name": "Status",
            "role": "AXStaticText",
        }.get(attr, "")
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        result = adapter_with_driver.assert_text(LocatorQuery(role="AXStaticText", name="Status"), "Ready")
        assert result["error_code"] == ErrorCode.ASSERTION_FAILED

    def test_assert_text_allows_empty_string(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        mock_el.size = {"width": 100, "height": 50}
        mock_el.text = ""
        mock_el.get_attribute.side_effect = lambda attr: {
            "name": "Status",
            "role": "AXStaticText",
            "value": "fallback value",
        }.get(attr, "")
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        result = adapter_with_driver.assert_text(LocatorQuery(role="AXStaticText", name="Status"), "")
        assert result == {}

    def test_input_click_at_success(self, adapter_with_driver):
        with patch.object(adapter_with_driver, "_run_with_timeout", side_effect=lambda fn, timeout=None: fn()):
            result = adapter_with_driver.input_click_at(100, 200)
        assert result == {}
        adapter_with_driver._driver.execute_script.assert_called_once_with("macos: click", {"x": 100, "y": 200})

    def test_menu_click_success(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = adapter_with_driver.menu_click("File > Open")
        assert result == {}

    def test_menu_click_rejects_empty_path(self, adapter_with_driver):
        result = adapter_with_driver.menu_click("   >   ")
        assert result["error_code"] == ErrorCode.INVALID_ARGUMENT

    def test_menu_click_supports_nested_submenus(self, adapter_with_driver):
        def _run(cmd, **kwargs):
            script = cmd[2]
            if "repeat with i from 2 to (count of menuParts)" not in script:
                return MagicMock(returncode=1, stderr="missing nested traversal")
            return MagicMock(returncode=0, stderr="")

        with patch("subprocess.run", side_effect=_run):
            result = adapter_with_driver.menu_click("File > Export > PDF")
        assert result == {}

    def test_input_text_error(self, adapter_with_driver):
        adapter_with_driver._driver.execute_script.side_effect = Exception("fail")
        with patch("time.sleep"):
            result = adapter_with_driver.input_text("hello")
        assert result["error_code"] == ErrorCode.INTERNAL_ERROR


class TestScreenshot:
    def test_screenshot_success(self, adapter_with_driver, tmp_path):
        adapter_with_driver._driver.get_screenshot_as_png.return_value = b"\x89PNG"
        path = str(tmp_path / "test.png")
        result = adapter_with_driver.screenshot(path)
        assert result["path"] == path
        assert result["size_bytes"] == 4

    def test_screenshot_error(self, adapter_with_driver, tmp_path):
        adapter_with_driver._driver.get_screenshot_as_png.side_effect = Exception("fail")
        result = adapter_with_driver.screenshot(str(tmp_path / "test.png"))
        assert result["error_code"] == ErrorCode.INTERNAL_ERROR


class TestUiTree:
    def test_ui_tree(self, adapter_with_driver):
        adapter_with_driver._driver.page_source = "<root/>"
        result = adapter_with_driver.ui_tree()
        assert "<root" in result


class TestInspect:
    def test_inspect_empty(self, adapter_with_driver):
        adapter_with_driver._driver.page_source = "<AppiumAUT/>"
        adapter_with_driver._driver.find_elements.return_value = []
        result = adapter_with_driver.inspect()
        assert result == []

    def test_inspect_with_elements(self, adapter_with_driver):
        adapter_with_driver._driver.page_source = '<AppiumAUT><XCUIElementTypeButton name="OK" visible="true" width="50" height="30"/></AppiumAUT>'
        mock_el = MagicMock()
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        result = adapter_with_driver.inspect()
        assert len(result) == 1
        assert result[0]["role"] == "Button"


class TestFind:
    def test_find_success(self, adapter_with_driver):
        mock_el = MagicMock()
        mock_el.tag_name = "XCUIElementTypeButton"
        mock_el.location = {"x": 0, "y": 0}
        mock_el.size = {"width": 100, "height": 50}
        mock_el.get_attribute.return_value = "OK"
        adapter_with_driver._driver.find_elements.return_value = [mock_el]
        with patch("fsq_mac.adapters.appium_mac2.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = mock_el
            status, elements = adapter_with_driver.find("OK")
        assert status == "exactly_one_match"
        assert len(elements) == 1

    def test_find_no_match(self, adapter_with_driver):
        with patch("fsq_mac.adapters.appium_mac2.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = Exception("not found")
            status, elements = adapter_with_driver.find("nonexistent")
        assert status == "no_match"

    def test_find_multiple(self, adapter_with_driver):
        mock_els = [MagicMock(), MagicMock()]
        for el in mock_els:
            el.tag_name = "XCUIElementTypeButton"
            el.location = {"x": 0, "y": 0}
            el.size = {"width": 100, "height": 50}
            el.get_attribute.return_value = "btn"
        adapter_with_driver._driver.find_elements.return_value = mock_els
        with patch("fsq_mac.adapters.appium_mac2.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = mock_els[0]
            status, elements = adapter_with_driver.find("btn")
        assert status == "multiple_matches"
        assert len(elements) == 2


class TestManagedBundleId:
    def test_from_capabilities(self, adapter_with_driver):
        assert adapter_with_driver._managed_bundle_id() == "com.apple.calculator"

    def test_no_driver(self):
        a = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        assert a._managed_bundle_id() == ""


class TestCheckServer:
    def test_pass(self, adapter_with_driver):
        with patch("httpx.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            ok, msg = adapter_with_driver.check_server()
        assert ok is True

    def test_fail(self, adapter_with_driver):
        with patch("httpx.get", side_effect=Exception("down")):
            ok, msg = adapter_with_driver.check_server()
        assert ok is False


class TestScreenshotElement:
    def test_screenshot_element_success(self, adapter_with_driver, tmp_path):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        type(mock_el).screenshot_as_png = PropertyMock(return_value=b"\x89PNG_DATA")
        adapter_with_driver._store_ref("e0", mock_el)
        path = str(tmp_path / "el.png")
        result = adapter_with_driver.screenshot_element("e0", path)
        assert result["path"] == path
        assert result["size_bytes"] == 9

    def test_screenshot_element_not_found(self, adapter_with_driver, tmp_path):
        adapter_with_driver._driver.find_elements.return_value = []
        with patch("fsq_mac.adapters.appium_mac2.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = Exception("timeout")
            result = adapter_with_driver.screenshot_element("e99", str(tmp_path / "el.png"))
        assert result["error_code"] == ErrorCode.ELEMENT_NOT_FOUND

    def test_screenshot_element_error(self, adapter_with_driver, tmp_path):
        mock_el = MagicMock()
        mock_el.location = {"x": 0, "y": 0}
        type(mock_el).screenshot_as_png = PropertyMock(side_effect=Exception("fail"))
        adapter_with_driver._store_ref("e0", mock_el)
        result = adapter_with_driver.screenshot_element("e0", str(tmp_path / "el.png"))
        assert result["error_code"] == ErrorCode.INTERNAL_ERROR


class TestScreenshotRect:
    def test_screenshot_rect_success(self, adapter_with_driver, tmp_path):
        path = str(tmp_path / "rect.png")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            # Create the file to simulate screencapture
            with open(path, "wb") as f:
                f.write(b"\x89PNG")
            result = adapter_with_driver.screenshot_rect("0,0,100,100", path)
        assert result["path"] == path

    def test_screenshot_rect_bad_format(self, adapter_with_driver, tmp_path):
        result = adapter_with_driver.screenshot_rect("0,0,100", str(tmp_path / "r.png"))
        assert result["error_code"] == ErrorCode.INVALID_ARGUMENT

    def test_screenshot_rect_non_integer(self, adapter_with_driver, tmp_path):
        result = adapter_with_driver.screenshot_rect("a,b,c,d", str(tmp_path / "r.png"))
        assert result["error_code"] == ErrorCode.INVALID_ARGUMENT


class TestWindowCurrent:
    def test_window_current_applescript(self, adapter_with_driver):
        sep = "\x1f"
        stdout = f"Finder{sep}com.apple.finder{sep}Documents{sep}100{sep}200{sep}800{sep}600\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=stdout)
            result = adapter_with_driver.window_current()
        assert result["app_name"] == "Finder"
        assert result["title"] == "Documents"
        assert result["width"] == 800

    def test_window_current_fallback(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = adapter_with_driver.window_current()
        # Falls back to driver.get_window_size
        assert result.get("width") == 400

    def test_window_current_exception(self, adapter_with_driver):
        adapter_with_driver._driver.get_window_size.side_effect = Exception("fail")
        with patch("subprocess.run", side_effect=Exception("no osascript")):
            result = adapter_with_driver.window_current()
        assert result == {}


class TestWindowList:
    def test_window_list_success(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Window 1, Window 2\n")
            result = adapter_with_driver.window_list()
        assert len(result) == 2
        assert result[0]["title"] == "Window 1"
        assert result[1]["index"] == 1

    def test_window_list_empty(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = adapter_with_driver.window_list()
        assert result == []

    def test_window_list_no_bundle(self):
        a = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        result = a.window_list()
        assert result == []


class TestWindowFocus:
    def test_window_focus_success(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run:
            # First call: window_list, second call: focus
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="Window 1, Window 2\n"),
                MagicMock(returncode=0),
            ]
            result = adapter_with_driver.window_focus(0)
        assert result["focused"] == 0

    def test_window_focus_out_of_range(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Window 1\n")
            result = adapter_with_driver.window_focus(5)
        assert result["error_code"] == ErrorCode.WINDOW_NOT_FOUND

    def test_window_focus_no_bundle(self):
        a = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        result = a.window_focus(0)
        assert result["error_code"] == ErrorCode.WINDOW_NOT_FOUND


class TestWaitElement:
    def test_wait_element_found(self, adapter_with_driver):
        with patch("fsq_mac.adapters.appium_mac2.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = MagicMock()
            result = adapter_with_driver.wait_element("btn", timeout=1)
        assert result is True

    def test_wait_element_timeout(self, adapter_with_driver):
        with patch("fsq_mac.adapters.appium_mac2.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = Exception("timeout")
            result = adapter_with_driver.wait_element("btn", timeout=1)
        assert result is False


class TestWaitWindow:
    def test_wait_window_found(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run, patch("time.sleep"), patch("time.time") as mock_time:
            mock_time.side_effect = [0, 0, 20]
            mock_run.return_value = MagicMock(returncode=0, stdout="Test Window\n")
            result = adapter_with_driver.wait_window("Test", timeout=10)
        assert result is True

    def test_wait_window_timeout(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run, patch("time.sleep"), patch("time.time") as mock_time:
            mock_time.side_effect = [0, 20]
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = adapter_with_driver.wait_window("Nope", timeout=0)
        assert result is False

    def test_wait_window_no_bundle(self):
        a = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        result = a.wait_window("Test", timeout=1)
        assert result is False


class TestWaitApp:
    def test_wait_app_found(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run, patch("time.sleep"), patch("time.time") as mock_time:
            mock_time.side_effect = [0, 0, 20]
            mock_run.return_value = MagicMock(returncode=0, stdout="com.test\n")
            result = adapter_with_driver.wait_app("com.test", timeout=10)
        assert result is True

    def test_wait_app_timeout(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run, patch("time.sleep"), patch("time.time") as mock_time:
            mock_time.side_effect = [0, 20]
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = adapter_with_driver.wait_app("com.test", timeout=0)
        assert result is False


class TestAppActivate:
    def test_activate_success(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            mock_run.return_value = MagicMock(returncode=0, stdout="Calculator\n")
            result = adapter_with_driver.app_activate("com.apple.calculator")
        assert result["bundle_id"] == "com.apple.calculator"

    def test_activate_no_driver(self):
        a = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        result = a.app_activate("com.test")
        assert result["error_code"] == ErrorCode.BACKEND_UNAVAILABLE

    def test_activate_driver_fails_falls_back(self, adapter_with_driver):
        adapter_with_driver._driver.activate_app.side_effect = Exception("unsupported")
        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            mock_run.return_value = MagicMock(returncode=0, stdout="Calculator\n")
            result = adapter_with_driver.app_activate("com.apple.calculator")
        assert result["bundle_id"] == "com.apple.calculator"


class TestAppTerminate:
    def test_terminate_success(self, adapter_with_driver):
        result = adapter_with_driver.app_terminate("com.apple.calculator")
        assert result.get("terminated") is not None or result.get("bundle_id") is not None

    def test_terminate_no_driver(self):
        a = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        result = a.app_terminate("com.test")
        assert result["error_code"] == ErrorCode.BACKEND_UNAVAILABLE


class TestAppList:
    def test_app_list_success(self, adapter_with_driver):
        sep = "\x1f"
        stdout = f"Finder{sep}com.apple.finder\nSafari{sep}com.apple.Safari\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=stdout)
            result = adapter_with_driver.app_list()
        assert len(result) == 2
        assert result[0]["name"] == "Finder"

    def test_app_list_error(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = adapter_with_driver.app_list()
        assert result == []

    def test_app_list_exception(self, adapter_with_driver):
        with patch("subprocess.run", side_effect=Exception("fail")):
            result = adapter_with_driver.app_list()
        assert result == []


class TestAppCurrent:
    def test_app_current_applescript(self, adapter_with_driver):
        sep = "\x1f"
        stdout = f"Safari{sep}com.apple.Safari\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=stdout)
            result = adapter_with_driver.app_current()
        assert result["name"] == "Safari"
        assert result["bundle_id"] == "com.apple.Safari"

    def test_app_current_fallback(self, adapter_with_driver):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = adapter_with_driver.app_current()
        # Falls back to _frontmost_info which uses driver capabilities
        assert "bundle_id" in result

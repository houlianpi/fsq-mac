# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Backend Adapter: Appium Mac2.

Wraps Appium WebDriver for macOS automation.  All Appium-specific logic lives
here so the upper layers stay driver-agnostic.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from typing import Any

from appium import webdriver
from appium.options.mac import Mac2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from fsq_mac.models import ElementInfo, ErrorCode, LocatorQuery

logger = logging.getLogger("mac-cli.adapter")


# ---------------------------------------------------------------------------
# AppleScript safety
# ---------------------------------------------------------------------------

def _safe_applescript_str(value: str) -> str:
    """Escape a string for safe use inside AppleScript double-quoted strings.

    Rejects characters that could break out of the string context.
    """
    if '"' in value or '\\' in value:
        raise ValueError(f"Unsafe characters in AppleScript string: {value!r}")
    return value

# ---------------------------------------------------------------------------
# Locator strategy mapping
# ---------------------------------------------------------------------------

_STRATEGY_MAP = {
    "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
    "name": AppiumBy.NAME,
    "id": AppiumBy.ID,
    "class_name": AppiumBy.CLASS_NAME,
    "xpath": AppiumBy.XPATH,
    "ios_predicate": AppiumBy.IOS_PREDICATE,
    "": AppiumBy.ACCESSIBILITY_ID,
}


def _resolve_locator(strategy: str, value: str):
    by = _STRATEGY_MAP.get(strategy.lower().strip(), AppiumBy.ACCESSIBILITY_ID)
    return (by, value)


def _quote_xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    quoted = []
    for i, part in enumerate(parts):
        if part:
            quoted.append(f"'{part}'")
        if i != len(parts) - 1:
            quoted.append('"\'"')
    return "concat(" + ", ".join(quoted) + ")"


def _query_xpath(query: LocatorQuery) -> str:
    conditions: list[str] = []
    if query.role:
        role = query.role.replace("AX", "", 1) if query.role.startswith("AX") else query.role
        conditions.append(f"self::XCUIElementType{role}")
    if query.name:
        quoted = _quote_xpath_literal(query.name)
        conditions.append(f"(@name={quoted} or @title={quoted} or @value={quoted})")
    if query.label:
        quoted = _quote_xpath_literal(query.label)
        conditions.append(f"@label={quoted}")
    if not conditions:
        return "//*"
    return "//*[(" + ") and (".join(conditions) + ")]"


# ---------------------------------------------------------------------------
# Page source helpers
# ---------------------------------------------------------------------------

def _is_visible(attrib: dict) -> bool:
    if attrib.get("visible") == "false":
        return False
    if attrib.get("displayed") == "false":
        return False
    if attrib.get("width") == "0" or attrib.get("height") == "0":
        return False
    return True


def _parse_frame(attrib: dict) -> dict[str, int] | None:
    try:
        x = int(attrib.get("x", 0))
        y = int(attrib.get("y", 0))
        w = int(attrib.get("width", 0))
        h = int(attrib.get("height", 0))
        return {"x": x, "y": y, "width": w, "height": h}
    except (ValueError, TypeError):
        return None


def _geometry_payload(frame: tuple[int, int, int, int]) -> dict[str, dict[str, int]]:
    x, y, width, height = frame
    return {
        "element_bounds": {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        },
        "center": {
            "x": x + width // 2,
            "y": y + height // 2,
        },
    }


def _frame_to_tuple(frame: dict[str, int] | None) -> tuple[int, int, int, int] | None:
    if not frame:
        return None
    try:
        return (
            int(frame.get("x", 0)),
            int(frame.get("y", 0)),
            int(frame.get("width", 0)),
            int(frame.get("height", 0)),
        )
    except (TypeError, ValueError):
        return None


def parse_ui_tree(page_source: str, max_elements: int = 200) -> list[ElementInfo]:
    """Parse Appium XML page source into a list of ElementInfo."""
    elements: list[ElementInfo] = []
    try:
        root = ET.fromstring(page_source)
    except ET.ParseError:
        return elements

    idx = 0
    doc_idx = -1
    skipped_tags: dict[str, int] = {}  # track skipped root/hierarchy tags
    skipped_invisible = 0
    skipped_unnamed_group = 0
    total_xml_nodes = 0
    is_first = True
    for elem in root.iter():
        total_xml_nodes += 1
        # Always skip the root element: XPath "//*" used for ref binding
        # returns all descendants but excludes the root, so we must exclude
        # it here to keep doc_order_index aligned with XPath results.
        if is_first:
            is_first = False
            skipped_tags[elem.tag] = skipped_tags.get(elem.tag, 0) + 1
            continue
        if elem.tag in ("AppiumAUT", "hierarchy"):
            skipped_tags[elem.tag] = skipped_tags.get(elem.tag, 0) + 1
            continue
        doc_idx += 1

        if not _is_visible(elem.attrib):
            skipped_invisible += 1
            continue

        role = elem.tag.replace("XCUIElementType", "")
        name = elem.attrib.get("name") or elem.attrib.get("label") or ""
        label = elem.attrib.get("label") or ""
        value = elem.attrib.get("value")
        enabled = elem.attrib.get("enabled", "true") == "true"
        focused = elem.attrib.get("focused", "false") == "true"

        # Skip elements without meaningful info
        if not name and not label and not value and role in ("Other", "Group"):
            skipped_unnamed_group += 1
            continue

        eid = f"e{idx}"
        hint = f"accessibility_id:{name}" if name else None

        elements.append(ElementInfo(
            element_id=eid,
            role=role,
            name=name or None,
            label=label or None,
            value=value,
            enabled=enabled,
            visible=True,
            focused=focused,
            frame=_parse_frame(elem.attrib),
            locator_hint=hint,
            doc_order_index=doc_idx,
        ))
        idx += 1
        if idx >= max_elements:
            break

    logger.debug(
        "parse_ui_tree: %d XML nodes total, %d elements returned, "
        "skipped_tags=%s, skipped_invisible=%d, skipped_unnamed_group=%d, "
        "max_doc_idx=%d",
        total_xml_nodes, len(elements), skipped_tags,
        skipped_invisible, skipped_unnamed_group, doc_idx,
    )
    return elements


def simplify_page_source(page_source: str, max_size: int = 200000) -> str:
    """Simplify page source if too large — keeps visible elements only."""
    if len(page_source) <= max_size:
        return page_source

    try:
        root = ET.fromstring(page_source)

        # Filter invisible
        def _filter(el):
            children = [c for c in (el if el.tag == "hierarchy" else el) if True]
            keep = []
            for child in list(el):
                if _is_visible(child.attrib) or child.tag == "hierarchy":
                    filtered = _filter(child)
                    if filtered is not None:
                        keep.append(filtered)
                el.remove(child)
            for k in keep:
                el.append(k)
            if el.tag == "hierarchy" or _is_visible(el.attrib) or len(el):
                return el
            return None

        _filter(root)
        result = ET.tostring(root, encoding="unicode")
        if len(result) <= max_size:
            return result

        # Truncate long attributes
        for elem in root.iter():
            for attr in ("text", "content-desc", "value"):
                v = elem.attrib.get(attr, "")
                if len(v) > 100:
                    elem.attrib[attr] = v[:97] + "..."
        result = ET.tostring(root, encoding="unicode")
        return result[:max_size]

    except ET.ParseError:
        return page_source[:max_size]


# ---------------------------------------------------------------------------
# Menu bar filtering (ported from mac_driver_tool.py)
# ---------------------------------------------------------------------------

def _is_menu_bar_element(element, driver) -> bool:
    try:
        tag = getattr(element, "tag_name", "")
        hittable = element.get_attribute("hittable") or ""
        loc = element.location
        size = element.size
        w, h = size.get("width", 0), size.get("height", 0)
        y = loc.get("y", 0)

        if tag.endswith(":") and (w == 0 and h == 0 or hittable == "false"):
            return True
        if w == 0 and h == 0 and hittable == "false":
            return True
        if y < 50 and w > 50:
            etype = (element.get_attribute("elementType") or "").lower()
            if any(m in etype for m in ("menubar", "menubaritem", "menu", "menuitem")):
                return True
        return False
    except Exception:
        try:
            return element.location.get("y", 0) < 35
        except Exception:
            return False


def _select_best_element(driver, locator, strategy: str, value: str):
    try:
        elements = driver.find_elements(*locator)
        if len(elements) > 1:
            for e in elements:
                if not _is_menu_bar_element(e, driver):
                    return e
            return elements[0] if elements else None
        elif len(elements) == 1:
            return elements[0]
        else:
            return WebDriverWait(driver, 5).until(EC.presence_of_element_located(locator))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Adapter class
# ---------------------------------------------------------------------------

class AppiumMac2Adapter:
    """Backend adapter that talks to Appium Mac2 driver."""

    def __init__(self, config: dict):
        self._config = config
        self._server_url: str = config.get("server_url", "http://127.0.0.1:4723")
        self._driver = None
        # Snapshot: maps element_id -> WebElement for the current UI context
        self._element_refs: dict[str, Any] = {}
        self._snapshot_generation: int = 0
        # Configurable delays
        self._delay_post_action: float = config.get("delay_post_action", 0)
        self._delay_pre_input: float = config.get("delay_pre_input", 0)
        self._delay_double_click_gap: float = config.get("delay_double_click_gap", 0)
        # Command timeout — caps any single driver call (find, click, etc.)
        self._command_timeout: float = config.get("command_timeout", 15.0)
        # Tree cache
        self._tree_cache: str | None = None
        self._tree_cache_time: float = 0.0
        self._tree_ttl: float = config.get("tree_cache_ttl", 2.0)

    def _run_with_timeout(self, fn, timeout: float | None = None):
        """Run *fn* in a thread; raise TimeoutError if it exceeds *timeout*."""
        timeout = timeout or self._command_timeout
        result_box: list = []
        error_box: list = []

        def _target():
            try:
                result_box.append(fn())
            except Exception as exc:
                error_box.append(exc)

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            raise TimeoutError(
                f"Driver operation timed out after {timeout}s"
            )
        if error_box:
            raise error_box[0]
        return result_box[0] if result_box else None

    def _configure_driver_timeouts(self) -> None:
        """Set Selenium implicit wait on the current driver."""
        if self._driver:
            self._driver.implicitly_wait(self._command_timeout)

    def _poll_until(self, predicate, timeout: float, interval: float = 0.2):
        deadline = time.monotonic() + timeout
        while True:
            result = predicate()
            if result:
                return result
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            time.sleep(min(interval, remaining))

    def _get_page_source(self, force_refresh: bool = False) -> str:
        """Return page source, using cache if within TTL."""
        if self._driver is None:
            raise RuntimeError(
                "No active driver connection. Launch an app first with "
                "'mac app launch <bundle_id>'."
            )
        now = time.monotonic()
        if (not force_refresh
                and self._tree_cache is not None
                and self._tree_ttl > 0
                and (now - self._tree_cache_time) < self._tree_ttl):
            return self._tree_cache
        try:
            self._tree_cache = self._run_with_timeout(
                lambda: self._driver.page_source
            )
        except TimeoutError as exc:
            raise RuntimeError(
                f"Timed out retrieving page source after {self._command_timeout}s"
            ) from exc
        self._tree_cache_time = time.monotonic()
        return self._tree_cache

    def _frontmost_app_snapshot(self) -> dict | None:
        _SEP = "\x1f"
        try:
            script = ('tell application "System Events"\n'
                      '  set fp to first application process whose frontmost is true\n'
                      '  set appName to name of fp\n'
                      '  set appBid to bundle identifier of fp\n'
                      '  return appName & ASCII character 31 & appBid\n'
                      'end tell')
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if result.returncode == 0 and _SEP in result.stdout.strip():
                parts = result.stdout.strip().split(_SEP, 1)
                return {"name": parts[0], "bundle_id": parts[1]}
        except Exception:
            pass
        return None

    def _frontmost_window_snapshot(self) -> dict | None:
        _SEP = "\x1f"
        try:
            script = ('tell application "System Events"\n'
                      '  set fp to first application process whose frontmost is true\n'
                      '  set appName to name of fp\n'
                      '  set appBid to bundle identifier of fp\n'
                      '  set fw to front window of fp\n'
                      '  set winName to name of fw\n'
                      '  set winPos to position of fw\n'
                      '  set winSz to size of fw\n'
                      '  set sep to ASCII character 31\n'
                      '  return appName & sep & appBid & sep & winName & sep & (item 1 of winPos) & sep & (item 2 of winPos) & sep & (item 1 of winSz) & sep & (item 2 of winSz)\n'
                      'end tell')
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if result.returncode == 0 and _SEP in result.stdout.strip():
                parts = result.stdout.strip().split(_SEP)
                if len(parts) >= 7:
                    return {
                        "app_name": parts[0],
                        "app_bundle_id": parts[1],
                        "title": parts[2],
                        "x": int(parts[3]),
                        "y": int(parts[4]),
                        "width": int(parts[5]),
                        "height": int(parts[6]),
                    }
        except Exception:
            pass
        return None

    def _app_process_snapshot(self, bundle_id: str) -> dict | None:
        try:
            safe_bid = _safe_applescript_str(bundle_id)
            result = subprocess.run(
                ["osascript", "-e",
                 f'tell application "System Events" to get bundle identifier of every application process whose bundle identifier is "{safe_bid}"'],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if result.returncode == 0 and bundle_id in result.stdout:
                return {"bundle_ids": [bundle_id]}
        except Exception:
            pass
        return None

    def _managed_window_snapshot(self, bundle_id: str) -> dict | None:
        try:
            safe_bid = _safe_applescript_str(bundle_id)
            script = ('tell application "System Events"\n'
                      f'  set ap to first application process whose bundle identifier is "{safe_bid}"\n'
                      '  get name of every window of ap\n'
                      'end tell')
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if result.returncode == 0:
                titles = [n.strip() for n in result.stdout.strip().split(", ") if n.strip()]
                return {"titles": titles}
        except Exception:
            pass
        return None

    def _wait_for_frontmost_app(self, bundle_id: str, timeout: float = 5):
        return self._poll_until(
            lambda: (snapshot if (snapshot := self._frontmost_app_snapshot()) and snapshot.get("bundle_id") == bundle_id else None),
            timeout=timeout,
        )

    def _wait_for_frontmost_window(self, bundle_id: str, title: str, timeout: float = 5):
        title_lower = title.lower()
        return self._poll_until(
            lambda: (snapshot if (snapshot := self._frontmost_window_snapshot()) and snapshot.get("app_bundle_id") == bundle_id and title_lower in snapshot.get("title", "").lower() else None),
            timeout=timeout,
        )

    def _probe_actionable_state(self, element) -> tuple[tuple[int, int, int, int], bool, bool]:
        frame = self._element_frame(element)

        visible = True
        try:
            if hasattr(element, "is_displayed") and not element.is_displayed():
                visible = False
        except Exception:
            pass
        try:
            if element.get_attribute("visible") == "false":
                visible = False
        except Exception:
            pass
        try:
            if element.get_attribute("displayed") == "false":
                visible = False
        except Exception:
            pass

        _, _, width, height = frame
        visible = visible and width > 0 and height > 0

        enabled = True
        try:
            enabled = (element.get_attribute("enabled") or "true") != "false"
        except Exception:
            pass

        return frame, visible, enabled

    def _focused_geometry_payload(self) -> dict:
        try:
            page_source = self._get_page_source(force_refresh=True)
            self._tree_cache = None
            self._tree_cache_ts = 0.0
            elements = parse_ui_tree(page_source, max_elements=200)
        except Exception:
            return {}
        for element in elements:
            if not element.focused:
                continue
            frame = _frame_to_tuple(element.frame)
            if frame is None:
                continue
            return _geometry_payload(frame)
        return {}

    def _get_clipboard_text(self) -> str:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
        return result.stdout

    def _set_clipboard_text(self, text: str) -> None:
        subprocess.run(["pbcopy"], input=text, text=True, check=True)

    def _paste_via_hotkey(self) -> None:
        hotkey_result = self.input_hotkey("command+v")
        if hotkey_result.get("error_code"):
            raise RuntimeError(hotkey_result.get("detail") or "Paste hotkey failed")

    def _input_text_via_paste(self, text: str) -> None:
        clipboard_before = self._get_clipboard_text()
        restore_error: Exception | None = None
        try:
            self._set_clipboard_text(text)
            self._paste_via_hotkey()
        finally:
            try:
                self._set_clipboard_text(clipboard_before)
            except Exception as exc:
                restore_error = exc
        if restore_error:
            logger.warning("Failed to restore clipboard after paste input: %s", restore_error)

    # -- lifecycle ----------------------------------------------------------

    def connect(self, bundle_id: str | None = None) -> None:
        caps = dict(self._config)
        caps.pop("server_url", None)
        if bundle_id:
            caps["bundleId"] = bundle_id
        options = Mac2Options().load_capabilities(caps)
        self._driver = webdriver.Remote(self._server_url, options=options)
        self._configure_driver_timeouts()

    @property
    def connected(self) -> bool:
        if not self._driver:
            return False
        try:
            self._driver.get_window_size()
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        if not self._driver:
            return
        try:
            quit_thread = threading.Thread(target=self._driver.quit)
            quit_thread.start()
            quit_thread.join(timeout=5)
            if quit_thread.is_alive():
                self._force_kill_app()
        except Exception as exc:
            logger.warning("Error during disconnect: %s", exc)
        finally:
            self._driver = None
            self._invalidate_refs()

    def _force_kill_app(self) -> None:
        bid = self._config.get("bundleId", "")
        if not bid:
            return
        try:
            safe_bid = _safe_applescript_str(bid)
            cmd = [
                "osascript", "-e",
                f'tell application "System Events" to unix id of processes whose bundle identifier is "{safe_bid}"',
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                for pid in result.stdout.strip().split(","):
                    pid = pid.strip()
                    if pid.isdigit():
                        subprocess.run(["kill", "-9", pid], check=False)
        except Exception as exc:
            logger.warning("Force kill failed: %s", exc)

    # -- element refs -------------------------------------------------------

    def _invalidate_refs(self) -> None:
        self._snapshot_generation += 1

    def _store_ref(self, eid: str, web_element, name: str | None = None,
                   frame: dict | None = None, visible: bool = True,
                   enabled: bool = True, role: str | None = None) -> None:
        self._element_refs[eid] = (self._snapshot_generation, web_element, name,
                                   frame, visible, enabled, role)

    def _get_ref(self, eid: str):
        """Return (element, error_code) for a stored ref.

        On stale ref, returns (None, ELEMENT_REFERENCE_STALE).
        Callers can access stored_name via _get_ref_name() for fallback.
        """
        entry = self._element_refs.get(eid)
        if entry is None:
            return None, ErrorCode.ELEMENT_NOT_FOUND
        # Support (gen, el), (gen, el, name), (gen, el, name, frame, vis, en[, role])
        gen, web_el = entry[0], entry[1]
        if gen != self._snapshot_generation:
            return None, ErrorCode.ELEMENT_REFERENCE_STALE
        # Quick liveness check
        try:
            web_el.location
            return web_el, None
        except Exception:
            return None, ErrorCode.ELEMENT_REFERENCE_STALE

    def _get_ref_name(self, eid: str) -> str | None:
        """Return the stored accessibility name for a ref (for stale fallback)."""
        entry = self._element_refs.get(eid)
        if entry is None or len(entry) < 3:
            return None
        return entry[2]  # (gen, web_el, name, ...)

    def _get_ref_role(self, eid: str) -> str | None:
        """Return the stored role for a ref (for stale fallback)."""
        entry = self._element_refs.get(eid)
        if entry is None or len(entry) < 7:
            return None
        return entry[6]  # (gen, web_el, name, frame, vis, en, role)

    def _get_ref_cached_state(self, eid: str) -> tuple[dict | None, bool, bool] | None:
        """Return cached (frame, visible, enabled) from inspect-time XML data.

        Returns None if no cached state is available (e.g., element found via
        locator query rather than inspect).
        """
        entry = self._element_refs.get(eid)
        if entry is None or len(entry) < 6:
            return None
        _gen, _el, _name, frame, visible, enabled = entry[:6]
        if frame is None:
            return None
        return frame, visible, enabled

    def _stale_ref_error(self, ref: str) -> dict:
        """Build a rich stale-ref error dict with cached identity."""
        cached_name = self._get_ref_name(ref)
        cached_role = self._get_ref_role(ref)
        detail = f"Ref '{ref}' is stale; UI changed since the last inspect"
        if cached_name and cached_role:
            detail = f"Ref '{ref}' ({cached_name}, {cached_role}) is stale; UI changed since the last inspect"
        elif cached_name:
            detail = f"Ref '{ref}' ({cached_name}) is stale; UI changed since the last inspect"
        return {
            "error_code": ErrorCode.ELEMENT_REFERENCE_STALE,
            "detail": detail,
            "details": {
                "ref": ref,
                "cached_name": cached_name,
                "cached_role": cached_role,
                "reason": "generation_mismatch",
            },
        }

    # -- resolve ref: element_id or locator ---------------------------------

    def _coerce_query(self, ref: str | LocatorQuery) -> LocatorQuery:
        if isinstance(ref, LocatorQuery):
            return ref
        return LocatorQuery(ref=ref)

    def _element_role(self, element) -> str:
        try:
            role = element.get_attribute("role") or ""
            if role:
                return role
        except Exception:
            pass
        try:
            return getattr(element, "tag_name", "").replace("XCUIElementType", "")
        except Exception:
            return ""

    def _element_name(self, element) -> str:
        for attr in ("name", "title", "value"):
            try:
                value = element.get_attribute(attr) or ""
                if value:
                    return value
            except Exception:
                pass
        try:
            return element.text or ""
        except Exception:
            return ""

    def _element_label(self, element) -> str:
        try:
            return element.get_attribute("label") or ""
        except Exception:
            return ""

    def _matches_query(self, element, query: LocatorQuery) -> bool:
        if query.role and self._element_role(element) != query.role:
            return False
        if query.name and self._element_name(element) != query.name:
            return False
        if query.label and self._element_label(element) != query.label:
            return False
        return True

    def _resolve_query(self, query: LocatorQuery, strategy: str = "accessibility_id", timeout: int = 5):
        if query.ref:
            return self._resolve_ref(query.ref, strategy, timeout)
        if query.id:
            locator = _resolve_locator("id", query.id)
            el = _select_best_element(self._driver, locator, "id", query.id)
            return (el, None) if el is not None else (None, ErrorCode.ELEMENT_NOT_FOUND)
        if query.role or query.name or query.label:
            locator = _resolve_locator("xpath", _query_xpath(query))
            try:
                def _find_by_query():
                    return self._driver.find_elements(*locator)
                matches = self._run_with_timeout(_find_by_query)
            except TimeoutError:
                return None, ErrorCode.TIMEOUT
            except Exception:
                matches = []
            if not matches:
                return None, ErrorCode.ELEMENT_NOT_FOUND
            if len(matches) > 1:
                return None, ErrorCode.ELEMENT_AMBIGUOUS
            return matches[0], None
        if query.xpath:
            locator = _resolve_locator("xpath", query.xpath)
            el = _select_best_element(self._driver, locator, "xpath", query.xpath)
            return (el, None) if el is not None else (None, ErrorCode.ELEMENT_NOT_FOUND)
        return None, ErrorCode.INVALID_ARGUMENT

    def _element_frame(self, element) -> tuple[int, int, int, int]:
        loc = element.location
        size = element.size
        return (
            int(loc.get("x", 0)),
            int(loc.get("y", 0)),
            int(size.get("width", 0)),
            int(size.get("height", 0)),
        )

    def _element_visible(self, element) -> bool:
        try:
            if hasattr(element, "is_displayed") and not element.is_displayed():
                return False
        except Exception:
            pass
        try:
            if element.get_attribute("visible") == "false":
                return False
        except Exception:
            pass
        try:
            if element.get_attribute("displayed") == "false":
                return False
        except Exception:
            pass
        _, _, width, height = self._element_frame(element)
        return width > 0 and height > 0

    def _element_enabled(self, element) -> bool:
        try:
            return (element.get_attribute("enabled") or "true") != "false"
        except Exception:
            return True

    def _ref_eid(self, ref: str | LocatorQuery) -> str | None:
        """Extract element id string from a ref or LocatorQuery."""
        if isinstance(ref, str):
            return ref
        if isinstance(ref, LocatorQuery):
            return ref.ref
        return None

    def _wait_for_actionable(self, element, timeout: int = 5,
                              cached_state: tuple[dict, bool, bool] | None = None) -> dict | None:
        # Fast path: use cached state from inspect-time XML parse.
        # The XML data was fetched alongside the WebElement refs, so it's
        # as fresh as the refs themselves — no need for live RPC probes.
        if cached_state is not None:
            frame_dict, visible, enabled = cached_state
            if visible and enabled and frame_dict:
                logger.debug("_wait_for_actionable: using cached XML state (visible=%s, enabled=%s)", visible, enabled)
                return None
            # Cached state says not actionable — report immediately
            checks = {"visible": visible, "enabled": enabled}
            waiting_on = [name for name, ok in checks.items() if not ok]
            return {
                "error_code": ErrorCode.TIMEOUT,
                "detail": f"Element not actionable (from cached state); waiting on {', '.join(waiting_on)}",
            }

        # Slow path: live probe via Appium RPC (for elements without cached state)
        deadline = time.monotonic() + timeout
        last_frame = None
        waiting_on = ["visible", "enabled", "stable"]
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {
                    "error_code": ErrorCode.TIMEOUT,
                    "detail": f"Element did not become actionable; waiting on {', '.join(waiting_on)}",
                }
            try:
                frame, visible, enabled = self._run_with_timeout(
                    lambda: self._probe_actionable_state(element),
                    timeout=remaining,
                )
            except TimeoutError as exc:
                return {
                    "error_code": ErrorCode.TIMEOUT,
                    "detail": f"Timed out while probing element state: {exc}",
                }
            except Exception as exc:
                return {
                    "error_code": ErrorCode.ELEMENT_REFERENCE_STALE,
                    "detail": str(exc),
                }
            checks = {
                "visible": visible,
                "enabled": enabled,
                "stable": last_frame is not None and frame == last_frame,
            }
            if all(checks.values()):
                return None
            waiting_on = [name for name, ok in checks.items() if not ok]
            last_frame = frame
            time.sleep(0.1)

    def _resolve_ref(self, ref: str | LocatorQuery, strategy: str = "accessibility_id", timeout: int = 5):
        """Resolve a ref to a WebElement.

        Returns (element, error_code|None).
        """
        if isinstance(ref, LocatorQuery):
            return self._resolve_query(ref, strategy, timeout)
        # Try element_id first
        if ref.startswith("e") and ref[1:].isdigit():
            el, err = self._get_ref(ref)
            if el is not None:
                return el, None
            # Stale ref — try to re-find by stored accessibility name
            if err == ErrorCode.ELEMENT_REFERENCE_STALE:
                stored_name = self._get_ref_name(ref)
                if stored_name:
                    logger.debug(
                        "resolve_ref: %s is stale, re-finding by accessibility_id '%s'",
                        ref, stored_name,
                    )
                    locator = _resolve_locator("accessibility_id", stored_name)
                    el = _select_best_element(self._driver, locator, "accessibility_id", stored_name)
                    if el is not None:
                        return el, None
                    logger.debug("resolve_ref: re-find by name '%s' failed", stored_name)
                return None, err

        # Locator-based resolution
        locator = _resolve_locator(strategy, ref)
        el = _select_best_element(self._driver, locator, strategy, ref)
        if el is None:
            return None, ErrorCode.ELEMENT_NOT_FOUND
        return el, None

    # -- app operations -----------------------------------------------------

    def app_launch(self, bundle_id: str, arguments: list | None = None) -> dict:
        try:
            if self._driver and self.connected:
                self.disconnect()
            cfg = dict(self._config)
            cfg["bundleId"] = bundle_id
            if arguments:
                cfg["arguments"] = arguments
            cfg.pop("server_url", None)
            options = Mac2Options().load_capabilities(cfg)
            self._driver = webdriver.Remote(self._server_url, options=options)
            self._configure_driver_timeouts()
            self._invalidate_refs()
            self._tree_cache = None
            info = self._wait_for_frontmost_app(bundle_id, timeout=5)
            if info is None:
                return {"error_code": ErrorCode.TIMEOUT, "detail": f"Timed out waiting for app {bundle_id!r} to become frontmost"}
            return info
        except Exception as exc:
            return {"error_code": ErrorCode.BACKEND_UNAVAILABLE, "detail": str(exc)}

    def app_activate(self, bundle_id: str) -> dict:
        if not self._driver or not self.connected:
            return {"error_code": ErrorCode.BACKEND_UNAVAILABLE, "detail": "No active session"}
        try:
            self._driver.activate_app(bundle_id)
        except Exception:
            # Mac2 driver may not support activate_app — fall back to AppleScript
            try:
                safe_bid = _safe_applescript_str(bundle_id)
            except ValueError:
                return {"error_code": ErrorCode.INVALID_ARGUMENT, "detail": f"Unsafe bundle ID: {bundle_id!r}"}
            subprocess.run(
                ["osascript", "-e",
                 f'tell application id "{safe_bid}" to activate'],
                capture_output=True, text=True, timeout=10, check=False,
            )
        self._invalidate_refs()
        time.sleep(self._delay_post_action)
        info = self._wait_for_frontmost_app(bundle_id, timeout=5)
        if info is None:
            return {"error_code": ErrorCode.TIMEOUT, "detail": f"Timed out waiting for app {bundle_id!r} to become frontmost"}
        self._tree_cache = None
        return info

    def app_terminate(self, bundle_id: str) -> dict:
        if not self._driver or not self.connected:
            return {"error_code": ErrorCode.BACKEND_UNAVAILABLE, "detail": "No active session"}
        try:
            self._driver.terminate_app(bundle_id)
        except Exception:
            # Mac2 driver may not support terminate_app — fall back to AppleScript
            try:
                safe_bid = _safe_applescript_str(bundle_id)
            except ValueError:
                return {"error_code": ErrorCode.INVALID_ARGUMENT, "detail": f"Unsafe bundle ID: {bundle_id!r}"}
            subprocess.run(
                ["osascript", "-e",
                 f'tell application id "{safe_bid}" to quit'],
                capture_output=True, text=True, timeout=10, check=False,
            )
        self._invalidate_refs()
        self._tree_cache = None
        return {"terminated": bundle_id}

    def app_current(self) -> dict:
        """Return the actual macOS frontmost application."""
        snapshot = self._frontmost_app_snapshot()
        if snapshot:
            return snapshot
        return self._frontmost_info()

    def app_list(self) -> list[dict]:
        """List visible applications using AppleScript."""
        try:
            # Use newline-delimited output to avoid comma-in-name ambiguity
            script = ('tell application "System Events"\n'
                      '  set procs to every application process whose background only is false\n'
                      '  set out to ""\n'
                      '  set sep to ASCII character 31\n'
                      '  repeat with p in procs\n'
                      '    set out to out & name of p & sep & bundle identifier of p & "\n"\n'
                      '  end repeat\n'
                      '  return out\n'
                      'end tell')
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if result.returncode != 0:
                return []
            apps = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if "\x1f" not in line:
                    continue
                name, bid = line.split("\x1f", 1)
                if bid and bid != "missing value":
                    apps.append({"name": name, "bundle_id": bid})
            return apps
        except Exception:
            return []

    def _managed_bundle_id(self) -> str:
        """Return the bundle ID of the app managed by this Appium session."""
        if not self._driver:
            return ""
        caps = self._driver.capabilities
        return caps.get("bundleId") or caps.get("appium:bundleId") or self._config.get("bundleId", "")

    def _frontmost_info(self) -> dict:
        try:
            bid = self._managed_bundle_id()
            info = {"bundle_id": bid}
            # Enrich with app name via AppleScript using bundle ID (#7)
            try:
                safe_bid = _safe_applescript_str(bid)
                result = subprocess.run(
                    ["osascript", "-e",
                     f'tell application "System Events" to get name of first application process whose bundle identifier is "{safe_bid}"'],
                    capture_output=True, text=True, timeout=5, check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    info["name"] = result.stdout.strip()
            except Exception:
                pass
            return info
        except Exception:
            return {"bundle_id": "unknown"}

    # -- element operations -------------------------------------------------

    def inspect(self, max_elements: int = 200) -> list[dict]:
        self._invalidate_refs()
        source = self._get_page_source()
        elements = parse_ui_tree(source, max_elements=max_elements)
        # Bind refs by document-order index
        try:
            all_web_els = self._run_with_timeout(
                lambda: self._driver.find_elements(AppiumBy.XPATH, "//*")
            )
            logger.debug(
                "inspect ref-binding: %d parsed elements, %d XPath elements",
                len(elements), len(all_web_els),
            )
            for info in elements:
                if 0 <= info.doc_order_index < len(all_web_els):
                    wel = all_web_els[info.doc_order_index]
                    self._store_ref(info.element_id, wel, name=info.name,
                                    frame=info.frame, visible=info.visible,
                                    enabled=info.enabled, role=info.role)
                    info.ref_bound = True
                else:
                    info.ref_bound = False
                    logger.debug(
                        "inspect ref-binding: %s doc_order_index=%d out of range (max=%d)",
                        info.element_id, info.doc_order_index, len(all_web_els),
                    )
        except TimeoutError:
            logger.warning("Timed out binding inspect element refs; returning parsed tree without refs")
            for info in elements:
                info.ref_bound = False
        except Exception:
            for info in elements:
                info.ref_bound = False
        return [e.to_dict() for e in elements]

    def find(self, value: str, strategy: str = "accessibility_id", timeout: int = 5) -> tuple[str, list[dict]]:
        """Returns (match_status, elements)."""
        locator = _resolve_locator(strategy, value)
        try:
            WebDriverWait(self._driver, timeout).until(EC.presence_of_element_located(locator))
        except Exception:
            return "no_match", []

        web_els = self._driver.find_elements(*locator)
        if not web_els:
            return "no_match", []

        self._snapshot_generation += 1
        result = []
        for i, wel in enumerate(web_els):
            eid = f"e{i}"
            el_name = ""
            el_label = ""
            try:
                el_name = wel.get_attribute("name") or ""
                el_label = wel.get_attribute("label") or ""
            except Exception:
                pass
            self._store_ref(eid, wel, name=el_name or None)
            result.append(ElementInfo(
                element_id=eid,
                role=getattr(wel, "tag_name", "").replace("XCUIElementType", ""),
                name=el_name or None,
                label=el_label or None,
                enabled=True,
                frame=None,
                locator_hint=f"{strategy}:{value}",
            ).to_dict())

        status = "exactly_one_match" if len(result) == 1 else "multiple_matches"
        return status, result

    def click(self, ref: str | LocatorQuery, strategy: str = "accessibility_id", timeout: int = 5) -> dict:
        el, err = self._resolve_ref(ref, strategy, timeout)
        if err:
            eid = self._ref_eid(ref)
            if err == ErrorCode.ELEMENT_REFERENCE_STALE and eid:
                return self._stale_ref_error(eid)
            return {"error_code": err}
        # Look up cached XML state for element refs (e0, e1, ...)
        eid = ref if isinstance(ref, str) else (ref.ref if isinstance(ref, LocatorQuery) else None)
        cached_state = self._get_ref_cached_state(eid) if eid else None
        wait_error = self._wait_for_actionable(el, timeout, cached_state=cached_state)
        if wait_error:
            logger.debug(
                "click: _wait_for_actionable failed for ref=%s: %s", ref, wait_error,
            )
            return wait_error
        # Use cached frame from XML if available, otherwise query live
        if cached_state is not None:
            fallback_frame = _frame_to_tuple(cached_state[0]) or (0, 0, 0, 0)
        else:
            fallback_frame = self._element_frame(el)
        x, y, w, h = fallback_frame
        if h <= 1 or w <= 1:
            try:
                el_name = el.get_attribute("name") or ""
                el_tag = getattr(el, "tag_name", "").replace("XCUIElementType", "")
            except Exception:
                el_name, el_tag = "?", "?"
            logger.warning(
                "click: degenerate frame for ref=%s (%s/%s): "
                "x=%d y=%d w=%d h=%d — coordinate-based fallback will be unreliable",
                ref, el_tag, el_name, x, y, w, h,
            )
        try:
            self._run_with_timeout(
                lambda: ActionChains(self._driver).move_to_element(el).click().perform()
            )
        except TimeoutError as exc:
            driver_click_error = exc
        except Exception as exc:
            driver_click_error = exc
        else:
            time.sleep(self._delay_post_action)
            self._invalidate_refs()
            self._tree_cache = None
            return _geometry_payload(fallback_frame)

        try:
            self._run_with_timeout(lambda: el.click())
        except TimeoutError as exc:
            driver_click_error = exc
        except Exception as exc:
            driver_click_error = exc
        else:
            time.sleep(self._delay_post_action)
            self._invalidate_refs()
            self._tree_cache = None
            return _geometry_payload(fallback_frame)

        try:
            x, y, width, height = fallback_frame
            fallback = self.input_click_at(x + width / 2, y + height / 2)
            if fallback.get("error_code"):
                if isinstance(driver_click_error, TimeoutError):
                    return {"error_code": ErrorCode.TIMEOUT, "detail": str(driver_click_error)}
                detail = fallback.get("detail") or str(driver_click_error)
                return {"error_code": fallback["error_code"], "detail": detail}
        except Exception as exc:
            if isinstance(driver_click_error, TimeoutError):
                return {"error_code": ErrorCode.TIMEOUT, "detail": str(driver_click_error)}
            return {"error_code": ErrorCode.ELEMENT_NOT_FOUND, "detail": str(exc)}

        if isinstance(driver_click_error, TimeoutError):
            logger.warning("Driver click timed out; recovered via coordinate click fallback")
        else:
            logger.warning("Driver click failed; recovered via coordinate click fallback: %s", driver_click_error)

        time.sleep(self._delay_post_action)
        self._invalidate_refs()
        self._tree_cache = None
        return _geometry_payload(fallback_frame)

    def right_click(self, ref: str | LocatorQuery, strategy: str = "accessibility_id", timeout: int = 5) -> dict:
        el, err = self._resolve_ref(ref, strategy, timeout)
        if err:
            eid = self._ref_eid(ref)
            if err == ErrorCode.ELEMENT_REFERENCE_STALE and eid:
                return self._stale_ref_error(eid)
            return {"error_code": err}
        cached_state = self._get_ref_cached_state(self._ref_eid(ref))
        wait_error = self._wait_for_actionable(el, timeout, cached_state=cached_state)
        if wait_error:
            return wait_error
        frame = _frame_to_tuple(cached_state[0]) if cached_state else self._element_frame(el)
        try:
            self._run_with_timeout(
                lambda: ActionChains(self._driver).context_click(el).perform()
            )
        except TimeoutError as exc:
            return {"error_code": ErrorCode.TIMEOUT, "detail": str(exc)}
        except Exception as exc:
            return {"error_code": ErrorCode.ELEMENT_NOT_FOUND, "detail": str(exc)}
        time.sleep(self._delay_post_action)
        self._invalidate_refs()
        self._tree_cache = None
        return _geometry_payload(frame)

    def double_click(self, ref: str | LocatorQuery, strategy: str = "accessibility_id", timeout: int = 5) -> dict:
        el, err = self._resolve_ref(ref, strategy, timeout)
        if err:
            eid = self._ref_eid(ref)
            if err == ErrorCode.ELEMENT_REFERENCE_STALE and eid:
                return self._stale_ref_error(eid)
            return {"error_code": err}
        cached_state = self._get_ref_cached_state(self._ref_eid(ref))
        wait_error = self._wait_for_actionable(el, timeout, cached_state=cached_state)
        if wait_error:
            return wait_error
        frame = _frame_to_tuple(cached_state[0]) if cached_state else self._element_frame(el)
        try:
            def _do_double_click():
                loc = el.location
                sz = el.size
                x = loc["x"] + sz["width"] / 2
                y = loc["y"] + sz["height"] / 2
                self._driver.tap([(x, y)])
                time.sleep(self._delay_double_click_gap)
                self._driver.tap([(x, y)])
            self._run_with_timeout(_do_double_click)
        except TimeoutError as exc:
            return {"error_code": ErrorCode.TIMEOUT, "detail": str(exc)}
        except Exception as exc:
            return {"error_code": ErrorCode.ELEMENT_NOT_FOUND, "detail": str(exc)}
        time.sleep(self._delay_post_action)
        self._invalidate_refs()
        self._tree_cache = None
        return _geometry_payload(frame)

    def hover(self, ref: str | LocatorQuery, strategy: str = "accessibility_id", duration: float = 1.0) -> dict:
        el, err = self._resolve_ref(ref, strategy)
        if err:
            eid = self._ref_eid(ref)
            if err == ErrorCode.ELEMENT_REFERENCE_STALE and eid:
                return self._stale_ref_error(eid)
            return {"error_code": err}
        cached_state = self._get_ref_cached_state(self._ref_eid(ref))
        wait_error = self._wait_for_actionable(el, cached_state=cached_state)
        if wait_error:
            return wait_error
        frame = _frame_to_tuple(cached_state[0]) if cached_state else self._element_frame(el)
        try:
            self._run_with_timeout(
                lambda: ActionChains(self._driver).move_to_element(el).perform()
            )
            if duration > 0:
                time.sleep(duration)
        except TimeoutError as exc:
            return {"error_code": ErrorCode.TIMEOUT, "detail": str(exc)}
        except Exception as exc:
            return {"error_code": ErrorCode.ELEMENT_NOT_FOUND, "detail": str(exc)}
        return _geometry_payload(frame)

    def type_text(self, ref: str | LocatorQuery, text: str, strategy: str = "accessibility_id",
                  input_method: str = "paste") -> dict:
        el, err = self._resolve_ref(ref, strategy)
        if err:
            eid = self._ref_eid(ref)
            if err == ErrorCode.ELEMENT_REFERENCE_STALE and eid:
                return self._stale_ref_error(eid)
            return {"error_code": err}
        cached_state = self._get_ref_cached_state(self._ref_eid(ref))
        wait_error = self._wait_for_actionable(el, cached_state=cached_state)
        if wait_error:
            return wait_error
        frame = _frame_to_tuple(cached_state[0]) if cached_state else self._element_frame(el)
        try:
            def _do_type():
                el.click()
                el.clear()
                if input_method == "keys":
                    try:
                        el.send_keys(text)
                    except Exception:
                        self._driver.execute_script("macos: keys", {"keys": list(text)})
                else:
                    self._input_text_via_paste(text)
            self._run_with_timeout(_do_type)
        except TimeoutError as exc:
            return {"error_code": ErrorCode.TIMEOUT, "detail": str(exc)}
        except Exception as exc:
            return {"error_code": ErrorCode.ELEMENT_NOT_FOUND, "detail": str(exc)}
        # Verify the typed value
        result = {"expected": text, **_geometry_payload(frame)}
        try:
            actual = el.get_attribute("value")
            if actual is None:
                actual = el.text or ""
            result["typed_value"] = actual
            result["verified"] = (actual == text)
        except Exception:
            result["verified"] = None  # verification not possible
        self._invalidate_refs()
        self._tree_cache = None
        return result

    def scroll(self, ref: str | LocatorQuery, direction: str = "down", strategy: str = "accessibility_id") -> dict:
        el, err = self._resolve_ref(ref, strategy)
        if err:
            eid = self._ref_eid(ref)
            if err == ErrorCode.ELEMENT_REFERENCE_STALE and eid:
                return self._stale_ref_error(eid)
            return {"error_code": err}
        try:
            self._driver.execute_script("mobile: scroll", {"direction": direction, "element": el})
        except Exception as exc:
            return {"error_code": ErrorCode.ELEMENT_NOT_FOUND, "detail": str(exc)}
        self._invalidate_refs()
        self._tree_cache = None
        return {}

    def drag(self, source_ref: str | LocatorQuery, target_ref: str | LocatorQuery, strategy: str = "accessibility_id") -> dict:
        src, err1 = self._resolve_ref(source_ref, strategy)
        tgt, err2 = self._resolve_ref(target_ref, strategy)
        if err1:
            eid = self._ref_eid(source_ref)
            if err1 == ErrorCode.ELEMENT_REFERENCE_STALE and eid:
                return self._stale_ref_error(eid)
            return {"error_code": err1, "detail": f"source: {source_ref}"}
        if err2:
            eid = self._ref_eid(target_ref)
            if err2 == ErrorCode.ELEMENT_REFERENCE_STALE and eid:
                return self._stale_ref_error(eid)
            return {"error_code": err2, "detail": f"target: {target_ref}"}
        src_cached = self._get_ref_cached_state(self._ref_eid(source_ref))
        tgt_cached = self._get_ref_cached_state(self._ref_eid(target_ref))
        wait_error = self._wait_for_actionable(src, cached_state=src_cached)
        if wait_error:
            return wait_error
        wait_error = self._wait_for_actionable(tgt, cached_state=tgt_cached)
        if wait_error:
            return wait_error
        try:
            self._run_with_timeout(
                lambda: ActionChains(self._driver).drag_and_drop(src, tgt).perform()
            )
        except TimeoutError as exc:
            return {"error_code": ErrorCode.TIMEOUT, "detail": str(exc)}
        except Exception as exc:
            return {"error_code": ErrorCode.ELEMENT_NOT_FOUND, "detail": str(exc)}
        self._invalidate_refs()
        self._tree_cache = None
        return {}

    # -- input operations ---------------------------------------------------

    def input_key(self, key: str) -> dict:
        key_mapping = {
            "return": "\n", "enter": "\n", "space": " ", "tab": "\t",
            "escape": "\x1b", "backspace": "\x08", "delete": "\x7f",
            # Arrow keys (XCUITest key constants)
            "up": "\uF700", "down": "\uF701",
            "left": "\uF702", "right": "\uF703",
            # Navigation keys
            "home": "\uF729", "end": "\uF72B",
            "pageup": "\uF72C", "pagedown": "\uF72D",
            # Function keys
            "f1": "\uF704", "f2": "\uF705", "f3": "\uF706", "f4": "\uF707",
            "f5": "\uF708", "f6": "\uF709", "f7": "\uF70A", "f8": "\uF70B",
            "f9": "\uF70C", "f10": "\uF70D", "f11": "\uF70E", "f12": "\uF70F",
        }
        mapped = key_mapping.get(key.lower(), key)
        try:
            self._driver.execute_script("macos: keys", {"keys": [mapped]})
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}
        self._tree_cache = None
        return self._focused_geometry_payload()

    def input_hotkey(self, combo: str) -> dict:
        key_mapping = {
            "return": "\n", "enter": "\n", "space": " ", "tab": "\t",
            "escape": "\x1b", "backspace": "\x08", "delete": "\x7f",
            # Arrow keys (XCUITest key constants)
            "up": "\uF700", "down": "\uF701",
            "left": "\uF702", "right": "\uF703",
            # Navigation keys
            "home": "\uF729", "end": "\uF72B",
            "pageup": "\uF72C", "pagedown": "\uF72D",
            # Function keys
            "f1": "\uF704", "f2": "\uF705", "f3": "\uF706", "f4": "\uF707",
            "f5": "\uF708", "f6": "\uF709", "f7": "\uF70A", "f8": "\uF70B",
            "f9": "\uF70C", "f10": "\uF70D", "f11": "\uF70E", "f12": "\uF70F",
        }
        parts = combo.lower().split("+")
        modifiers = parts[:-1]
        actual = parts[-1]
        flags = 0
        for mod in modifiers:
            if mod in ("command", "cmd"):
                flags |= 1 << 4
            elif mod == "shift":
                flags |= 1 << 1
            elif mod in ("control", "ctrl"):
                flags |= 1 << 2
            elif mod in ("option", "alt"):
                flags |= 1 << 3
            elif mod in ("fn", "function"):
                flags |= 1 << 5
        mapped = key_mapping.get(actual, actual)
        try:
            time.sleep(self._delay_pre_input)
            self._driver.execute_script("macos: keys", {"keys": [{"key": mapped, "modifierFlags": flags}]})
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}
        self._tree_cache = None
        return self._focused_geometry_payload()

    def input_text(self, text: str, input_method: str = "paste") -> dict:
        try:
            time.sleep(self._delay_pre_input)
            if input_method == "keys":
                self._driver.execute_script("macos: keys", {"keys": list(text)})
            else:
                self._input_text_via_paste(text)
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}
        self._tree_cache = None
        return self._focused_geometry_payload()

    def input_click_at(self, x: int, y: int) -> dict:
        try:
            time.sleep(self._delay_pre_input)
            self._run_with_timeout(
                lambda: self._driver.execute_script(
                    "macos: click",
                    {"x": int(x), "y": int(y)},
                )
            )
        except TimeoutError as exc:
            return {"error_code": ErrorCode.TIMEOUT, "detail": str(exc)}
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}
        self._invalidate_refs()
        self._tree_cache = None
        return {}

    def _assert_compare(self, actual: str, expected: str, kind: str) -> dict:
        if actual == expected:
            return {}
        return {
            "error_code": ErrorCode.ASSERTION_FAILED,
            "detail": f"expected {kind} {expected!r} but got {actual!r}",
        }

    def assert_visible(self, query: LocatorQuery) -> dict:
        el, err = self._resolve_ref(query)
        if err:
            return {"error_code": err}
        if self._element_visible(el):
            return {}
        return {"error_code": ErrorCode.ASSERTION_FAILED, "detail": "element is not visible"}

    def assert_enabled(self, query: LocatorQuery) -> dict:
        el, err = self._resolve_ref(query)
        if err:
            return {"error_code": err}
        if self._element_enabled(el):
            return {}
        return {"error_code": ErrorCode.ASSERTION_FAILED, "detail": "element is not enabled"}

    def assert_text(self, query: LocatorQuery, expected: str) -> dict:
        el, err = self._resolve_ref(query)
        if err:
            return {"error_code": err}
        actual = getattr(el, "text", None)
        if actual is None:
            actual = self._element_name(el)
        return self._assert_compare(actual, expected, "text")

    def assert_value(self, query: LocatorQuery, expected: str) -> dict:
        el, err = self._resolve_ref(query)
        if err:
            return {"error_code": err}
        try:
            actual = el.get_attribute("value") or ""
        except Exception:
            actual = ""
        return self._assert_compare(actual, expected, "value")

    def menu_click(self, path: str) -> dict:
        parts = [part.strip() for part in path.split(">") if part.strip()]
        if not parts:
            return {"error_code": ErrorCode.INVALID_ARGUMENT, "detail": f"Invalid menu path: {path!r}"}
        bid = self._managed_bundle_id()
        if not bid:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": "Cannot determine managed bundle ID for menu click"}
        safe_bid = _safe_applescript_str(bid)
        quoted_parts = ", ".join(f'"{_safe_applescript_str(part)}"' for part in parts)
        script = (
            'on clickMenu(menuParts)\n'
            '  tell application "System Events"\n'
            f'    tell first application process whose bundle identifier is "{safe_bid}"\n'
            '      set currentMenuItem to menu bar item (item 1 of menuParts) of menu bar 1\n'
            '      click currentMenuItem\n'
            '      repeat with i from 2 to (count of menuParts)\n'
            '        set currentMenuItem to menu item (item i of menuParts) of menu 1 of currentMenuItem\n'
            '        click currentMenuItem\n'
            '      end repeat\n'
            '    end tell\n'
            '  end tell\n'
            'end clickMenu\n'
            f'clickMenu({{{quoted_parts}}})'
        )
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if result.returncode != 0:
                return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": result.stderr.strip() or "menu click failed"}
            self._invalidate_refs()
            self._tree_cache = None
            return {}
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}

    # -- capture ------------------------------------------------------------

    def screenshot(self, path: str) -> dict:
        try:
            png = self._driver.get_screenshot_as_png()
            with open(path, "wb") as f:
                f.write(png)
            return {"path": path, "size_bytes": len(png)}
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}

    def screenshot_element(self, ref: str, path: str, strategy: str = "accessibility_id") -> dict:
        el, err = self._resolve_ref(ref, strategy)
        if err:
            return {"error_code": err, "detail": f"Element '{ref}' not found"}
        try:
            png = el.screenshot_as_png
            with open(path, "wb") as f:
                f.write(png)
            return {"path": path, "size_bytes": len(png)}
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}

    def screenshot_rect(self, rect: str, path: str) -> dict:
        parts = rect.split(",")
        if len(parts) != 4:
            return {"error_code": ErrorCode.INVALID_ARGUMENT,
                    "detail": f"Expected x,y,w,h but got: {rect}"}
        try:
            x, y, w, h = [int(p.strip()) for p in parts]
        except ValueError:
            return {"error_code": ErrorCode.INVALID_ARGUMENT,
                    "detail": f"Non-integer values in rect: {rect}"}
        try:
            result = subprocess.run(
                ["screencapture", f"-R{x},{y},{w},{h}", path],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if result.returncode != 0:
                return {"error_code": ErrorCode.INTERNAL_ERROR,
                        "detail": f"screencapture failed: {result.stderr.strip()}"}
            size = os.path.getsize(path) if os.path.exists(path) else 0
            return {"path": path, "size_bytes": size}
        except Exception as exc:
            return {"error_code": ErrorCode.INTERNAL_ERROR, "detail": str(exc)}

    def ui_tree(self) -> str:
        source = self._get_page_source()
        return simplify_page_source(source)

    # -- window -------------------------------------------------------------

    def window_current(self) -> dict:
        """Return info about the actual frontmost window."""
        snapshot = self._frontmost_window_snapshot()
        if snapshot:
            return snapshot
        # Fallback: managed app window via driver
        try:
            size = self._driver.get_window_size()
            title = None
            bid = self._managed_bundle_id()
            try:
                safe_bid = _safe_applescript_str(bid)
                script = ('tell application "System Events"\n'
                          f'  set ap to first application process whose bundle identifier is "{safe_bid}"\n'
                          '  get name of first window of ap\n'
                          'end tell')
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True, text=True, timeout=5, check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    title = result.stdout.strip()
            except Exception:
                pass
            info = {"width": size.get("width", 0), "height": size.get("height", 0)}
            if title:
                info["title"] = title
            return info
        except Exception:
            return {}

    def window_list(self) -> list[dict]:
        """List windows of the managed app using AppleScript."""
        try:
            bid = self._managed_bundle_id()
            if not bid:
                return []
            safe_bid = _safe_applescript_str(bid)
            script = ('tell application "System Events"\n'
                      f'  set ap to first application process whose bundle identifier is "{safe_bid}"\n'
                      '  get name of every window of ap\n'
                      'end tell')
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return []
            names = [n.strip() for n in result.stdout.strip().split(", ")]
            windows = []
            for i, name in enumerate(names):
                windows.append({"index": i, "title": name})
            return windows
        except Exception:
            return []

    def window_focus(self, index: int) -> dict:
        """Focus a window by index using AppleScript."""
        try:
            bid = self._managed_bundle_id()
            if not bid:
                return {"error_code": ErrorCode.WINDOW_NOT_FOUND, "detail": "No managed bundle ID"}
            # First, get the window count to validate index
            windows = self.window_list()
            if index < 0 or index >= len(windows):
                max_idx = len(windows) - 1 if windows else 0
                return {"error_code": ErrorCode.WINDOW_NOT_FOUND,
                        "detail": f"Window index {index} out of range (0-{max_idx})"}
            # AppleScript uses 1-based indexing
            safe_bid = _safe_applescript_str(bid)
            script = ('tell application "System Events"\n'
                      f'  set ap to first application process whose bundle identifier is "{safe_bid}"\n'
                      f'  perform action "AXRaise" of window {index + 1} of ap\n'
                      'end tell')
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if result.returncode != 0:
                return {"error_code": ErrorCode.WINDOW_NOT_FOUND,
                        "detail": result.stderr.strip() or "Failed to focus window"}
            title = windows[index].get("title", "")
            info = self._wait_for_frontmost_window(bid, title, timeout=5)
            if info is None:
                return {"error_code": ErrorCode.TIMEOUT,
                        "detail": f"Timed out waiting for window {title!r} to become frontmost"}
            self._invalidate_refs()
            return {"focused": index, "title": title}
        except Exception as exc:
            return {"error_code": ErrorCode.WINDOW_NOT_FOUND, "detail": str(exc)}

    # -- wait ---------------------------------------------------------------

    def wait_element(self, value: str, strategy: str = "accessibility_id", timeout: int = 10) -> bool:
        locator = _resolve_locator(strategy, value)
        try:
            WebDriverWait(self._driver, timeout).until(EC.presence_of_element_located(locator))
            return True
        except Exception:
            return False

    def wait_window(self, title: str, timeout: float = 10) -> bool:
        """Poll for a window with the given title to appear."""
        bid = self._managed_bundle_id()
        if not bid:
            return False
        try:
            _safe_applescript_str(bid)
        except ValueError:
            return False
        return self._poll_until(
            lambda: (snapshot if (snapshot := self._managed_window_snapshot(bid)) and any(title.lower() in name.lower() for name in snapshot.get("titles", [])) else None),
            timeout=timeout,
        ) is not None

    def wait_app(self, bundle_id: str, timeout: float = 10) -> bool:
        """Poll for an application with the given bundle ID to appear."""
        try:
            _safe_applescript_str(bundle_id)
        except ValueError:
            return False
        return self._poll_until(
            lambda: self._app_process_snapshot(bundle_id),
            timeout=timeout,
        ) is not None

    # -- doctor helpers -----------------------------------------------------

    def check_server(self) -> tuple[bool, str]:
        import httpx
        try:
            r = httpx.get(f"{self._server_url}/status", timeout=5)
            return r.status_code == 200, f"Appium server at {self._server_url}"
        except Exception as exc:
            return False, str(exc)

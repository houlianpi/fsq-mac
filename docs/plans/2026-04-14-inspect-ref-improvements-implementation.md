# Inspect & Ref Stabilization Patch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the three-change stabilization patch from `docs/plans/2026-04-14-inspect-ref-improvements-design.md` — best-effort auto-snapshot after mutations, `ref_bound` field, and improved stale ref diagnostics.

**Architecture:** Changes span three files: `models.py` (add `ref_bound` field), `appium_mac2.py` (remove alignment verification, emit `ref_bound`, improve stale ref error details), and `core.py` (best-effort post-action snapshot helper). The adapter's `inspect()` method returns element dicts with `ref_bound`; the core's `_element_action()` / `element_type()` / `element_drag()` attempt a follow-up `inspect()` and attach it as `snapshot` with a `snapshot_status` field.

**Tech Stack:** Python 3.10+, pytest, unittest.mock

---

### Task 1: Add `ref_bound` field to `ElementInfo`

**Files:**
- Modify: `src/fsq_mac/models.py:184-210`
- Test: `tests/test_models.py` (create)

**Step 1: Write the failing test**

Create `tests/test_models.py`:

```python
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for models.py — ElementInfo ref_bound field."""

from fsq_mac.models import ElementInfo


def test_element_info_ref_bound_default_true():
    el = ElementInfo(element_id="e0", role="Button")
    assert el.ref_bound is True


def test_element_info_ref_bound_in_to_dict():
    el = ElementInfo(element_id="e0", role="Button", ref_bound=True)
    d = el.to_dict()
    assert d["ref_bound"] is True


def test_element_info_ref_bound_false():
    el = ElementInfo(element_id="e0", role="Button", ref_bound=False)
    d = el.to_dict()
    assert d["ref_bound"] is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `TypeError: unexpected keyword argument 'ref_bound'`

**Step 3: Write minimal implementation**

In `src/fsq_mac/models.py`, add to `ElementInfo` dataclass (after `doc_order_index` field, line 196):

```python
ref_bound: bool = True  # whether a WebElement ref was bound during inspect
```

In `ElementInfo.to_dict()` (line 198-210), add `ref_bound` to the returned dict:

```python
def to_dict(self) -> dict:
    return {
        "element_id": self.element_id,
        "role": self.role,
        "name": self.name,
        "label": self.label,
        "value": self.value,
        "enabled": self.enabled,
        "visible": self.visible,
        "focused": self.focused,
        "frame": self.frame,
        "locator_hint": self.locator_hint,
        "ref_bound": self.ref_bound,
    }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All existing tests pass (ref_bound defaults to True, so no existing behavior changes)

**Step 6: Commit**

```bash
git add tests/test_models.py src/fsq_mac/models.py
git commit -m "Add ref_bound field to ElementInfo"
```

---

### Task 2: Remove alignment verification and emit `ref_bound` in `inspect()`

**Files:**
- Modify: `src/fsq_mac/adapters/appium_mac2.py:1022-1093`
- Test: `tests/test_inspect_refs.py`

**Step 1: Write the failing test**

Add to `tests/test_inspect_refs.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_inspect_refs.py -v`
Expected: `ref_bound` tests fail (key not in dict), alignment verification test fails (get_attribute IS called)

**Step 3: Replace the inspect() method**

In `src/fsq_mac/adapters/appium_mac2.py`, replace the `inspect()` method (lines 1022-1093) with:

```python
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
                                enabled=info.enabled)
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
```

Key changes:
- Removed all alignment verification code (lines 1035-1088): no more sampling, `get_attribute("name")`, mismatch reporting
- Added `info.ref_bound = True/False` based on whether binding succeeded
- On timeout/exception, all elements get `ref_bound = False`

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_inspect_refs.py -v`
Expected: All PASS

**Step 5: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All pass

**Step 6: Commit**

```bash
git add src/fsq_mac/adapters/appium_mac2.py tests/test_inspect_refs.py
git commit -m "Remove alignment verification, emit ref_bound in inspect"
```

---

### Task 3: Improve stale ref error diagnostics

**Files:**
- Modify: `src/fsq_mac/adapters/appium_mac2.py` (click, right_click, double_click, _resolve_ref)
- Modify: `src/fsq_mac/core.py:337-351` (_element_action)
- Test: `tests/test_stale_ref_diagnostics.py` (create)

**Step 1: Write the failing test**

Create `tests/test_stale_ref_diagnostics.py`:

```python
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for improved stale ref diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter
from fsq_mac.models import ErrorCode


def test_stale_ref_includes_cached_identity(mock_config):
    """Stale ref errors should include cached name and role in the detail."""
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    adapter._driver = driver

    driver.page_source = (
        '<AppiumAUT>'
        '<XCUIElementTypeButton name="Submit" visible="true" enabled="true" '
        'x="0" y="0" width="80" height="30"/>'
        '</AppiumAUT>'
    )
    web_el = MagicMock(name="WebElement_0")
    web_el.location = {"x": 0, "y": 0}
    driver.find_elements.return_value = [web_el]

    adapter.inspect()

    # Invalidate refs to make e0 stale
    adapter._invalidate_refs()

    result = adapter.click("e0")
    assert result["error_code"] == ErrorCode.ELEMENT_REFERENCE_STALE
    assert "detail" in result
    assert "Submit" in result["detail"]
    assert "e0" in result["detail"]


def test_stale_ref_error_includes_details_dict(mock_config):
    """Stale ref errors should include structured details dict."""
    adapter = AppiumMac2Adapter(mock_config)
    driver = MagicMock()
    adapter._driver = driver

    driver.page_source = (
        '<AppiumAUT>'
        '<XCUIElementTypeButton name="Submit" visible="true" enabled="true" '
        'x="0" y="0" width="80" height="30"/>'
        '</AppiumAUT>'
    )
    web_el = MagicMock(name="WebElement_0")
    web_el.location = {"x": 0, "y": 0}
    driver.find_elements.return_value = [web_el]

    adapter.inspect()
    adapter._invalidate_refs()

    result = adapter.click("e0")
    assert result["error_code"] == ErrorCode.ELEMENT_REFERENCE_STALE
    assert "details" in result
    assert result["details"]["ref"] == "e0"
    assert result["details"]["cached_name"] == "Submit"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stale_ref_diagnostics.py -v`
Expected: FAIL — `detail` doesn't contain "Submit", no `details` key

**Step 3: Improve stale ref error details in adapter**

The adapter action methods (click, right_click, etc.) currently return bare `{"error_code": err}` when `_resolve_ref` fails. We need to propagate richer error info.

**3a. Add a `_stale_ref_error` helper** to `appium_mac2.py` (after `_get_ref_cached_state`, around line 680):

```python
def _stale_ref_error(self, ref: str) -> dict:
    """Build a rich stale-ref error dict with cached identity."""
    cached_name = self._get_ref_name(ref)
    # Get cached role from the entry if it exists
    entry = self._element_refs.get(ref)
    cached_role = None
    if entry and len(entry) >= 6:
        # We don't store role in the tuple, but we store frame
        # Role isn't in the 6-tuple, so we'll omit it
        pass
    detail = f"Ref '{ref}' is stale; UI changed since the last inspect"
    if cached_name:
        detail = f"Ref '{ref}' ({cached_name}) is stale; UI changed since the last inspect"
    result = {
        "error_code": ErrorCode.ELEMENT_REFERENCE_STALE,
        "detail": detail,
        "details": {
            "ref": ref,
            "cached_name": cached_name,
            "reason": "generation_mismatch",
        },
    }
    return result
```

**3b. Update `click()` method** (line 1132-1135) to use rich error:

Replace:
```python
el, err = self._resolve_ref(ref, strategy, timeout)
if err:
    return {"error_code": err}
```

With:
```python
el, err = self._resolve_ref(ref, strategy, timeout)
if err:
    eid = self._ref_eid(ref)
    if err == ErrorCode.ELEMENT_REFERENCE_STALE and eid:
        return self._stale_ref_error(eid)
    return {"error_code": err}
```

**3c. Apply the same pattern to `right_click()`, `double_click()`, `hover()`, `scroll()`, `type_text()`** — search for `return {"error_code": err}` after `_resolve_ref` calls and add the stale ref enrichment.

**3d. Update core.py `_element_action` to propagate `details`** (line 337-351):

In `_element_action`, pass `details` from the adapter result to the error response:

Replace:
```python
err_code = result.get("error_code")
if err_code:
    ref = query.ref or query.to_dict()
    msg = result.get("detail", f"Action failed on '{ref}'")
    suggested = "mac element inspect" if err_code == ErrorCode.ELEMENT_REFERENCE_STALE else None
    return error_response(command, err_code, msg, session_id=active,
                          meta=self._meta(t, active), suggested_next_action=suggested)
```

With:
```python
err_code = result.get("error_code")
if err_code:
    ref = query.ref or query.to_dict()
    msg = result.get("detail", f"Action failed on '{ref}'")
    suggested = "mac element inspect" if err_code == ErrorCode.ELEMENT_REFERENCE_STALE else None
    details = result.get("details")
    return error_response(command, err_code, msg, session_id=active,
                          meta=self._meta(t, active), suggested_next_action=suggested,
                          details=details)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_stale_ref_diagnostics.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All pass

**Step 6: Commit**

```bash
git add src/fsq_mac/adapters/appium_mac2.py src/fsq_mac/core.py tests/test_stale_ref_diagnostics.py
git commit -m "Improve stale ref error diagnostics with cached identity"
```

---

### Task 4: Best-effort auto-snapshot after mutating actions

**Files:**
- Modify: `src/fsq_mac/core.py:337-430`
- Test: `tests/test_auto_snapshot.py` (create)

**Step 1: Write the failing tests**

Create `tests/test_auto_snapshot.py`:

```python
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for best-effort auto-snapshot after mutating actions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fsq_mac.core import AutomationCore
from fsq_mac.models import ErrorCode, LocatorQuery
from fsq_mac.session import SessionManager
import fsq_mac.session as session_module


@pytest.fixture()
def mock_adapter():
    adapter = MagicMock(unsafe=True)
    adapter.connected = True
    return adapter


@pytest.fixture()
def core_with_session(tmp_path, monkeypatch, mock_adapter):
    monkeypatch.setattr(session_module, "STATE_DIR", tmp_path)
    config = {"server_url": "http://127.0.0.1:4723"}
    sm = SessionManager(config, adapter_factory=lambda c: mock_adapter)
    sm.start()
    core = AutomationCore(sm)
    return core, mock_adapter


class TestAutoSnapshot:
    def test_click_attaches_snapshot_on_success(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {"x": 100, "y": 200}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "Button", "name": "Home", "ref_bound": True}
        ]
        resp = core.element_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"
        assert resp.data["snapshot"]["elements"][0]["name"] == "Home"
        assert resp.data["snapshot"]["count"] == 1

    def test_click_snapshot_failed_best_effort(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {"x": 100, "y": 200}
        adapter.inspect.side_effect = RuntimeError("driver gone")
        resp = core.element_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "failed_best_effort"
        assert "snapshot" not in resp.data

    def test_click_error_no_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.click.return_value = {"error_code": ErrorCode.ELEMENT_NOT_FOUND}
        resp = core.element_click("e0")
        assert resp.ok is False
        # No snapshot attempted on failure
        adapter.inspect.assert_not_called()

    def test_hover_no_snapshot(self, core_with_session):
        """Hover is non-mutating — should NOT attach snapshot."""
        core, adapter = core_with_session
        adapter.hover.return_value = {"x": 50, "y": 60}
        resp = core.element_hover("e0")
        assert resp.ok is True
        assert "snapshot_status" not in resp.data
        adapter.inspect.assert_not_called()

    def test_right_click_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.right_click.return_value = {"x": 10, "y": 20}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "MenuItem", "name": "Copy", "ref_bound": True}
        ]
        resp = core.element_right_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"

    def test_double_click_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.double_click.return_value = {"x": 10, "y": 20}
        adapter.inspect.return_value = []
        resp = core.element_double_click("e0")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"
        assert resp.data["snapshot"]["count"] == 0

    def test_scroll_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.scroll.return_value = {}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "ScrollArea", "name": None, "ref_bound": True}
        ]
        resp = core.element_scroll("e0", "down")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"

    def test_type_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.type_text.return_value = {"verified": True, "typed_value": "hello", "expected": "hello"}
        adapter.inspect.return_value = [
            {"element_id": "e0", "role": "TextField", "name": "Input", "ref_bound": True}
        ]
        resp = core.element_type("e0", "hello")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"

    def test_drag_attaches_snapshot(self, core_with_session):
        core, adapter = core_with_session
        adapter.drag.return_value = {}
        adapter.inspect.return_value = []
        resp = core.element_drag("e0", "e1")
        assert resp.ok is True
        assert resp.data["snapshot_status"] == "attached"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auto_snapshot.py -v`
Expected: FAIL — `snapshot_status` not in response data

**Step 3: Implement best-effort auto-snapshot in core.py**

**3a. Add a `_best_effort_snapshot` helper method** to `AutomationCore` (before `_element_action`, around line 337):

```python
# -- best-effort post-action snapshot ------------------------------------

_MUTATING_COMMANDS = frozenset({
    "element.click", "element.right-click", "element.double-click",
    "element.type", "element.scroll", "element.drag",
})

def _best_effort_snapshot(self, adapter, data: dict) -> dict:
    """Attempt adapter.inspect() and attach results to data.

    Always adds snapshot_status. Never raises.
    """
    try:
        elements = adapter.inspect()
        data["snapshot_status"] = "attached"
        data["snapshot"] = {
            "elements": elements,
            "count": len(elements),
        }
    except Exception:
        data["snapshot_status"] = "failed_best_effort"
    return data
```

**3b. Update `_element_action` to call `_best_effort_snapshot`** for mutating commands:

Replace the success return (line 351):
```python
return success_response(command, data=result or {}, session_id=active, meta=self._meta(t, active))
```

With:
```python
data = result or {}
if command in self._MUTATING_COMMANDS:
    self._best_effort_snapshot(adapter, data)
return success_response(command, data=data, session_id=active, meta=self._meta(t, active))
```

**3c. Update `element_type`** (lines 377-401):

After the success return at line 400-401, change:
```python
return success_response("element.type", data=data or None,
                        session_id=active, meta=self._meta(t, active))
```

To:
```python
if not data:
    data = {}
self._best_effort_snapshot(adapter, data)
return success_response("element.type", data=data,
                        session_id=active, meta=self._meta(t, active))
```

**3d. Update `element_drag`** (lines 419-429):

After the success return at line 429, change:
```python
return success_response("element.drag", session_id=active, meta=self._meta(t, active))
```

To:
```python
data = {}
self._best_effort_snapshot(adapter, data)
return success_response("element.drag", data=data, session_id=active, meta=self._meta(t, active))
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_auto_snapshot.py -v`
Expected: All PASS

**Step 5: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All pass. Note: existing tests that checked `resp.data` for click/type/drag may need minor adjustments if they check exact dict shape — verify and update if needed.

**Step 6: Commit**

```bash
git add src/fsq_mac/core.py tests/test_auto_snapshot.py
git commit -m "Add best-effort auto-snapshot after mutating actions"
```

---

### Task 5: Final integration test and cleanup

**Files:**
- All modified files
- Test: `tests/test_core.py` (verify existing tests still pass)

**Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS

**Step 2: Verify snapshot_status not present in non-mutating commands**

Manually verify in `tests/test_core.py` that hover, inspect, find responses do NOT have `snapshot_status` field. If existing tests check exact `resp.data` shapes, update them to account for new `snapshot_status` and `snapshot` keys in mutating action responses.

**Step 3: Commit any test fixups**

```bash
git add -u
git commit -m "Fix test expectations for auto-snapshot fields"
```

**Step 4: Final commit with all changes**

Verify the git log shows clean TDD progression:
```bash
git log --oneline -10
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `src/fsq_mac/models.py` | Add `ref_bound: bool = True` to `ElementInfo`, include in `to_dict()` |
| `src/fsq_mac/adapters/appium_mac2.py` | Remove alignment verification block (lines 1035-1088), set `ref_bound` per element, add `_stale_ref_error()` helper, enrich stale ref returns in `click`/`right_click`/`double_click`/`hover`/`scroll`/`type_text` |
| `src/fsq_mac/core.py` | Add `_MUTATING_COMMANDS` set, `_best_effort_snapshot()` helper, call it from `_element_action`/`element_type`/`element_drag`, propagate `details` in `_element_action` error path |
| `tests/test_models.py` | New: `ref_bound` field tests |
| `tests/test_inspect_refs.py` | New: `ref_bound` in inspect output, no alignment verification |
| `tests/test_stale_ref_diagnostics.py` | New: stale ref error includes cached identity |
| `tests/test_auto_snapshot.py` | New: snapshot_status attached/failed/not-present for mutating/non-mutating |

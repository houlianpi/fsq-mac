# Phase 2: Core Differentiators Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add lazy locators, auto-wait, assertions, menu clicks, and coordinate clicks so `fsq-mac` starts to feel like a deterministic automation tool instead of an inspect-then-act prototype.

**Architecture:** Introduce a shared `LocatorQuery` model, thread it through CLI → daemon → core → adapter, and keep backend-specific lookup and auto-wait logic in `AppiumMac2Adapter`. Implement Phase 2 in two checkpoints so the larger feature set stays reviewable.

**Tech Stack:** Python 3.10+, argparse, dataclasses, Starlette, Appium Mac2 WebDriver, AppleScript/System Events, pytest, unittest.mock

---

### Task 1: Add shared locator and assertion models

**Files:**
- Modify: `src/fsq_mac/models.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

Add tests for:

```python
def test_locator_query_to_dict_for_role_name():
    query = LocatorQuery(role="AXButton", name="Submit")
    assert query.to_dict() == {"role": "AXButton", "name": "Submit"}


def test_assertion_failed_error_code_value():
    assert ErrorCode.ASSERTION_FAILED.value == "ASSERTION_FAILED"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -q`
Expected: FAIL because `LocatorQuery` and `ASSERTION_FAILED` do not exist yet.

**Step 3: Write minimal implementation**

Add:

- `ErrorCode.ASSERTION_FAILED`
- `LocatorQuery` dataclass with `ref`, `id`, `role`, `name`, `label`, `xpath`
- `LocatorQuery.to_dict()` that omits empty fields

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/models.py tests/test_models.py
git commit -m "Add phase 2 locator query model"
```

---

### Task 2: Add CLI support for lazy locator flags and new domains

**Files:**
- Modify: `src/fsq_mac/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_routes.py`

**Step 1: Write the failing test**

Add parser and `_run()` tests for:

- `mac element click --role AXButton --name Submit`
- `mac element type --label Search hello`
- `mac assert visible --role AXButton --name Submit`
- `mac menu click "File > Open"`
- `mac input click-at 100 200`

Example:

```python
def test_run_maps_lazy_locator_click():
    args = self._make_args(["element", "click", "--role", "AXButton", "--name", "Submit"])
    ...
    assert call_kwargs["role"] == "AXButton"
    assert call_kwargs["name"] == "Submit"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py tests/test_routes.py -q`
Expected: FAIL because the parser and route list do not support these commands yet.

**Step 3: Write minimal implementation**

In `src/fsq_mac/cli.py`:

- add reusable locator flags to relevant parsers
- make element actions accept either positional `ref` or locator flags
- add `assert` and `menu` domains
- add `input click-at`
- map new args through `_run()`

In `tests/test_routes.py`, extend `_ALL_COMMANDS` expectations for the new command pairs.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py tests/test_routes.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/cli.py tests/test_cli.py tests/test_routes.py
git commit -m "Add phase 2 CLI surfaces"
```

---

### Task 3: Add protocol methods and daemon dispatch for Phase 2

**Files:**
- Modify: `src/fsq_mac/adapters/protocol.py`
- Modify: `src/fsq_mac/daemon.py`
- Modify: `tests/test_protocol.py`
- Modify: `tests/test_routes.py`

**Step 1: Write the failing test**

Add dispatch tests so these routes resolve instead of falling through:

- `assert.visible`
- `assert.enabled`
- `assert.text`
- `assert.value`
- `menu.click`
- `input.click-at`

Add protocol expectations for assertion/menu/click-at methods.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_protocol.py tests/test_routes.py -q`
Expected: FAIL because protocol and daemon dispatch are incomplete.

**Step 3: Write minimal implementation**

Update protocol and `_dispatch()` to pass through the new commands and locator fields.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_protocol.py tests/test_routes.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/adapters/protocol.py src/fsq_mac/daemon.py tests/test_protocol.py tests/test_routes.py
git commit -m "Thread phase 2 routes through daemon"
```

---

### Task 4: Implement lazy locator resolution and auto-wait in the adapter

**Files:**
- Modify: `src/fsq_mac/adapters/appium_mac2.py`
- Modify: `tests/test_adapter_methods.py`
- Modify: `tests/test_find.py`

**Step 1: Write the failing test**

Add focused tests for:

- resolving `role + name`
- resolving `label`
- resolving `xpath`
- ambiguous lazy locator returns `ELEMENT_AMBIGUOUS`
- auto-wait succeeds after element becomes stable
- auto-wait times out when element stays disabled or unstable

Example:

```python
def test_click_waits_for_stable_element(adapter_with_driver):
    ...
    result = adapter_with_driver.click(role="AXButton", name="Submit")
    assert result == {}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapter_methods.py tests/test_find.py -q`
Expected: FAIL because the adapter only knows `ref + strategy` today.

**Step 3: Write minimal implementation**

Add:

- a query-aware resolver
- helper methods to inspect visible/enabled/stable state
- auto-wait wrapper used by interaction methods
- structured error results for ambiguous queries and timeouts

Keep existing `e0` semantics unchanged.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapter_methods.py tests/test_find.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/adapters/appium_mac2.py tests/test_adapter_methods.py tests/test_find.py
git commit -m "Add lazy locators and auto-wait"
```

---

### Task 5: Implement core-level locator mapping for element actions

**Files:**
- Modify: `src/fsq_mac/core.py`
- Modify: `tests/test_core.py`

**Step 1: Write the failing test**

Add tests that verify `AutomationCore` forwards lazy locator fields and maps adapter errors correctly for:

- `element.click`
- `element.type`
- `element.drag`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_core.py -q`
Expected: FAIL because core methods currently only forward `ref` and `strategy`.

**Step 3: Write minimal implementation**

Reconstruct `LocatorQuery` instances from request parameters and pass them to adapter methods. Preserve existing stale-ref guidance and error envelopes.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_core.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/core.py tests/test_core.py
git commit -m "Map phase 2 locators through core"
```

---

### Task 6: Add assertion commands end to end

**Files:**
- Modify: `src/fsq_mac/core.py`
- Modify: `src/fsq_mac/adapters/appium_mac2.py`
- Modify: `tests/test_core.py`
- Modify: `tests/test_adapter_methods.py`

**Step 1: Write the failing test**

Add tests for:

- visible assertion success/failure
- enabled assertion success/failure
- text assertion success/failure
- value assertion success/failure

Failure cases should assert `ASSERTION_FAILED`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_core.py tests/test_adapter_methods.py -q`
Expected: FAIL because assertion methods do not exist.

**Step 3: Write minimal implementation**

Add assertion methods in the adapter and response mapping in the core.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_core.py tests/test_adapter_methods.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/core.py src/fsq_mac/adapters/appium_mac2.py tests/test_core.py tests/test_adapter_methods.py
git commit -m "Add assertion commands"
```

---

### Task 7: Add menu click and coordinate click

**Files:**
- Modify: `src/fsq_mac/core.py`
- Modify: `src/fsq_mac/adapters/appium_mac2.py`
- Modify: `tests/test_core.py`
- Modify: `tests/test_adapter_methods.py`

**Step 1: Write the failing test**

Add tests for:

- `menu.click("File > Open")`
- invalid menu path handling
- `input.click-at(100, 200)`
- AppleScript failure handling

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_core.py tests/test_adapter_methods.py -q`
Expected: FAIL because these operations do not exist.

**Step 3: Write minimal implementation**

Implement AppleScript-backed adapter methods and core response mapping.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_core.py tests/test_adapter_methods.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fsq_mac/core.py src/fsq_mac/adapters/appium_mac2.py tests/test_core.py tests/test_adapter_methods.py
git commit -m "Add menu and coordinate click commands"
```

---

### Task 8: Run full verification and final cleanup

**Files:**
- Review: `src/fsq_mac/*.py`
- Review: `tests/*.py`

**Step 1: Run targeted suites first**

Run:

```bash
pytest tests/test_models.py tests/test_cli.py tests/test_routes.py tests/test_protocol.py tests/test_core.py tests/test_adapter_methods.py tests/test_find.py -q
```

Expected: PASS.

**Step 2: Run full suite**

Run:

```bash
pytest -q
```

Expected: PASS.

**Step 3: Review diff for accidental scope growth**

Check:

- locator handling remains consistent across layers
- no old commands regressed
- assertion failures use the dedicated error code
- no debug prints or dead helpers remain

**Step 4: Commit**

```bash
git add src/fsq_mac tests docs/plans
git commit -m "Implement phase 2 core differentiators"
```

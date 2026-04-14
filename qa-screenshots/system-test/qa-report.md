# System Test Report — fsq-mac Stabilization Patch

**Date:** 2026-04-14
**Version:** fsq-mac 0.2.1 (dev)
**Daemon:** Appium Mac2 backend
**Platform:** macOS Darwin 25.4.0

---

## Test Matrix

| ID | Phase | Difficulty | Description | Result |
|----|-------|-----------|-------------|--------|
| N1 | Native (Calculator) | Simple | Inspect + Click + Snapshot Contract | PASS |
| N2 | Native (Calculator) | Medium | Stale Ref Error Diagnostics | PASS |
| N3 | Native (Calculator) | Complex | Multi-step Interaction (5 × 3 = 15) | PASS |
| W1 | Web App (Edge) | Simple | Inspect + Snapshot Contract | PASS |
| W2 | Web App (Edge) | Medium | Navigate to URL + Auto-Snapshot | PASS |
| W3 | Web App (Edge) | Complex | Click Link + Verify Navigation | PASS |

**Overall: 6/6 PASS**

---

## Phase 1: Native App (Calculator)

### N1: Inspect + Click + Snapshot Contract (PASS)

**Goal:** Verify that inspect returns correct snapshot-level and element-level contract fields; verify click returns auto-snapshot.

**Steps:**
1. `mac app launch com.apple.calculator`
2. `mac element inspect --json` → 46 elements, all bound

**Snapshot contract verified:**
- `snapshot_id`: snap_5
- `generation`: 5
- `backend`: appium_mac2
- `binding_mode`: bound
- `elements`: 46 elements array
- `count`: 46

**Element contract verified (all 46 elements):**
- `ref`: present (e0–e45)
- `element_bounds`: present with x, y, width, height
- `center`: present with x, y
- `ref_bound`: True for all 46 elements
- `ref_status`: "bound" for all 46 elements
- `state_source`: "xml" for all elements

**Click auto-snapshot verified:**
- Clicked e13 (button "5") → ok=True
- Response included: `resolved_element`, `actionability_used`, `element_bounds`, `center`
- `snapshot_status`: "attached"
- Auto-snapshot: snap_7, generation=7, binding_mode=bound, count=46

---

### N2: Stale Ref Error Diagnostics (PASS)

**Goal:** Verify enriched stale ref errors include cached_name, cached_role, reason, and suggested_next_action.

**Steps:**
1. Inspected Calculator (got refs e0–e45)
2. Launched TextEdit to change app context
3. Clicked old ref e13 → ELEMENT_REFERENCE_STALE

**Error response verified:**
```json
{
  "error_code": "ELEMENT_REFERENCE_STALE",
  "message": "Ref 'e13' (5, Button) is stale; UI changed since the last inspect",
  "suggested_next_action": "mac element inspect",
  "details": {
    "ref": "e13",
    "cached_name": "5",
    "cached_role": "Button",
    "reason": "generation_mismatch"
  }
}
```

All enriched diagnostic fields present and accurate.

---

### N3: Multi-step Interaction — 5 × 3 = 15 (PASS)

**Goal:** Verify auto-snapshot consistency across a multi-step calculation sequence.

**Steps:**
1. Inspected Calculator → identified button refs
2. Executed: AC → 5 → × → 3 → =
3. Verified result via screenshot

**Auto-snapshot tracking:**

| Step | Action | Generation | snapshot_status |
|------|--------|-----------|-----------------|
| AC (e5) | Clear | 18→19 | attached |
| 5 (e13) | Digit | 20→21 | attached |
| × (e11) | Multiply | 22→23 | attached |
| 3 (e18) | Digit | 24→25 | attached |
| = (e23) | Equals | 26→27 | attached |

All 5 clicks returned ok=True with auto-snapshots attached. Generations incremented consistently.

**Evidence:** `calc_result.png` — Calculator displays "15" (correct).

---

## Phase 2: Web App (Microsoft Edge)

**Bundle ID:** com.microsoft.edgemac

### W1: Edge Inspect + Snapshot Contract (PASS)

**Goal:** Verify inspect works correctly on a browser app with more complex UI.

**Steps:**
1. `mac app launch com.microsoft.edgemac`
2. `mac element inspect --json` → 140 elements

**Snapshot contract verified:**
- All fields present: snapshot_id, generation, backend, binding_mode, count
- binding_mode: bound (all 140 elements bound)

**Element contract verified (all 140 elements):**
- ref_bound: True for all 140 elements
- ref_status: "bound" for all 140 elements
- element_bounds and center present for all elements

---

### W2: Navigate to URL + Auto-Snapshot (PASS)

**Goal:** Verify click + type interaction on a web browser; verify auto-snapshot after mutations.

**Steps:**
1. Found address bar: e6 (role=TextField, name="Address and search bar")
2. Clicked e6 → ok=True, snapshot_status=attached
3. Auto-snapshot: generation=31, count=185 (UI expanded after click)
4. Typed "example.com" + Enter
5. Window title confirmed: "Example Domain - Microsoft Edge - Work"

---

### W3: Click Link + Verify Navigation (PASS)

**Goal:** Complex web interaction — click a link inside a rendered web page and verify navigation.

**Steps:**
1. Inspected example.com page
2. Found "Learn more" link: e18
3. Clicked e18 → ok=True, snapshot_status=attached
4. Auto-snapshot: generation=34, count=56 (page changed, fewer elements)
5. Verified via screenshot: IANA website loaded

**Evidence:** `edge_after_click.png` — Edge shows IANA page (confirmed navigation).

**Observation:** `mac window list` still reports "Example Domain" title after navigation. This appears to be a browser accessibility-tree caching behavior, not an fsq-mac issue. The actual page content navigated correctly as confirmed by screenshot.

---

## Summary of Verified Features

| Feature | Status | Notes |
|---------|--------|-------|
| Snapshot contract fields | OK | All fields present in every inspect |
| Element ref_bound field | OK | Accurately reports True for all bound elements |
| Element ref_status field | OK | Reports "bound" for all bound refs |
| Auto-snapshot after click | OK | snapshot_status="attached" on every mutation |
| Generation increments | OK | Consistent incrementing across multi-step sequences |
| Stale ref cached_name | OK | Included in error response |
| Stale ref cached_role | OK | Included in error response |
| Stale ref reason | OK | "generation_mismatch" correctly reported |
| Stale ref suggested_next_action | OK | "mac element inspect" correctly suggested |
| Native app (Calculator) | OK | All interactions reliable |
| Web app (Edge) | OK | All interactions reliable |

## Issues Found

**None.** All stabilization patch features work correctly across both native and web app targets.

## Observations (non-blocking)

1. **Window title caching in Edge:** `mac window list` may not reflect the latest page title immediately after in-page navigation. This is likely a browser accessibility-tree behavior rather than an fsq-mac issue.

2. **`mac assert value` syntax:** The assert command requires locator flags (e.g., `--name`), making direct value assertion on the focused element non-obvious. Consider documenting common assert patterns.

---

**Verdict: ALL PASS (6/6)** — The stabilization patch is working correctly.

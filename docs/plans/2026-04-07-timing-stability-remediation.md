# Timing Stability Remediation

> Date: 2026-04-07
> Status: In Progress

## Goal

Close the remaining timing-stability gaps in the Appium Mac2 adapter so targeted commands return promptly under slow or hung driver calls instead of blocking indefinitely.

## Problem Summary

The first remediation pass covered direct action execution such as `click()`, `double_click()`, `hover()`, and `type_text()` by routing driver calls through `_run_with_timeout()`.

Two unstable paths remain:

1. `_get_page_source()` still reads `driver.page_source` directly, so `element inspect` and `capture ui-tree` can hang if Appium stalls while building the accessibility tree.
2. `_wait_for_actionable()` still probes element frame and state directly, so commands can hang before the guarded action path even starts.

There is also a secondary stability issue in `inspect()`: ref binding via `find_elements("//*")` is best-effort, but today it can still block the whole inspect command.

The next gap is action completion semantics around app and window transitions. Several commands return success immediately after issuing an activate/focus request, even when the requested app or window has not actually become frontmost yet. That creates flaky follow-up commands and weakens the meaning of `wait_app()` / `wait_window()`.

## Scope

### Included

- Guard `driver.page_source` with `command_timeout`
- Guard actionable-state probing with remaining command budget
- Make inspect ref binding best-effort under timeout pressure
- Add a shared polling helper for frontmost app/window stabilization
- Wait for app launch, app activation, and window focus to actually settle
- Move `wait_app()` and `wait_window()` to the shared polling path with finer polling cadence
- Add regression tests in `tests/test_adapter_methods.py`
- Update the manual E2E plan with timing-stability checks

### Excluded

- Changes to CLI or response envelope semantics
- New timeout-related config knobs
- Broader refactors of locator resolution or trace capture

## Implementation Notes

### Adapter

- Update `_get_page_source()` to fetch page source via `_run_with_timeout()` and raise a bounded adapter error when the fetch exceeds `command_timeout`.
- Refactor `_wait_for_actionable()` so each probe of frame, visibility, and enabled state is time-bounded.
- Keep the existing actionable contract: return `TIMEOUT` when the element never becomes ready, but avoid unbounded driver access while checking readiness.
- In `inspect()`, treat wildcard element binding as optional. If it times out, return parsed elements without ref hydration instead of failing the whole command.

### Adapter Phase 2

- Add `_poll_until(predicate, timeout, interval)` as the single polling primitive for timing-sensitive adapter waits.
- Extract frontmost app/window snapshot helpers so launch, activate, focus, and wait operations read the same state source.
- Require `app_launch()` to wait until the requested bundle is actually frontmost before returning success; otherwise return `TIMEOUT`.
- Require `app_activate()` to wait until the requested bundle is actually frontmost before returning success; otherwise return `TIMEOUT`.
- Require `window_focus()` to wait until the requested window title is actually frontmost before returning success; otherwise return `TIMEOUT`.
- Keep existing no-driver and invalid-argument behaviors unchanged.

### Tests

- Add regression coverage for timed-out page-source fetches.
- Add regression coverage for actionable checks when element frame reads hang.
- Add coverage that `inspect()` still returns parsed elements when ref binding times out.
- Add regression coverage for frontmost app/window stabilization after launch, activate, and focus.
- Add coverage that `wait_app()` and `wait_window()` route through the shared polling helper.

### Docs

- Extend the manual E2E plan with a timing-stability section that exercises repeated inspect/ui-tree calls and verifies bounded failure on slow clicks.
- Extend the manual E2E plan with app/window stabilization checks so launch, activate, focus, and wait semantics are verified against real frontmost state.

## Verification

Run:

```bash
pytest -q tests/test_adapter_methods.py tests/test_command_timeout.py tests/test_tree_cache.py
```

Expected result: all timing-stability and cache regressions pass, with no new hangs in targeted adapter tests.

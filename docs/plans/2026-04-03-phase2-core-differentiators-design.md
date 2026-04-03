# Phase 2: Core Differentiators — Design Document

> Date: 2026-04-03
> Status: Approved

## Goal

Implement the first set of Playwright-class differentiators for `fsq-mac`:

1. Lazy locator queries that coexist with static refs like `e0`
2. Actionability-based auto-wait before mutations
3. Assertion commands for visibility, enabled state, text, and value
4. Menu bar click support for common macOS workflows
5. Coordinate click support for non-accessible surfaces

---

## Architecture Choice

Use a single structured locator model instead of adding one-off flags per command.

The core abstraction is a `LocatorQuery` value object. CLI parsing normalizes user input into one of two targeting modes:

- Static reference: `ref="e0"`
- Lazy locator query: `id`, `role`, `name`, `label`, or `xpath`

`AutomationCore` passes the query through as product semantics only. `AppiumMac2Adapter` remains the place where lookup, auto-wait, and backend-specific behavior live.

This keeps Phase 2 aligned with future recording/replay work, because recorded steps can store a stable query object rather than an ephemeral `e5` reference.

---

## Locator Model

### CLI Surface

Element actions continue to accept the current positional `ref`, but also accept a mutually composable locator parameter set:

- `--id`
- `--role`
- `--name`
- `--label`
- `--xpath`

Resolution rules:

1. If any explicit locator flags are present, build a lazy `LocatorQuery`
2. Otherwise, treat the positional argument as the existing `ref`
3. For commands that must support both source and target, each side gets its own query

### Supported Query Shapes

The initial structured model supports these stable combinations:

- `ref`
- `id`
- `role + name`
- `label`
- `xpath`

This deliberately does not add free-form boolean logic, predicate strings, or arbitrary mixed strategies in Phase 2.

### Adapter Resolution Strategy

Adapter lookup follows the PRD priority order:

1. `id`
2. `role + name`
3. `label`
4. `xpath`

If a query resolves to zero elements, return `ELEMENT_NOT_FOUND`.

If a query resolves to multiple elements in a context that needs exactly one target, return `ELEMENT_AMBIGUOUS` with lightweight candidate details.

Static refs keep current behavior, including stale detection.

---

## Auto-Wait Model

### Scope

Auto-wait applies to element mutations and direct interactions:

- `click`
- `right-click`
- `double-click`
- `type`
- `hover`
- `drag`

It does not apply to `inspect`, `find`, screenshots, or read-only assertions.

### Actionability Checks

Phase 2 implements the minimal set called out in the PRD:

- `visible`
- `enabled`
- `stable`

Definitions:

- `visible`: element has non-zero size and is not explicitly hidden via backend attributes
- `enabled`: backend does not report `enabled=false`
- `stable`: two consecutive samples of location and size match within the wait window

### Behavior

Each action resolves the target first, then polls until the target is actionable or the timeout expires.

On failure, return a structured `TIMEOUT` error with details that indicate which checks were still failing.

This replaces the product reason for most fixed sleeps without changing the existing configurable post-action delay knobs that were introduced in Phase 1.

---

## Assertions

### CLI Surface

Add a new `assert` command domain:

- `mac assert visible`
- `mac assert enabled`
- `mac assert text <expected>`
- `mac assert value <expected>`

Assertions use the same `LocatorQuery` flags as element actions, so deterministic scripts and future record/replay use one targeting model.

### Error Model

Assertion failures should not reuse generic `INVALID_ARGUMENT` or `ELEMENT_NOT_FOUND` when the element exists but the state is wrong.

Add a dedicated error code:

- `ASSERTION_FAILED`

This preserves product semantics and lets agents branch cleanly.

---

## Menu Click

### CLI Surface

Add:

- `mac menu click "File > Open"`

### Implementation Choice

Implement menu clicks with AppleScript instead of Appium tree traversal.

Reasons:

- Menu hierarchy is a macOS-native concern
- Appium menu discovery is already filtered as a special case in the adapter
- AppleScript is simpler and more stable for this narrow workflow

### Behavior

Parse the path on `>` separators, trim whitespace, and click the final item by traversing nested menu bars and submenus.

Invalid or empty paths return `INVALID_ARGUMENT`.

AppleScript execution failures return `WINDOW_NOT_FOUND` or `INTERNAL_ERROR` depending on whether the target structure is missing or execution itself fails.

---

## Coordinate Click

### CLI Surface

Add:

- `mac input click-at <x> <y>`

### Implementation Choice

Use AppleScript/System Events as the backend-facing implementation path.

This capability exists to cover non-accessible surfaces, so it should not depend on resolving a WebElement first.

### Behavior

Coordinates are absolute screen coordinates. Invalid numbers return `INVALID_ARGUMENT`. Failures to synthesize the event return `INTERNAL_ERROR`.

---

## Data Flow Changes

### New Shared Models

Add small product-level dataclasses in `models.py`:

- `LocatorQuery`
- `ActionabilityState`

These are transport-friendly and keep the CLI, daemon, core, and adapter using one shape.

### Routing

`cli.py` builds request payloads with locator fields.

`daemon.py` passes these fields through untouched and dispatches new `assert` and `menu` domains.

`core.py` reconstructs `LocatorQuery` instances, invokes adapter methods, and maps adapter results into response envelopes.

`appium_mac2.py` owns:

- query resolution
- actionability polling
- assertion evaluation
- AppleScript-backed menu and coordinate operations

---

## Testing Strategy

Phase 2 is implemented in two checkpoints.

### Checkpoint A

- Structured lazy locators
- Auto-wait for element interactions

Tests:

- CLI parsing and request mapping
- daemon dispatch coverage
- core happy/error paths
- adapter resolution and auto-wait behavior

### Checkpoint B

- assert domain
- menu clicks
- `input click-at`

Tests:

- CLI parsing and request mapping
- daemon dispatch coverage
- core response mapping
- adapter AppleScript and assertion behavior

The implementation stays test-first for each slice: add a failing test, run it, implement minimally, rerun, then broaden coverage.

---

## Non-Goals

- No codegen, replay, or trace viewer in this phase
- No full Playwright-style `receives events` or editable checks yet
- No new plugin system
- No Appium bypass or direct Accessibility API rewrite

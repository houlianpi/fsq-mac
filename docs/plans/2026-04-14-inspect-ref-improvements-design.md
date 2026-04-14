# Inspect & Ref Stabilization Patch Design

> Date: 2026-04-14
> Status: Draft
> Scope: Short-term stabilization patch, not the long-term inspect/ref contract

## Goal

Reduce the most immediate inspect/ref failure modes without introducing a misleading long-term contract.

This design is intentionally limited. It does not attempt to make Appium Mac2 refs behave like Playwright engine-guaranteed refs. It only makes the current system more honest, easier to recover from, and less likely to hide binding problems.

## Why This Is A Patch

QA found real problems in the current ref flow:

- alignment verification can silently report success even when all probes fail
- refs go stale between actions and the current error messages are too generic
- agents often need a fresh inspect after mutations, but forcing that into the core action contract would make every action heavier and blur success semantics

Those issues need short-term treatment, but the real fix requires a separate redesign of the inspect/ref/actionability contract.

This document therefore covers only a stabilization patch. The long-term contract work belongs in a separate design.

Update: the repository has already moved beyond this patch-only scope. Snapshot-oriented inspect payloads, richer action results, split failure semantics, and best-effort web-content signaling now live in the codebase. This document should now be read as historical patch rationale, not as the full current contract.

## Product Positioning For This Patch

- keep the current `inspect -> act -> inspect` workflow available
- improve error recovery signals for stale refs
- stop presenting heuristic ref binding as more trustworthy than it is
- avoid changing all action commands into implicit full-tree snapshot operations

## Change 1: Optional Best-Effort Auto Snapshot After Mutations

## Problem

After a mutating action, refs often become stale. Agents benefit from receiving a fresh element view, but a mandatory full `inspect()` after every successful action would add latency and can fail independently of the action itself.

## Design

Add a best-effort post-action snapshot path in `core.py`, but do not make it part of the success condition for the action itself.

- on successful mutating actions, the core may attempt `adapter.inspect()`
- if snapshot succeeds, attach it under `snapshot`
- always attach `snapshot_status`
- snapshot failure must not turn a successful action into a command failure

Initial `snapshot_status` values:

- `not_requested`
- `attached`
- `failed_best_effort`

This keeps the contract honest: the action succeeded or failed on its own merits, and snapshot attachment is a separate best-effort enrichment.

## Scope

Mutating actions that may attach a best-effort snapshot:

- `element_click`
- `element_right_click`
- `element_double_click`
- `element_type`
- `element_scroll`
- `element_drag`

Non-mutating actions that do not auto-attach snapshots:

- `element_hover`
- `element_inspect`
- `element_find`

## Response Shape

```json
{
  "ok": true,
  "command": "element.click",
  "data": {
    "x": 100,
    "y": 200,
    "snapshot_status": "attached",
    "snapshot": {
      "elements": [
        {"id": "e0", "role": "Button", "name": "Home", "ref_bound": true}
      ],
      "count": 1
    }
  }
}
```

If snapshot fails:

```json
{
  "ok": true,
  "command": "element.click",
  "data": {
    "x": 100,
    "y": 200,
    "snapshot_status": "failed_best_effort"
  }
}
```

## Change 2: Remove Misleading Alignment Verification And Surface Binding State

## Problem

The current `inspect()` flow parses XML and bulk-binds refs by document order. It then samples a subset of refs for verification. On some Edge Canary web content, all verification probes can error, yet the current code still reports successful alignment.

The immediate problem is not only weak verification. It is also that the system can imply stronger ref confidence than the backend can actually guarantee.

## Design

Keep the current bulk binding mechanism for now, but stop treating the current verification step as a reliable confidence signal.

- remove the existing sampling-based alignment verification block
- keep binding refs by document order index as the current heuristic
- explicitly expose whether an element received a bound ref
- do not imply that `ref_bound=true` means the ref is stable or guaranteed actionable

## Element Output Change

Add `ref_bound` to element payloads:

- `true`: this XML node was assigned a ref token during inspect
- `false`: this XML node is present in the snapshot but no ref token was assigned

This is only a binding-state field. It is not a reliability guarantee.

Example:

```json
{"id": "e0", "role": "Button", "name": "Home", "ref_bound": true}
{"role": "StaticText", "name": "Hello", "ref_bound": false}
```

## Fallback Guidance

For `ref_bound=false` elements, callers may still:

- re-run `element inspect`
- use locator-driven actions such as `--name` or `--role`
- use coordinate actions only as a best-effort fallback, especially in native app flows

This patch does not treat `click-at` as a universal recovery strategy for web content.

## Change 3: Improve Stale Ref Diagnostics

## Problem

Current stale-ref messages are too generic and do not help the caller decide whether to re-inspect, re-locate, or switch strategy.

## Design

Keep the top-level error code unchanged, but improve structured details and human-readable text.

- keep `error.code = ELEMENT_REFERENCE_STALE`
- keep `suggested_next_action = "mac element inspect"`
- include cached element identity when available
- add structured stale context under `error.details`

Suggested `error.details` fields:

- `ref`
- `cached_name`
- `cached_role`
- `reason`

Example detail message:

```text
Ref 'e5' (Submit, AXButton) is stale; UI changed since the last inspect
```

## Implementation Scope

- `src/fsq_mac/core.py`
  - add best-effort snapshot attachment helper
  - add `snapshot_status` to eligible action responses
- `src/fsq_mac/adapters/appium_mac2.py`
  - remove current inspect alignment verification block
  - emit `ref_bound`
  - improve stale-ref details
- `src/fsq_mac/models.py`
  - add `ref_bound` to `ElementInfo`

## Verification

1. Automated tests
   - successful mutating action can return `snapshot_status="attached"`
   - successful mutating action with inspect failure still returns `ok=true` and `snapshot_status="failed_best_effort"`
   - inspect results include `ref_bound`
   - stale ref errors include structured details when cached identity exists

2. Manual validation
   - Edge Canary inspect does not claim successful alignment when verification probes fail
   - stale refs are easier to diagnose and recover from
   - post-action responses remain usable even when follow-up inspect is slow or fails

## Out Of Scope

- redesigning the inspect payload into a formal snapshot contract
- defining `ref_status` beyond `ref_bound`
- full actionability redesign
- browser-native backend work
- guaranteeing stable refs for complex web content

## Next Step

After this patch, the repository should move to a dedicated contract redesign for `inspect/ref/actionability`. That design, not this patch, should define the long-term product semantics.

That next-step work has now started landing incrementally. The authoritative contract direction is captured in [docs/plans/2026-04-14-inspect-ref-actionability-contract-design.md](docs/plans/2026-04-14-inspect-ref-actionability-contract-design.md).

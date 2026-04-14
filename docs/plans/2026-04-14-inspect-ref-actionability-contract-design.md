# Inspect / Ref / Actionability Contract Redesign

> Date: 2026-04-14
> Status: Draft
> Scope: Product-contract redesign for inspect, ref lifecycle, and actionability semantics

## Goal

Define a stable, machine-consumable contract for how `fsq-mac` exposes inspected elements, ref lifecycle, actionability checks, action results, and recovery guidance.

The purpose of this redesign is not to pretend Appium Mac2 can provide Playwright-grade guarantees on all web content. The purpose is to make the product contract honest, stable, and extensible across backends.

## Why A Contract Redesign Is Needed

The current system mixes product semantics with backend-specific behavior:

- `inspect()` behaves like both a debug dump and a working element snapshot
- ref tokens such as `e5` look stable, but are actually generation-bound and backend-limited
- actionability checks partially depend on slow or unreliable backend RPCs
- errors do not clearly distinguish stale refs, unbound refs, bad geometry, backend timeouts, and web-content limitations

As a result, upstream agents cannot reliably decide what is safe to trust, when to retry, and when to switch strategy.

## Design Principles

- only expose guarantees the backend can actually support
- separate binding state from reliability state
- make every action result explain what evidence was used
- keep the top-level CLI contract backend-neutral where possible
- allow stronger backends later without breaking the CLI shape

## Contract Overview

The redesigned contract has five parts:

1. snapshot contract
2. ref lifecycle contract
3. actionability contract
4. action result contract
5. error and recovery contract

## 1. Snapshot Contract

`inspect` should be treated as a structured snapshot, not only as a debug listing.

### Top-Level Snapshot Fields

Suggested shape:

```json
{
  "snapshot_id": "snap_20260414_001",
  "generation": 12,
  "backend": "appium_mac2",
  "binding_mode": "heuristic",
  "binding_warnings": [
    {
      "code": "WEB_CONTENT_BEST_EFFORT",
      "count": 1,
      "message": "Web content is exposed through accessibility and remains best effort under the current backend."
    }
  ],
  "elements": [...],
  "count": 200
}
```

### Element Fields

Each element should expose stable product fields, even if the data source varies by backend:

- `ref`
- `role`
- `name`
- `label`
- `value`
- `element_bounds`
- `center`
- `visible`
- `enabled`
- `ref_status`
- `state_source`

### Field Semantics

- `element_bounds`: normalized geometry object with `x`, `y`, `width`, `height`
- `center`: normalized interaction point derived from bounds when available
- `ref_status`: lifecycle-oriented status, not just “did we assign an id”
- `state_source`: where visibility/enabled/geometry came from

Initial `state_source` values:

- `xml`
- `rpc`
- `mixed`
- `unknown`

Initial `binding_mode` values:

- `engine_guaranteed`
- `heuristic`
- `unbound_only`

Current Appium Mac2 implementation status:

- `backend` is emitted today
- `binding_mode` is emitted today
- `binding_warnings` is emitted today
- current warning codes include `UNBOUND_ELEMENTS_PRESENT` and `WEB_CONTENT_BEST_EFFORT`

## 2. Ref Lifecycle Contract

Refs must stop behaving like implied stable handles.

### Ref Model

A ref token is:

- issued from a specific snapshot generation
- valid only within backend-specific limits
- allowed to become stale after UI change
- recoverable only through defined strategies

### Ref Status

Recommended values:

- `bound`
- `heuristic`
- `unbound`
- `stale`

Meaning:

- `bound`: backend assigned a ref and considers it usable within current generation limits
- `heuristic`: backend assigned a ref through weaker matching or inference
- `unbound`: element is visible in the snapshot but no actionable ref exists
- `stale`: previously issued ref no longer maps to a current actionable element

`bound` is stronger than today's `ref_bound=true`, but still not equivalent to Playwright locator stability unless the backend declares stronger capabilities.

## 3. Actionability Contract

Actionability must be based only on evidence the backend can actually prove.

### What Actionability Answers

Before `click`, `type`, `drag`, or similar operations, the backend should report whether the target is actionable enough for the requested operation.

### Initial Actionability Fields

Suggested shape:

```json
{
  "actionable": true,
  "reason": null,
  "checks": {
    "has_ref": true,
    "has_geometry": true,
    "visible": true,
    "enabled": true
  },
  "evidence_source": "xml"
}
```

### Rules

- do not add slow RPC probes only to simulate stronger guarantees
- do not infer “clickable” from geometry alone when the backend cannot prove hit-target correctness
- use the same contract for both pre-action checks and failure reporting

This means `fsq-mac` should not try to fully mimic Playwright actionability on top of Mac2. It should provide a narrower but honest actionability contract.

## 4. Action Result Contract

Action responses should explain both the operation result and the confidence/context around it.

### Suggested Fields

- `target_ref`
- `resolved_element`
- `actionability_used`
- `element_bounds`
- `center`
- `snapshot_status`
- optional `snapshot`

Example:

```json
{
  "ok": true,
  "command": "element.click",
  "data": {
    "target_ref": "e5",
    "resolved_element": {
      "role": "AXButton",
      "name": "Submit",
      "ref_status": "heuristic"
    },
    "actionability_used": {
      "actionable": true,
      "evidence_source": "xml"
    },
    "element_bounds": {"x": 100, "y": 200, "width": 50, "height": 20},
    "center": {"x": 125, "y": 210},
    "snapshot_status": "attached"
  }
}
```

This lets upstream tools decide whether to continue, refresh, or switch strategy.

## 5. Error And Recovery Contract

Errors should tell the caller what failed and what recovery path is appropriate.

### Priority Error Codes For This Redesign

- `ELEMENT_REFERENCE_STALE`
- `ELEMENT_UNBOUND`
- `ELEMENT_NOT_ACTIONABLE`
- `GEOMETRY_UNRELIABLE`
- `BACKEND_RPC_TIMEOUT`
- `WEB_CONTENT_UNRELIABLE`

### Recovery Semantics

- `ELEMENT_REFERENCE_STALE`: refresh snapshot or re-locate
- `ELEMENT_UNBOUND`: use locator-based action or different backend
- `ELEMENT_NOT_ACTIONABLE`: wait, re-inspect, or change target
- `GEOMETRY_UNRELIABLE`: avoid coordinate fallback unless native-app context is acceptable
- `BACKEND_RPC_TIMEOUT`: retry or degrade to lower-confidence strategy if allowed
- `WEB_CONTENT_UNRELIABLE`: treat as backend boundary, not a normal transient failure

### Structured Error Details

Suggested detail fields:

- `ref`
- `snapshot_id`
- `cached_name`
- `cached_role`
- `state_source`
- `reason`
- `recovery_hint`
- `web_best_effort`

Current Appium Mac2 implementation status:

- `ELEMENT_NOT_ACTIONABLE`, `GEOMETRY_UNRELIABLE`, and `BACKEND_RPC_TIMEOUT` already carry structured `details`
- web-content-related failures may carry `web_best_effort=true`
- this is advisory contract metadata, not a separate hard-failure mode yet

## Capability Model Link

This contract is designed to work with multiple backends.

Backends should eventually declare capabilities such as:

- `stable_refs`
- `accurate_element_bounds`
- `native_text_input`
- `web_semantics`
- `network_control`

The contract stays stable, but stronger backends can populate stronger `binding_mode`, `ref_status`, and `state_source` values.

## Initial Implementation Slice

The first implementation should stay narrow. Recommended first slice:

1. add normalized `element_bounds` and `center`
2. add `ref_status`
3. add `snapshot_status` to action responses
4. split stale vs unbound vs backend-timeout error paths more clearly

Do not attempt a full backend rewrite in the first slice.

## Out Of Scope

- browser-native backend implementation
- full command-tree redesign
- DOM-level guarantees for web content under Mac2
- network/storage/devtools web features

## Success Criteria

- upstream agents can distinguish trustworthy refs from weak refs
- action responses say what evidence was used
- failures become recoverable through stable error semantics instead of message parsing
- the contract can later be implemented by both Mac2 and a browser-native backend without changing the CLI shape

## Current Implementation Notes

As of the current Appium Mac2 slice, the contract is partially implemented:

- `element inspect` returns snapshot-oriented top-level fields
- element payloads include `ref`, `element_bounds`, `center`, `ref_status`, and `state_source`
- successful element actions can return `resolved_element`, `resolved_target`, `actionability_used`, and best-effort `snapshot`
- snapshot warnings explicitly mark unbound snapshots and web-content best-effort situations
- failure details explicitly distinguish stale refs, unbound refs, non-actionable elements, unreliable geometry, and backend RPC timeouts

The remaining gap is not basic contract shape. The remaining gap is backend strength, especially for complex web content.

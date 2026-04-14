# CLI Reference

All commands follow the pattern: `mac <domain> <action> [args] [flags]`

Global flags available on all commands:
- `--pretty` — human-readable output (default: JSON)
- `--session <session-id>` — target a specific session
- `--verbose` / `--debug` — logging verbosity
- `--strategy <strategy>` — element locator strategy (default: accessibility_id)
- `--timeout <ms>` — command timeout in milliseconds (default: 120000)
- `--allow-dangerous` — required for DANGEROUS commands

All commands return JSON by default. Use `--pretty` for human-readable formatting.

Machine-readable contract source of truth: `docs/agent-contract.json`.

## Exit codes

- `0` — command succeeded (`ok: true`)
- `1` — command failed (`ok: false`)

## Error handling

All commands return a stable top-level JSON envelope. On failure, the CLI keeps the same envelope shape and populates `error` with machine-consumable fields:

> **Exception:** `trace codegen` on success prints the generated shell script as raw text (or `Script written to <path>` when `--output` is used) instead of the JSON envelope. On failure it still returns the standard envelope.

- `code`
- `message`
- `retryable`
- `details`
- `suggested_next_action`
- `doctor_hint`

Example failure response:

```json
{
  "ok": false,
  "command": "element.find",
  "session_id": "s1",
  "data": null,
  "error": {
    "code": "ELEMENT_NOT_FOUND",
    "message": "Element 'Submit' not found",
    "retryable": true,
    "details": {},
    "suggested_next_action": "mac element inspect",
    "doctor_hint": null
  },
  "meta": {
    "backend": "appium_mac2",
    "duration_ms": 42,
    "timestamp": "2026-04-13T00:00:00Z",
    "frontmost_app": "com.apple.Safari",
    "frontmost_window": "Example"
  }
}
```

Recommended consumer interpretation:

- use `error.code` for control flow, not regexes over `message`
- use `error.retryable` as the primary retry hint
- use `suggested_next_action` and `doctor_hint` as operator guidance, not as required fields
- use `docs/agent-playbook.md` for recommended retry and recovery flows

### Error codes

Codes marked **emitted** are returned by current runtime code paths. Codes marked **reserved** are defined in the enum for forward compatibility but not yet emitted by any code path; agents should not branch on reserved codes until a future release begins emitting them.

| Code | Retryable | Status | Description |
|------|-----------|--------|-------------|
| `SESSION_NOT_FOUND` | no | emitted | No active session matches the requested ID |
| `SESSION_EXPIRED` | no | reserved | Session timed out or was cleaned up |
| `SESSION_CONFLICT` | yes | emitted | Another session is already active; end it first |
| `BACKEND_UNAVAILABLE` | yes | emitted | Appium server is not reachable; run `mac doctor backend` |
| `APP_NOT_FOUND` | no | reserved | Bundle ID not found among running applications |
| `WINDOW_NOT_FOUND` | yes | emitted | Target window not found; it may still be loading |
| `ELEMENT_NOT_FOUND` | yes | emitted | No element matches the locator; re-inspect and retry |
| `ELEMENT_AMBIGUOUS` | no | emitted | Multiple elements match; narrow the locator |
| `ELEMENT_REFERENCE_STALE` | yes | emitted | Ref was invalidated by a mutation; re-inspect |
| `ELEMENT_UNBOUND` | no | emitted | Element is visible but was not bound to a driver handle |
| `ELEMENT_NOT_ACTIONABLE` | no | emitted | Element failed actionability checks (not visible or not enabled) |
| `GEOMETRY_UNRELIABLE` | no | emitted | Element bounds are degenerate or zero-area |
| `PERMISSION_DENIED` | no | reserved | Accessibility permission not granted |
| `ACTION_BLOCKED` | no | emitted | Safety classification blocks this action; use `--allow-dangerous` |
| `INVALID_ARGUMENT` | no | emitted | Invalid argument supplied to command |
| `ASSERTION_FAILED` | no | emitted | An assert command's condition was not met |
| `TRACE_STEP_NOT_REPLAYABLE` | no | emitted | Trace step cannot be replayed (missing locator or unsupported action) |
| `TYPE_VERIFICATION_FAILED` | no | emitted | Typed text did not match expected value after verification |
| `BACKEND_RPC_TIMEOUT` | yes | emitted | Driver operation timed out; retry or refresh snapshot |
| `TIMEOUT` | yes | emitted | Command exceeded its timeout; increase `--timeout` or retry |
| `INTERNAL_ERROR` | no | emitted | Unexpected internal error |

For element commands, `error.details` may also include:

- `state_source`
- `checks`
- `element_bounds`
- `recovery_hint`
- `web_best_effort`

`web_best_effort=true` means the current backend is operating on browser web content through accessibility and the failure should be treated as best-effort backend behavior, not as a DOM-native guarantee regression.

## session

| Command | Description | Safety |
|---------|-------------|--------|
| `mac session start` | Start a new automation session | SAFE |
| `mac session get` | Get current session info | SAFE |
| `mac session list` | List all active sessions | SAFE |
| `mac session end` | End the current session | SAFE |

```bash
mac session start
mac session list --pretty
mac session end
```

## app

| Command | Description | Safety |
|---------|-------------|--------|
| `mac app launch <bundle_id>` | Launch an application | GUARDED |
| `mac app activate <bundle_id>` | Activate (bring to front) an application | GUARDED |
| `mac app list` | List running applications | SAFE |
| `mac app current` | Get frontmost application info | SAFE |
| `mac app terminate <bundle_id> --allow-dangerous` | Terminate an application | DANGEROUS |

```bash
mac app launch com.apple.calculator
mac app activate com.apple.Safari
mac app list --pretty
mac app current
mac app terminate com.apple.calculator --allow-dangerous
```

## window

| Command | Description | Safety |
|---------|-------------|--------|
| `mac window current` | Get frontmost window info | SAFE |
| `mac window list` | List all windows | SAFE |
| `mac window focus <index>` | Focus a window by index | GUARDED |

```bash
mac window current
mac window list --pretty
mac window focus 0
```

## element

All element commands accept locator flags: `--id`, `--role`, `--name`, `--label`, `--xpath`

`mac element inspect` returns a structured snapshot, not only a flat debug listing. Important top-level fields include:

- `snapshot_id`
- `generation`
- `backend`
- `binding_mode`
- `binding_warnings`
- `elements`
- `count`

Current `binding_mode` meanings:

- `bound` — every parsed element received a bound ref under the current accessibility-based backend heuristic
- `heuristic` — some parsed elements were bound and some remained unbound
- `unbound_only` — the snapshot contains visible elements but no actionable refs were bound

Current `binding_warnings` may include:

- `UNBOUND_ELEMENTS_PRESENT`
- `WEB_CONTENT_BEST_EFFORT`

| Command | Description | Safety |
|---------|-------------|--------|
| `mac element inspect` | Inspect all visible elements | SAFE |
| `mac element find` | Find elements matching locator | SAFE |

`element find` accepts locator flags and an optional `--first-match` flag to return only the first match.

| `mac element click` | Click an element | GUARDED |
| `mac element right-click` | Right-click an element | GUARDED |
| `mac element double-click` | Double-click an element | GUARDED |
| `mac element type <text>` | Type text into an element | GUARDED |
| `mac element scroll <dir>` | Scroll an element | GUARDED |
| `mac element hover` | Hover over an element | GUARDED |
| `mac element drag` | Drag an element | GUARDED |

```bash
mac element inspect --pretty
mac element find --role AXButton
mac element find --role AXButton --first-match
mac element click --role AXButton --name OK
mac element click e0
mac element type "hello world" --role AXTextField
mac element type e3 "hello world"
mac element type "hello world" --role AXTextField --input-method keys
mac element scroll down --role AXScrollArea
mac element right-click --name "File"
```

Example inspect response shape:

```json
{
  "ok": true,
  "command": "element.inspect",
  "data": {
    "snapshot_id": "snap_12",
    "generation": 12,
    "backend": "appium_mac2",
    "binding_mode": "bound",
    "binding_warnings": [
      {
        "code": "WEB_CONTENT_BEST_EFFORT",
        "count": 1,
        "message": "Web content is exposed through accessibility and remains best effort under the current backend."
      }
    ],
    "elements": [
      {
        "element_id": "e0",
        "role": "WebArea",
        "name": "Docs",
        "element_bounds": {"x": 0, "y": 0, "width": 1280, "height": 720},
        "center": {"x": 640, "y": 360},
        "ref_bound": true,
        "ref_status": "bound",
        "state_source": "xml"
      }
    ],
    "count": 1
  }
}
```

Example element action success shape:

```json
{
  "ok": true,
  "command": "element.click",
  "data": {
    "resolved_element": {
      "ref": "e0",
      "role": "AXButton",
      "name": "OK",
      "ref_status": "bound",
      "state_source": "xml",
      "element_bounds": {"x": 10, "y": 20, "width": 80, "height": 40},
      "center": {"x": 50, "y": 40}
    },
    "actionability_used": {
      "actionable": true,
      "checks": {
        "has_ref": true,
        "has_geometry": true,
        "visible": true,
        "enabled": true
      },
      "evidence_source": "xml"
    },
    "element_bounds": {"x": 10, "y": 20, "width": 80, "height": 40},
    "center": {"x": 50, "y": 40},
    "snapshot_status": "attached",
    "snapshot": {
      "snapshot_id": "snap_13",
      "generation": 13,
      "backend": "appium_mac2",
      "binding_mode": "bound",
      "binding_warnings": [],
      "elements": [
        {
          "element_id": "e0",
          "role": "Button",
          "name": "OK",
          "ref_bound": true,
          "ref_status": "bound",
          "state_source": "xml"
        }
      ],
      "count": 1
    }
  }
}
```

Successful mutating element actions may return additional machine-consumable fields:

- `resolved_element`
- `resolved_target`
- `actionability_used`
- `element_bounds`
- `center`
- `snapshot_status`
- `snapshot`
- `target_bounds` and `target_center` on drag success

Text-writing commands support `--input-method paste|keys|auto`.

- `paste` is the default and inserts final text via clipboard plus paste hotkey
- `keys` preserves synthetic key injection for flows that need key-event semantics
- `auto` currently behaves the same as `paste`

Example structured error shapes:

```json
{
  "ok": false,
  "command": "element.click",
  "error": {
    "code": "ELEMENT_UNBOUND",
    "message": "Ref 'e5' is visible in the current snapshot but was not bound to an actionable element handle",
    "details": {
      "ref": "e5",
      "reason": "snapshot_unbound"
    },
    "suggested_next_action": "mac element inspect"
  }
}
```

```json
{
  "ok": false,
  "command": "element.click",
  "error": {
    "code": "BACKEND_RPC_TIMEOUT",
    "message": "Timed out while probing element state: Driver operation timed out after 0.5s",
    "details": {
      "state_source": "rpc",
      "checks": {"rpc_probe": "timed_out"},
      "recovery_hint": "Retry the action or refresh the UI snapshot if the backend remains slow."
    },
    "suggested_next_action": "Retry the action or refresh with 'mac element inspect'"
  }
}
```

```json
{
  "ok": false,
  "command": "element.click",
  "error": {
    "code": "GEOMETRY_UNRELIABLE",
    "message": "click-at failed",
    "details": {
      "ref": "e0",
      "state_source": "xml",
      "checks": {"has_geometry": false},
      "element_bounds": {"x": 0, "y": 0, "width": 1, "height": 1},
      "recovery_hint": "Refresh the snapshot and avoid coordinate fallback for this element until stable bounds are available.",
      "web_best_effort": true
    },
    "suggested_next_action": "mac element inspect"
  }
}
```

## input

| Command | Description | Safety |
|---------|-------------|--------|
| `mac input key <key>` | Press a single key | GUARDED |
| `mac input hotkey <combo>` | Press a key combination | GUARDED |
| `mac input text <text>` | Type text (no element target) | GUARDED |
| `mac input click-at <x> <y>` | Click at screen coordinates | GUARDED |

```bash
mac input key Return
mac input hotkey cmd+c
mac input text "hello world"
mac input text "hello world" --input-method keys
mac input click-at 100 200
```

## assert

All assert commands accept locator flags: `--id`, `--role`, `--name`, `--label`, `--xpath`

| Command | Description | Safety |
|---------|-------------|--------|
| `mac assert visible` | Assert element is visible | SAFE |
| `mac assert enabled` | Assert element is enabled | SAFE |
| `mac assert text <text>` | Assert element text matches | SAFE |
| `mac assert value <value>` | Assert element value matches | SAFE |
| `mac assert app-running <bundle_id>` | Assert application is running | SAFE |
| `mac assert app-frontmost <bundle_id>` | Assert application is frontmost | SAFE |

```bash
mac assert visible --role AXButton --name OK
mac assert enabled --role AXTextField
mac assert text "Hello" --role AXStaticText
mac assert value "42" --role AXTextField
mac assert app-running com.apple.Safari
mac assert app-frontmost com.apple.Safari
```

## menu

| Command | Description | Safety |
|---------|-------------|--------|
| `mac menu click <path>` | Click a menu item by path | GUARDED |

```bash
mac menu click "File > Open"
mac menu click "Edit > Copy"
```

## trace

| Command | Description | Safety |
|---------|-------------|--------|
| `mac trace start [path]` | Start recording a trace | SAFE |
| `mac trace stop` | Stop the active trace | SAFE |
| `mac trace status` | Show active trace status | SAFE |
| `mac trace replay <path>` | Replay a saved trace | GUARDED |
| `mac trace viewer <path>` | Generate HTML viewer for a trace | SAFE |
| `mac trace codegen <path> [--output file]` | Generate shell script from trace | SAFE |

```bash
mac trace start
mac trace stop
mac trace status
mac trace replay artifacts/traces/20250101-120000
mac trace viewer artifacts/traces/20250101-120000
mac trace codegen artifacts/traces/20250101-120000
mac trace codegen artifacts/traces/20250101-120000 --output script.sh
```

## capture

| Command | Description | Safety |
|---------|-------------|--------|
| `mac capture screenshot [path]` | Take a screenshot | SAFE |
| `mac capture ui-tree` | Get UI element tree as XML | SAFE |

Flags for screenshot:
- `--element <ref>` — screenshot a specific element (e.g., `e0`)
- `--rect <x,y,w,h>` — screenshot a region

```bash
mac capture screenshot ./screenshot.png
mac capture screenshot --element e0
mac capture screenshot --rect 0,0,400,300
mac capture ui-tree
```

## wait

| Command | Description | Safety |
|---------|-------------|--------|
| `mac wait element <locator>` | Wait for element to appear | SAFE |
| `mac wait window <title>` | Wait for window to appear | SAFE |
| `mac wait app <bundle_id>` | Wait for application to start | SAFE |

All wait commands accept `--timeout <ms>` (default: 10000) and `--strategy <strategy>`.

For app-level verification, use these semantics:

- `mac wait app <bundle_id>` is the canonical running-verification primitive when you want to assert that an app becomes available within a timeout window
- `mac assert app-running <bundle_id>` is the immediate assertion form for "this app should already be running"
- `mac assert app-frontmost <bundle_id>` is the immediate assertion form for "this app should already be frontmost"
- `mac app current` and `mac app list` remain stable structured query surfaces when the calling framework wants to implement its own logic

```bash
mac wait element "OK" --timeout 5000
mac wait window "Main Window"
mac wait app com.apple.calculator
```

## doctor

| Command | Description | Safety |
|---------|-------------|--------|
| `mac doctor` | Run all environment checks | SAFE |
| `mac doctor permissions` | Check Accessibility permissions | SAFE |
| `mac doctor backend` | Check Appium server and Mac2 driver | SAFE |
| `mac doctor plugins` | List discovered plugins | SAFE |

```bash
mac doctor
mac doctor permissions
mac doctor backend
mac doctor plugins
```

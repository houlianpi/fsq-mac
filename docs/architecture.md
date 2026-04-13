# Architecture

fsq-mac uses a daemon/client architecture where the CLI communicates over HTTP with a persistent daemon process that drives Appium Mac2.

## Request flow

```
CLI (cli.py)
  -> DaemonClient (client.py)
    -> HTTP POST /api/{domain}/{action}
      -> Starlette daemon (daemon.py)
        -> AutomationCore (core.py)
          -> SessionManager (session.py)
            -> AppiumMac2Adapter (adapters/appium_mac2.py)
              -> Appium WebDriver -> macOS Accessibility API
```

## Module responsibilities

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Argparse CLI entry point, translates args to HTTP calls |
| `client.py` | HTTP client, auto-starts daemon if not running |
| `daemon.py` | Starlette/Uvicorn HTTP server, request routing, trace artifact capture |
| `core.py` | Product semantics layer, safety checks, response envelope |
| `session.py` | Multi-session lifecycle management |
| `adapters/appium_mac2.py` | Appium Mac2 WebDriver adapter |
| `adapters/__init__.py` | Adapter registry, plugin discovery via entry points |
| `models.py` | Data models (ErrorCode, Response, TraceRun, TraceStep, etc.) |
| `formatters.py` | Output formatting (JSON, pretty, table) |
| `trace.py` | Trace recording, replay, viewer generation |
| `codegen.py` | Trace-to-shell-script code generation |
| `doctor.py` | Environment diagnostics (Accessibility, Appium, Xcode) |

## Daemon lifecycle

- **Auto-start**: The daemon starts automatically on the first CLI call if not already running.
- **State directory**: `~/.fsq-mac/` stores PID file, port file, and configuration.
- **Idle timeout**: The daemon auto-exits after 30 minutes of inactivity.
- **Port**: Default `19444`, stored in `~/.fsq-mac/port`.

## Session lifecycle

```
session start -> creates adapter -> connects to Appium
  |
element inspect / click / type ... (adapter calls)
  |
session end -> disconnects adapter -> cleans up state
```

- Multiple sessions can be active simultaneously.
- Each session has a unique ID and its own adapter instance.
- Sessions track frontmost app/window metadata.

## Adapter protocol

Adapters implement a set of methods for automation:

- **Lifecycle**: `connect()`, `disconnect()`, `connected`
- **App**: `app_launch()`, `app_activate()`, `app_terminate()`, `app_current()`, `app_list()`
- **Element**: `inspect()`, `find()`, `click()`, `type_text()`, `scroll()`, `drag()`
- **Input**: `key()`, `hotkey()`, `text()`, `click_at()`
- **Window**: `window_current()`, `window_list()`, `window_focus()`
- **Assert**: `assert_visible()`, `assert_enabled()`, `assert_text()`, `assert_value()`
- **Capture**: `screenshot()`, `ui_tree()`

The adapter registry (`adapters/__init__.py`) maps backend names to factory callables. Third-party adapters can register via Python entry points.

## Safety classification

Every command has a safety level:

| Level | Behavior | Examples |
|-------|----------|----------|
| **SAFE** | Always allowed | `element inspect`, `app list`, `session start` |
| **GUARDED** | Allowed by default, logged | `element click`, `app launch`, `input key` |
| **DANGEROUS** | Requires `--allow-dangerous` flag | `app terminate` |

Safety is checked in `core.py:check_safety()` before dispatch.

## Trace system

The trace system records, replays, and exports automation workflows:

1. **Recording**: `trace start` begins capturing steps. Each CLI command during recording is logged as a `TraceStep` with before/after screenshots and UI tree snapshots.
2. **Replay**: `trace replay` re-executes recorded steps through the adapter.
3. **Viewer**: `trace viewer` generates a static HTML report with step details and tree diffs.
4. **Codegen**: `trace codegen` converts a trace to a runnable bash script.

Trace data is stored as JSON manifests (`trace.json`) with artifacts in a `steps/` subdirectory.

## Response envelope

Every API response follows a consistent structure:

```json
{
  "ok": true,
  "command": "element.click",
  "session_id": "...",
  "data": { ... },
  "error": {
    "code": "ELEMENT_NOT_FOUND",
    "message": "...",
    "retryable": true,
    "details": {},
    "suggested_next_action": "mac element inspect",
    "doctor_hint": null
  },
  "meta": {
    "backend": "appium_mac2",
    "duration_ms": 42,
    "timestamp": "...",
    "frontmost_app": "...",
    "frontmost_window": "..."
  }
}
```

For non-zero command failures, the CLI keeps the same top-level envelope shape and returns a populated `error` object with these machine-consumable fields:

- `error.code`
- `error.message`
- `error.retryable`
- `error.details`
- `error.suggested_next_action`
- `error.doctor_hint`

Consumers should treat this JSON structure as the stable failure contract for CLI and daemon responses.

## Error taxonomy

`fsq-mac` exposes a stable top-level error code taxonomy through `models.py:ErrorCode`.

Common codes and their intended meaning:

| Code | Category | Meaning | Retryable |
|------|----------|---------|-----------|
| `SESSION_NOT_FOUND` | precondition | No active session exists for a command that requires one | usually no |
| `SESSION_CONFLICT` | precondition | Session state conflict that may be recoverable by retrying or choosing a different session | yes |
| `BACKEND_UNAVAILABLE` | environment/backend | Appium server, Mac2 driver, or backend connectivity is unavailable | yes |
| `WINDOW_NOT_FOUND` | observation | The requested window could not be found | yes |
| `ELEMENT_NOT_FOUND` | observation | The requested element could not be found | yes |
| `ELEMENT_REFERENCE_STALE` | observation | A previously returned element ref is no longer valid | yes |
| `ACTION_BLOCKED` | safety/precondition | The command is blocked by an explicit safety requirement | no |
| `INVALID_ARGUMENT` | caller/input | The command arguments are invalid | no |
| `ASSERTION_FAILED` | assertion | The target element exists, but the asserted state/value is wrong | no |
| `TIMEOUT` | timing/environment | The target state did not become true before the timeout | yes |
| `INTERNAL_ERROR` | runtime/internal | The backend or runtime hit an unexpected failure | no |

Other `ErrorCode` values may appear for narrower situations, but consumers should prefer `error.code` over parsing free-form text.

## Retryable semantics

`error.retryable` is derived from the top-level error code, not from the message text.

Current retryable set:

- `SESSION_CONFLICT`
- `BACKEND_UNAVAILABLE`
- `WINDOW_NOT_FOUND`
- `ELEMENT_NOT_FOUND`
- `ELEMENT_REFERENCE_STALE`
- `TIMEOUT`

Treat `error.retryable` as the intended orchestration signal for whether a retry or refresh strategy is usually reasonable. It is a product-level hint, not a guarantee that retrying will succeed in every environment.

## Performance optimization

The adapter includes a page source cache (`_get_page_source()`) to reduce redundant XML fetches:

- Cached within a configurable TTL (default 2 seconds).
- Automatically invalidated after mutation commands (click, type, scroll, etc.).
- Disabled by setting `tree_cache_ttl: 0` in config.

## Plugin system

Adapters and doctor checks can be extended via Python entry points:

- **`fsq_mac.adapters`**: Register custom automation backends.
- **`fsq_mac.doctor`**: Register custom environment checks.

See [Plugin Development](plugins.md) for details.

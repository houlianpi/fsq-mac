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
    "retryable": false,
    "suggested_next_action": "mac element inspect"
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

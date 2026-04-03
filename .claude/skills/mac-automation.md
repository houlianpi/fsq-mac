# macOS Automation with fsq-mac

Use when the user asks to automate, interact with, test, or control a macOS native application. Triggers: mac automation, click button, UI testing, accessibility, element inspect, screenshot, app launch, macOS app, native app automation.

## Prerequisites

- Appium server running (`appium` in a terminal)
- Mac2 driver installed (`appium driver install mac2`)
- macOS Accessibility permissions granted
- Run `mac doctor` to verify setup

## Core Workflow

Every automation session follows this pattern:

1. **Start session** — `mac session start`
2. **Launch/activate app** — `mac app launch <bundle_id>`
3. **Inspect UI** — `mac element inspect` to discover elements
4. **Act** — click, type, scroll, etc. using element refs (e0, e1, ...)
5. **Verify** — `mac capture screenshot` or re-inspect to confirm result
6. **End session** — `mac session end`

## Command Reference

### Session
| Command | Description |
|---------|-------------|
| `mac session start` | Start a new automation session |
| `mac session get` | Get current session info |
| `mac session list` | List all sessions |
| `mac session end` | End current session |

### Application
| Command | Description |
|---------|-------------|
| `mac app launch <bundle_id>` | Launch app (e.g. `com.apple.calculator`) |
| `mac app activate <bundle_id>` | Bring app to front |
| `mac app current` | Get frontmost app info |
| `mac app list` | List running apps |
| `mac app terminate <bundle_id>` | Terminate app (requires `--allow-dangerous`) |

### Element
| Command | Description |
|---------|-------------|
| `mac element inspect` | List all visible UI elements with refs (e0, e1, ...) |
| `mac element find <locator>` | Find element by locator value |
| `mac element click <ref>` | Click element (e.g. `e5`) |
| `mac element right-click <ref>` | Right-click element |
| `mac element double-click <ref>` | Double-click element |
| `mac element type <ref> <text>` | Type text into element |
| `mac element scroll <ref> [up|down|left|right]` | Scroll element |
| `mac element hover <ref>` | Hover over element |
| `mac element drag <source> <target>` | Drag from source to target element |

### Input (no element target)
| Command | Description |
|---------|-------------|
| `mac input key <key>` | Press key (return, space, tab, escape, etc.) |
| `mac input hotkey <combo>` | Key combo (e.g. `command+c`, `command+shift+s`) |
| `mac input text <text>` | Type text to focused element |

### Capture
| Command | Description |
|---------|-------------|
| `mac capture screenshot [path]` | Take screenshot (default: ./screenshot.png) |
| `mac capture screenshot --element <ref> [path]` | Screenshot a specific element |
| `mac capture screenshot --rect x,y,w,h [path]` | Screenshot a region |
| `mac capture ui-tree` | Get raw UI element tree (XML) |

### Window
| Command | Description |
|---------|-------------|
| `mac window current` | Get frontmost window info |
| `mac window list` | List windows of managed app |
| `mac window focus <index>` | Focus window by index |

### Wait
| Command | Description |
|---------|-------------|
| `mac wait element <locator>` | Wait for element to appear |
| `mac wait window <title>` | Wait for window to appear |
| `mac wait app <bundle_id>` | Wait for app to start |

### Doctor
| Command | Description |
|---------|-------------|
| `mac doctor` | Run all diagnostics |
| `mac doctor permissions` | Check Accessibility permissions |
| `mac doctor backend` | Check Appium server and Mac2 driver |

## Global Options

| Option | Description |
|--------|-------------|
| `--session <id>` | Target a specific session (default: most recent) |
| `--strategy <strategy>` | Locator strategy: accessibility_id, name, xpath, class_name, ios_predicate |
| `--timeout <ms>` | Timeout in milliseconds (default: 120000) |
| `--pretty` | Human-friendly output (default: compact JSON for agents) |
| `--allow-dangerous` | Allow dangerous operations (e.g. app terminate) |
| `--version` | Show version |

## Response Format

Every command returns a JSON envelope:

```json
{
  "ok": true,
  "command": "element.click",
  "session_id": "s1",
  "data": {},
  "error": null,
  "meta": {
    "backend": "appium_mac2",
    "duration_ms": 1234,
    "timestamp": "2026-04-03T10:00:00Z",
    "frontmost_app": "com.apple.calculator",
    "frontmost_window": "Calculator"
  }
}
```

On error:

```json
{
  "ok": false,
  "command": "element.click",
  "error": {
    "code": "ELEMENT_NOT_FOUND",
    "message": "Element 'e5' not found",
    "retryable": true,
    "suggested_next_action": "mac element inspect",
    "doctor_hint": null
  }
}
```

## Error Recovery

When a command fails, check `error.code` and follow this recovery strategy:

| Error Code | Recovery |
|------------|----------|
| `SESSION_NOT_FOUND` | Run `mac session start` |
| `BACKEND_UNAVAILABLE` | Run `mac doctor backend`, ensure Appium is running |
| `ELEMENT_NOT_FOUND` | Run `mac element inspect` to refresh elements, find correct ref |
| `ELEMENT_REFERENCE_STALE` | Run `mac element inspect` — refs are invalidated after mutations |
| `ELEMENT_AMBIGUOUS` | Use `--first-match` or refine the locator strategy |
| `TYPE_VERIFICATION_FAILED` | Typed value didn't match; re-type or verify the target field |
| `ACTION_BLOCKED` | Add `--allow-dangerous` flag for dangerous operations |
| `TIMEOUT` | Increase `--timeout` or check if the target exists |
| `PERMISSION_DENIED` | Run `mac doctor permissions` and grant Accessibility access |

## Element References

- `mac element inspect` assigns refs: `e0`, `e1`, `e2`, ...
- Refs are **scoped to the last inspect/find** — a new inspect invalidates all previous refs
- After any mutation (click, type, etc.), refs may become stale
- Pattern: **inspect -> act -> re-inspect** for multi-step flows

## Safety Model

Commands are classified into three safety levels:

- **SAFE** — read-only operations (inspect, screenshot, list, wait, doctor)
- **GUARDED** — operations that modify state (click, type, launch, activate)
- **DANGEROUS** — destructive operations (terminate) — requires `--allow-dangerous`

## Common Patterns

### Calculator: 5 + 3

```bash
mac session start
mac app launch com.apple.calculator
mac element inspect                  # discover elements
mac element click e5                 # click "5"
mac element inspect                  # re-inspect after mutation
mac element click e2                 # click "+"
mac element inspect
mac element click e3                 # click "3"
mac element inspect
mac element click e8                 # click "="
mac capture screenshot ./result.png  # verify result
mac session end
```

### Type text into a search field

```bash
mac session start
mac app activate com.apple.safari
mac element inspect                      # find the search field
mac element type e12 "hello world"       # type into it
mac input hotkey command+a               # select all
mac capture screenshot ./typed.png
```

### Tips

- Always run `mac element inspect` before interacting with elements
- After any click/type, run `mac element inspect` again — refs are invalidated
- Use `mac capture screenshot` to visually verify results between steps
- Use `--pretty` when debugging interactively, omit for agent consumption
- Common bundle IDs: `com.apple.calculator`, `com.apple.Safari`, `com.apple.finder`, `com.apple.TextEdit`, `com.apple.systempreferences`

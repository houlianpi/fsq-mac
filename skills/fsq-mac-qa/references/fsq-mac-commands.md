# fsq-mac Command Reference for QA

Quick-reference cheatsheet for fsq-mac CLI commands used during macOS application QA sessions.

## 1. Session Lifecycle

| Command | Description | Safety |
|---------|-------------|--------|
| `mac session start` | Start a new automation session | SAFE |
| `mac session get` | Get current session info | SAFE |
| `mac session list` | List all active sessions | SAFE |
| `mac session end` | End the current session | SAFE |

## 2. App Management

| Command | Description | Safety |
|---------|-------------|--------|
| `mac app launch <bundle_id>` | Launch an application | GUARDED |
| `mac app current` | Get frontmost application info | SAFE |
| `mac app list` | List running applications | SAFE |
| `mac app activate <bundle_id>` | Bring an application to front | GUARDED |
| `mac app terminate <bundle_id> --allow-dangerous` | Terminate an application | DANGEROUS |

## 3. Window Management

| Command | Description | Safety |
|---------|-------------|--------|
| `mac window current` | Get frontmost window info | SAFE |
| `mac window list` | List all windows | SAFE |
| `mac window focus <index>` | Focus a window by index | GUARDED |

## 4. Element Inspection

| Command | Description | Safety |
|---------|-------------|--------|
| `mac element inspect [--pretty]` | Inspect all visible elements | SAFE |
| `mac element find` | Find elements matching a locator | SAFE |

Locator flags (used with `find` and most element/assert commands): `--id`, `--role`, `--name`, `--label`, `--xpath`.

> Element refs (`e0`, `e1`, ...) are assigned by `inspect`/`find` and become stale after any mutation. See [Element Ref Lifecycle](#element-ref-lifecycle).

## 5. Element Interaction

All commands accept an optional `[ref]` (e.g., `e0`) or locator flags.

| Command | Description | Safety |
|---------|-------------|--------|
| `mac element click [ref]` | Click an element | GUARDED |
| `mac element right-click [ref]` | Right-click an element | GUARDED |
| `mac element double-click [ref]` | Double-click an element | GUARDED |
| `mac element type [ref] <text>` | Type text into an element | GUARDED |
| `mac element scroll [ref] <direction>` | Scroll (up/down/left/right) | GUARDED |
| `mac element hover [ref]` | Hover over an element | GUARDED |
| `mac element drag <source> <target>` | Drag from one element to another | GUARDED |

## 6. Direct Input

| Command | Description | Safety |
|---------|-------------|--------|
| `mac input key <key>` | Press a single key (e.g., `Return`) | GUARDED |
| `mac input hotkey <combo>` | Press a key combination (e.g., `cmd+c`) | GUARDED |
| `mac input text <text>` | Type text without an element target | GUARDED |
| `mac input click-at <x> <y>` | Click at screen coordinates | GUARDED |

## 7. Assertions

All assert commands accept locator flags (`--id`, `--role`, `--name`, `--label`, `--xpath`).

| Command | Description | Safety |
|---------|-------------|--------|
| `mac assert visible` | Assert element is visible | SAFE |
| `mac assert enabled` | Assert element is enabled | SAFE |
| `mac assert text <expected>` | Assert element text matches | SAFE |
| `mac assert value <expected>` | Assert element value matches | SAFE |

## 8. Menu Navigation

| Command | Description | Safety |
|---------|-------------|--------|
| `mac menu click "Path > To > Item"` | Click a menu item by path | GUARDED |

## 9. Capture

| Command | Description | Safety |
|---------|-------------|--------|
| `mac capture screenshot [path]` | Take a full screenshot | SAFE |
| `mac capture screenshot --element <ref>` | Screenshot a specific element | SAFE |
| `mac capture screenshot --rect x,y,w,h` | Screenshot a region | SAFE |
| `mac capture ui-tree` | Get UI element tree as XML | SAFE |

## 10. Wait / Polling

All wait commands accept `--timeout <ms>` (default: 10000) and `--strategy <strategy>`.

| Command | Description | Safety |
|---------|-------------|--------|
| `mac wait element <locator>` | Wait for an element to appear | SAFE |
| `mac wait window <title>` | Wait for a window to appear | SAFE |
| `mac wait app <bundle_id>` | Wait for an application to start | SAFE |

## 11. Trace Record-Replay

| Command | Description | Safety |
|---------|-------------|--------|
| `mac trace start [path]` | Start recording a trace | SAFE |
| `mac trace stop` | Stop the active trace | SAFE |
| `mac trace status` | Show active trace status | SAFE |
| `mac trace replay <path>` | Replay a saved trace | GUARDED |
| `mac trace viewer <path>` | Generate HTML viewer for a trace | SAFE |
| `mac trace codegen <path> [--output file]` | Generate shell script from trace | SAFE |

## 12. Diagnostics

| Command | Description | Safety |
|---------|-------------|--------|
| `mac doctor` | Run all environment checks | SAFE |
| `mac doctor permissions` | Check Accessibility permissions | SAFE |
| `mac doctor backend` | Check Appium server and Mac2 driver | SAFE |
| `mac doctor plugins` | List discovered plugins | SAFE |

## Global Flags

| Flag | Description |
|------|-------------|
| `--pretty` | Human-readable output |
| `--json` | JSON output (default) |
| `--sid <session-id>` | Target a specific session |
| `--verbose` / `--debug` | Logging verbosity |
| `--strategy <strategy>` | Element location strategy |
| `--timeout <ms>` | Command timeout in milliseconds |
| `--allow-dangerous` | Required for DANGEROUS commands |

## Safety Classification

| Level | Meaning | Example |
|-------|---------|---------|
| **SAFE** | Read-only, no side effects | `mac element inspect`, `mac capture screenshot` |
| **GUARDED** | Mutations, allowed by default | `mac element click`, `mac app launch` |
| **DANGEROUS** | Destructive, requires `--allow-dangerous` | `mac app terminate` |

## Common QA Patterns

**1. Inspect and screenshot all visible elements**
```bash
mac element inspect --pretty
mac capture screenshot --element e0   # repeat for each ref
```
**2. Verify button click produces expected result**
```bash
mac element inspect
mac element click e3
mac wait element "Result"
mac assert text "Expected" --name "Result"
```
**3. Record and replay a user flow**
```bash
mac trace start ./my-trace
# ... perform actions ...
mac trace stop
mac trace replay ./my-trace
```
**4. Test menu bar item**
```bash
mac menu click "File > Save"
mac wait window "Save"
mac assert visible --name "Save"
```
**5. Full-screen UI audit**
```bash
mac capture screenshot overview.png
mac capture ui-tree   # review tree for missing accessibility labels or roles
```

## Element Ref Lifecycle

Refs are assigned by `inspect` and `find`. After any mutation command (`click`, `type`, `scroll`, `hover`, `drag`, `right-click`, `double-click`), assume **all** refs are stale. Re-run `mac element inspect` or `mac element find` to get fresh refs before using them again.

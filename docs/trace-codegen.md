# Trace & Codegen Guide

This guide covers recording automation workflows, replaying them, and converting them to standalone scripts.

## Recording a trace

Start recording to capture every command you execute:

```bash
mac trace start
```

Optionally specify an output directory:

```bash
mac trace start /path/to/my-trace
```

Now run your automation steps normally. Each command is recorded as a trace step with:

- **Command name** (e.g., `element.click`)
- **Arguments** (e.g., `{"role": "AXButton", "name": "OK"}`)
- **Locator query** (element-targeting fields)
- **Replayability status**
- **Timing information**
- **Before/after screenshots** (PNG)
- **Before/after UI tree snapshots** (XML)

Stop recording:

```bash
mac trace stop
```

Check recording status at any time:

```bash
mac trace status
```

## Trace format

Each trace is stored in a directory with this structure:

```
<trace-id>/
  trace.json          # Manifest with all step metadata
  steps/
    000-before.png    # Screenshot before step 0
    000-after.png     # Screenshot after step 0
    000-before-tree.xml
    000-after-tree.xml
    001-before.png
    ...
  viewer/
    index.html        # Generated HTML report
```

### trace.json manifest

```json
{
  "trace_id": "20250401-143022",
  "output_dir": "/path/to/trace",
  "created_at": "2025-04-01T14:30:22",
  "backend": "appium_mac2",
  "session_id": "abc123",
  "status": "stopped",
  "steps": [
    {
      "index": 0,
      "command": "element.click",
      "args": {},
      "locator_query": {"role": "AXButton", "name": "OK"},
      "replayable": true,
      "started_at": "2025-04-01T14:30:25",
      "duration_ms": 142,
      "ok": true,
      "artifacts": {
        "before_screenshot": ".../steps/000-before.png",
        "after_screenshot": ".../steps/000-after.png",
        "before_tree": ".../steps/000-before-tree.xml",
        "after_tree": ".../steps/000-after-tree.xml"
      }
    }
  ]
}
```

## Replay

Replay re-executes each step through the adapter:

```bash
mac trace replay /path/to/trace
```

### Replay behavior

- Steps are executed in order.
- If a step is marked `replayable: false`, replay stops with an error.
- If a command fails during replay, the error is reported with the failing step index.
- Non-replayable steps include those using element refs (`e0`, `e1`, ...) that are session-specific.

### Replay result

```json
{
  "ok": true,
  "completed_steps": 5,
  "total_steps": 5
}
```

On failure:

```json
{
  "ok": false,
  "completed_steps": 2,
  "failing_step": {"index": 3, "command": "element.click"},
  "error": {"code": "ELEMENT_NOT_FOUND", "message": "..."}
}
```

## HTML viewer

Generate a visual report of a trace:

```bash
mac trace viewer /path/to/trace
```

This creates `viewer/index.html` with:

- Step-by-step timeline
- Before/after screenshots
- UI tree diff summaries
- Command details and timing

## Code generation

Convert a recorded trace into a runnable bash script:

```bash
# Print to stdout
mac trace codegen /path/to/trace

# Write to file (automatically made executable)
mac trace codegen /path/to/trace --output script.sh
```

### Generated script format

```bash
#!/usr/bin/env bash
set -euo pipefail

mac session start

mac app launch com.apple.calculator
mac element click --role AXButton --name '5'
mac element click --role AXButton --name '+'
mac element click --role AXButton --name '3'
mac input key Return

mac session end
```

### Command mapping

| Trace command | Generated CLI |
|--------------|---------------|
| `app.launch` | `mac app launch <bundle_id>` |
| `app.activate` | `mac app activate <bundle_id>` |
| `app.terminate` | `mac app terminate <bundle_id> --allow-dangerous` |
| `element.click` | `mac element click` + locator flags |
| `element.type` | `mac element type --text <text>` + locator flags |
| `element.scroll` | `mac element scroll --direction <dir>` + locator flags |
| `input.key` | `mac input key <key>` |
| `input.hotkey` | `mac input hotkey <combo>` |
| `input.text` | `mac input text <text>` |
| `input.click-at` | `mac input click-at --x <x> --y <y>` |
| `menu.click` | `mac menu click --path <path>` |
| `assert.*` | `mac assert <action>` + flags |
| `wait.*` | `mac wait <action>` + flags |

### Non-replayable steps

Steps marked as not replayable are emitted as comments:

```bash
# SKIPPED (not replayable): element.click {'ref': 'e0'}
```

### Unknown commands

Commands without a mapping are emitted as TODO comments:

```bash
# TODO: manual step -- custom.action {'key': 'val'}
```

## Locator replayability

Locators determine whether a step can be replayed:

| Locator type | Replayable | Notes |
|-------------|-----------|-------|
| `--role` + `--name` | Yes | Preferred for stable replay |
| `--label` | Yes | Good for accessibility labels |
| `--xpath` | Yes | Fragile if UI changes |
| `--id` | Yes | Stable if app sets accessibility IDs |
| Element ref (`e0`) | No | Session-specific, not portable |

For best replay results, use role + name locators when possible.

## Customizing generated scripts

The generated script is plain bash. You can:

- Add error handling (`|| echo "Step failed"`)
- Insert delays (`sleep 1`)
- Add conditional logic
- Replace TODO comments with manual implementations
- Add loops for repeated actions

All argument values are properly escaped with `shlex.quote()` to prevent shell injection.

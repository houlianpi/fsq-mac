# Quickstart

Get up and running with fsq-mac in minutes.

## Prerequisites

- **macOS** 13+ (Ventura or later recommended)
- **Python 3.10+**
- **Appium server** with the Mac2 driver installed
- **Accessibility permission** granted to your terminal

### Install Appium and Mac2 driver

```bash
npm install -g appium
appium driver install mac2
```

### Grant Accessibility permission

Open **System Settings > Privacy & Security > Accessibility** and add your terminal app (Terminal.app, iTerm2, etc.).

## Installation

```bash
# From PyPI
pip install fsq-mac

# Or clone and install for development
git clone https://github.com/houlianpi/fsq-mac.git
cd fsq-mac
uv sync
```

After installation, the CLI is available as `mac`.

If you are running directly from the source checkout without installing the package, use `uv run mac ...` as a temporary alternative.

### Verify installation

```bash
mac doctor
```

This checks Accessibility permissions, Appium server, Mac2 driver, and plugins in one step. Fix any issues it reports before proceeding.

## Your first session

### 1. Start Appium server

In a separate terminal:

```bash
appium
```

> If `mac session start` later fails with `BACKEND_UNAVAILABLE`, ensure Appium is running and reachable at `http://127.0.0.1:4723`.

### 2. Start a session

```bash
mac session start
```

This auto-starts the fsq-mac daemon and creates a new automation session.

### 3. Explore running apps

```bash
# List running applications
mac app list

# Get the frontmost app
mac app current

# Verify app state
mac assert app-running com.apple.Safari
mac assert app-frontmost com.apple.Safari
```

### 4. Inspect the UI

```bash
# Inspect all visible elements as a structured snapshot
mac element inspect --pretty

# Find a specific element
mac element find --role AXButton --name OK
```

`element inspect` returns a snapshot-oriented payload. The most important top-level fields are:

- `snapshot_id`
- `generation`
- `backend`
- `binding_mode`
- `binding_warnings`
- `elements`

Typical meanings:

- `binding_mode=bound`: every snapshot element received a bound ref under the current Appium Mac2 accessibility heuristic
- `binding_mode=heuristic`: some snapshot elements were bound and some were left unbound
- `binding_mode=unbound_only`: the snapshot contains visible elements, but none received actionable refs
- `binding_warnings` may include `WEB_CONTENT_BEST_EFFORT`: browser web content is available, but still only through accessibility, not DOM-native guarantees

Example:

```json
{
  "ok": true,
  "command": "element.inspect",
  "data": {
    "snapshot_id": "snap_12",
    "generation": 12,
    "backend": "appium_mac2",
    "binding_mode": "bound",
    "binding_warnings": [],
    "elements": [
      {
        "element_id": "e0",
        "role": "Button",
        "name": "OK",
        "element_bounds": {"x": 10, "y": 20, "width": 80, "height": 40},
        "center": {"x": 50, "y": 40},
        "ref_bound": true,
        "ref_status": "bound",
        "state_source": "xml"
      }
    ],
    "count": 1
  }
}
```

### 5. Interact with elements

```bash
# Click a button
mac element click --role AXButton --name OK

# Type text into a field
mac element type "hello world" --role AXTextField

# Force key-injection mode when you need key-event semantics
mac element type "hello world" --role AXTextField --input-method keys

# Press a key
mac input key Return

# Type into the focused element using the default paste-first path
mac input text "hello world"
```

Successful element actions may also attach machine-consumable context such as:

- `resolved_element`
- `actionability_used`
- `element_bounds`
- `center`
- `snapshot_status`
- optional best-effort `snapshot`
- for drag: `resolved_target`, `target_bounds`, `target_center`

If an action fails, prefer `error.code` and `error.details` over parsing free-form messages.

### 6. End the session

```bash
mac session end
```

## Recording a trace

Traces record your interactions for replay and script generation.

```bash
# Start recording
mac trace start

# Perform your actions
mac element click --role AXButton --name "5"
mac element click --role AXButton --name "+"
mac element click --role AXButton --name "3"
mac input key Return

# Stop recording
mac trace stop
```

The trace is saved to `artifacts/traces/<trace-id>/`.

### View the trace

```bash
mac trace viewer artifacts/traces/<trace-id>
```

This generates an HTML report at `viewer/index.html`.

### Replay a trace

```bash
mac trace replay artifacts/traces/<trace-id>
```

## Generating a script

Convert any trace into a runnable bash script:

```bash
# Print to stdout
mac trace codegen artifacts/traces/<trace-id>

# Write to file
mac trace codegen artifacts/traces/<trace-id> --output script.sh
```

The generated script uses `mac` CLI commands and is immediately runnable.

## Environment diagnostics

Check that your environment is correctly configured:

```bash
# Run all checks
mac doctor

# Check specific areas
mac doctor permissions   # Accessibility permission
mac doctor backend       # Appium server and Mac2 driver
mac doctor plugins       # Installed plugins
```

## Output formatting

All commands return structured JSON by default, except for successful `trace codegen` which prints raw script text or a write confirmation. Use `--pretty` for human-readable output:

```bash
mac element inspect --pretty
```

## Next steps

- [Agent Contract](agent-contract.json) -- machine-readable command and error contract
- [Agent Playbook](agent-playbook.md) -- recommended orchestration and recovery patterns
- [OpenAPI](openapi.json) -- daemon endpoint schema
- [CLI Reference](cli-reference.md) -- complete list of all commands and flags
- [Architecture](architecture.md) -- how fsq-mac works internally
- [Trace & Codegen Guide](trace-codegen.md) -- detailed trace and codegen workflows
- [Plugin Development](plugins.md) -- extend fsq-mac with custom backends
- [Releasing](releasing.md) -- PyPI publishing and release workflow

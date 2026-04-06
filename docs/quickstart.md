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
uv pip install fsq-mac

# Or clone and install for development
git clone https://github.com/anthropics/fsq-mac.git
cd fsq-mac
uv sync
```

After installation, the CLI is available as `mac`.

If you are running directly from the source checkout without installing the package, use `uv run mac ...` as a temporary alternative.

## Your first session

### 1. Start Appium server

In a separate terminal:

```bash
appium
```

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
```

### 4. Inspect the UI

```bash
# Inspect all visible elements
mac element inspect

# Find a specific element
mac element find --role AXButton --name OK
```

### 5. Interact with elements

```bash
# Click a button
mac element click --role AXButton --name OK

# Type text into a field
mac element type "hello world" --role AXTextField

# Press a key
mac input key Return
```

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

All commands return structured JSON by default. Use `--pretty` for human-readable output:

```bash
mac element inspect --pretty
```

## Next steps

- [CLI Reference](cli-reference.md) -- complete list of all commands and flags
- [Architecture](architecture.md) -- how fsq-mac works internally
- [Trace & Codegen Guide](trace-codegen.md) -- detailed trace and codegen workflows
- [Plugin Development](plugins.md) -- extend fsq-mac with custom backends
- [Releasing](releasing.md) -- PyPI publishing and release workflow

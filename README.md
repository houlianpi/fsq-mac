# fsq-mac

Agent-first macOS native application automation CLI.

## Overview

`fsq-mac` is a daemon/client CLI tool that drives macOS native applications via Appium Mac2. It is designed for AI agent consumption — every command returns a structured JSON envelope with `ok`, `error.code`, `retryable`, and `suggested_next_action` fields.

## Architecture

```
CLI (cli.py) → HTTP Client → Daemon (Starlette/Uvicorn) → Core → Adapter (Appium Mac2)
```

- **Daemon auto-lifecycle**: Starts on first CLI call, auto-exits after 30 min idle
- **Session management**: Monotonic IDs, stale cleanup on restart
- **Safety classification**: Commands are SAFE / GUARDED / DANGEROUS (gated by `--allow-dangerous`)

## Prerequisites

- Python 3.10+
- [Appium](https://appium.io/) with [mac2 driver](https://github.com/nicedoc/appium-mac2-driver)
- macOS Accessibility permissions granted to the terminal

## Install

```bash
uv sync
```

## Usage

```bash
# Start a session (daemon auto-starts)
mac session start

# Inspect the frontmost app UI tree
mac element inspect --pretty

# Click an element by ref
mac element click e3

# Type text into an element
mac element type e5 "hello world"

# Get frontmost application info
mac app current --pretty

# Get frontmost window info (title, position, size)
mac window current --pretty

# Wait for an element
mac element wait "Submit" accessibility_id --timeout 5000

# End session
mac session end s1

# Check environment
mac doctor
```

## Commands

| Command | Description |
|---------|-------------|
| `session start` | Start automation session |
| `session end <id>` | End a session |
| `session list` | List active sessions |
| `element inspect` | Inspect UI tree, bind element refs |
| `element find <query> <by>` | Find elements by locator |
| `element click <ref>` | Click an element |
| `element type <ref> <text>` | Type text into an element (with verification) |
| `element attr <ref> <name>` | Get element attribute |
| `element scroll <ref> <dir>` | Scroll an element |
| `element wait <query> <by>` | Wait for element to appear |
| `app current` | Get frontmost application info |
| `app list` | List running applications |
| `app launch <bundle_id>` | Launch an application |
| `app terminate <bundle_id>` | Terminate an application |
| `app activate <bundle_id>` | Activate (bring to front) an application |
| `window current` | Get frontmost window info (title, position, size) |
| `window list` | List windows of frontmost app |
| `window switch <index>` | Switch to a window by index |
| `screenshot` | Take a screenshot |
| `doctor` | Check environment and dependencies |

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v
```

## State Directory

Session state is stored in `~/.fsq-mac/`. The daemon writes PID and port files there for lifecycle management.

## License

MIT

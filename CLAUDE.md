# CLAUDE.md

## Project Overview

fsq-mac is an agent-first macOS native application automation CLI. It uses a daemon/client architecture where the CLI communicates over HTTP with a Starlette/Uvicorn daemon that drives Appium Mac2.

## Build & Run

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v

# Run the CLI
uv run mac session start
```

## Architecture

```
src/fsq_mac/
├── cli.py              # CLI entry point (argparse)
├── client.py           # HTTP client → daemon
├── daemon.py           # Starlette HTTP daemon
├── core.py             # Product semantics layer
├── session.py          # Multi-session management
├── models.py           # Data models, ErrorCode enum, response helpers
├── formatters.py       # Output formatters (JSON, pretty, table)
├── doctor.py           # Environment diagnostics
└── adapters/
    └── appium_mac2.py  # Appium Mac2 WebDriver adapter
```

- `cli.py` → `client.py` → HTTP → `daemon.py` → `core.py` → `session.py` → `adapters/appium_mac2.py`
- State directory: `~/.fsq-mac/`
- Daemon auto-starts on first CLI call, auto-exits after 30 min idle

## Key Conventions

- **Python 3.10+**, managed with `uv`
- **src layout**: all source under `src/fsq_mac/`, imports use `from fsq_mac.module import ...`
- **Response envelope**: Every command returns `{"ok": bool, "data": {...}, "error": {"code": "...", "message": "...", "retryable": bool, "suggested_next_action": "..."}, "meta": {...}}`
- **Safety classification**: SAFE / GUARDED / DANGEROUS — dangerous commands require `--allow-dangerous`
- **Element refs**: Static refs (`e0`, `e1`, ...) bound during `element inspect`, invalidated on mutation
- **AppleScript**: Used for frontmost app/window queries; use `_safe_applescript_str()` to prevent injection
- **Commit messages**: Present-tense verb, first line under 50 chars

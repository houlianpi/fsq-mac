# Phase 4: Codegen, Performance, Plugins, Documentation — Design & Implementation

> Date: 2026-04-06
> Status: Implemented

## Goal

Add four capabilities on top of the Phase 3 trace loop:

1. Trace-to-shell-script code generation
2. Inspect performance optimization via native tree caching
3. Plugin system for adapters and doctor checks via Python entry points
4. User-facing documentation

These are largely independent and can be developed in parallel.

---

## Architecture Choices

### Codegen

The codegen module is a pure function: `TraceRun` in, bash script out. It lives in a dedicated `codegen.py` module rather than expanding `trace.py`, because codegen is a consumer of trace data, not part of the trace runtime.

The mapping from trace commands to CLI invocations is an internal dict inside `codegen.py`. This keeps the mapping colocated with the output format and avoids coupling `cli.py` to the trace system.

All argument values are escaped with `shlex.quote()` to prevent shell injection in generated scripts. Non-replayable steps emit comments rather than failing, since codegen is a best-effort export.

### Tree Caching

The bottleneck is `page_source` — a full XML fetch of the accessibility tree that takes 45–120ms per call. Multiple operations (inspect, ui_tree, repeated finds) may call it redundantly within a short window.

The cache is adapter-internal with a configurable TTL (default 2s). It is invalidated after any mutation command (click, type, scroll, drag, app lifecycle, menu click). This is conservative: false invalidation is cheap, stale cache is dangerous.

The cache lives on the adapter instance, not as a global or module-level construct, so multi-session scenarios remain correct.

### Plugin System

Use Python's standard `importlib.metadata.entry_points` mechanism. This is the established pattern for plugin discovery in the Python ecosystem and requires zero custom infrastructure.

Two entry point groups:

- `fsq_mac.adapters` — adapter backend factories
- `fsq_mac.doctor` — environment check callables

Built-in adapters are registered first; entry points with colliding names are silently skipped. Broken entry points (import errors, missing dependencies) are silently skipped to avoid breaking the CLI for all users when one plugin is broken.

Discovery runs at module import time via a module-level function call, consistent with the existing `register_adapter("appium_mac2", ...)` pattern.

### Documentation

Five guides cover the user journey from installation to plugin development. Documentation lives in `docs/` and references the actual CLI surface and code architecture.

---

## Scope

### Included

- `mac trace codegen <path> [--output file]`
- `generate_shell_script()` with full command mapping table
- adapter-level `_get_page_source()` cache with TTL and invalidation
- `_discover_entry_points()` for adapters and doctor checks
- `mac doctor plugins` subcommand
- `[project.entry-points]` declarations in pyproject.toml
- docs: quickstart, CLI reference, architecture, trace-codegen guide, plugin guide

### Excluded

- Codegen for languages other than bash
- AST-level script optimization or deduplication
- Distributed or shared tree cache
- Plugin marketplace or version compatibility checks
- Auto-generated API docs from docstrings

---

## Implementation

### Task 18: Trace → Shell Script Codegen

**Files created:**
- `src/fsq_mac/codegen.py` — `generate_shell_script(trace_run)` with command mapping dict, `_locator_flags()`, `_emit_step()`
- `tests/test_codegen.py` — 8 tests covering basic output, non-replayable skip, arg quoting, unknown commands, multiple steps, empty trace, locator flags, core integration

**Files modified:**
- `src/fsq_mac/core.py` — added `trace_codegen()` method, `trace.codegen: SAFE` in `_SAFETY`
- `src/fsq_mac/daemon.py` — added `codegen` action in trace dispatch block
- `src/fsq_mac/cli.py` — added `trace codegen` subcommand with `--output` flag; updated `_run()` to handle file output with `chmod +x`
- `tests/test_routes.py` — added `trace-codegen` to route coverage

**Command mapping table:**

| Trace command | CLI output |
|--------------|------------|
| `app.launch` | `mac app launch {bundle_id}` |
| `app.activate` | `mac app activate {bundle_id}` |
| `app.terminate` | `mac app terminate {bundle_id} --allow-dangerous` |
| `element.click` | `mac element click` + locator flags |
| `element.type` | `mac element type --text {text}` + locator flags |
| `element.scroll` | `mac element scroll --direction {dir}` + locator flags |
| `element.hover` | `mac element hover` + locator flags |
| `element.drag` | `mac element drag` + locator + target flags |
| `input.key` | `mac input key {key}` |
| `input.hotkey` | `mac input hotkey {combo}` |
| `input.text` | `mac input text {text}` |
| `input.click-at` | `mac input click-at --x {x} --y {y}` |
| `menu.click` | `mac menu click --path {path}` |
| `assert.*` | `mac assert {action}` + flags |
| `wait.*` | `mac wait {action}` + flags |
| Unknown | `# TODO: manual step` comment |

### Task 19: Native Tree Caching

**Files modified:**
- `src/fsq_mac/adapters/appium_mac2.py`:
  - Added `_tree_cache`, `_tree_cache_time`, `_tree_ttl` to `__init__`
  - Added `_get_page_source(force_refresh=False)` method
  - Added `self._tree_cache = None` invalidation in: `click()`, `type_text()`, `scroll()`, `drag()`, `app_launch()`, `app_activate()`, `app_terminate()`, `menu_click()`
  - Updated `inspect()` and `ui_tree()` to use `_get_page_source()`

**Files created:**
- `tests/test_tree_cache.py` — 6 tests: cache within TTL, expiry refetch, invalidation after click/type, TTL=0 disables, force_refresh bypass

**Config:** `tree_cache_ttl` (float, seconds, default 2.0). Set to 0 to disable.

### Task 20: Plugin System

**Files modified:**
- `src/fsq_mac/adapters/__init__.py` — added `_discover_entry_points()` using `entry_points(group="fsq_mac.adapters")`
- `src/fsq_mac/doctor.py` — added `_discover_doctor_plugins()` and `check_plugins()` returning adapter and doctor plugin lists
- `src/fsq_mac/daemon.py` — added `doctor.plugins` dispatch returning `check_plugins()` via `success_response()`
- `src/fsq_mac/cli.py` — added `plugins` action under doctor subparser
- `src/fsq_mac/core.py` — added `doctor.plugins: SAFE` to `_SAFETY`
- `pyproject.toml` — added `[project.entry-points."fsq_mac.adapters"]` and `[project.entry-points."fsq_mac.doctor"]`
- `tests/test_routes.py` — added `doctor-plugins` to route coverage

**Files created:**
- `tests/test_plugin_system.py` — 5 tests: entry point loading, broken plugin skip, builtin protection, doctor plugin listing, available_backends integration

### Task 21: Documentation

**Files created:**
- `docs/quickstart.md` — installation, first session, trace recording, codegen, doctor
- `docs/cli-reference.md` — complete command reference by domain with flags, safety levels, examples
- `docs/architecture.md` — request flow, module responsibilities, session lifecycle, adapter protocol, safety, trace system, response envelope, cache, plugins
- `docs/trace-codegen.md` — recording, trace format, replay semantics, codegen output, locator replayability, script customization
- `docs/plugins.md` — entry point groups, adapter plugin guide, doctor plugin guide, example pyproject.toml, discovery mechanism

---

## Testing Summary

| Test file | Tests | Coverage |
|-----------|-------|----------|
| `tests/test_codegen.py` | 8 | codegen module, core integration |
| `tests/test_tree_cache.py` | 6 | cache TTL, invalidation, disable, force refresh |
| `tests/test_plugin_system.py` | 5 | entry point discovery, error handling, registry |
| `tests/test_routes.py` | +2 | trace-codegen, doctor-plugins routes |

Total: 499 tests passing (up from 478), 0 warnings.

---

## Non-Goals

- No codegen for Python, JavaScript, or other languages
- No intelligent step merging or deduplication in codegen
- No plugin dependency resolution or version constraints
- No tree cache sharing across sessions or processes
- No live-reloading documentation server

# fsq-mac

[![CI](https://github.com/houlianpi/fsq-mac/actions/workflows/ci.yml/badge.svg)](https://github.com/houlianpi/fsq-mac/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://github.com/houlianpi/fsq-mac)
[![License](https://img.shields.io/github/license/houlianpi/fsq-mac.svg)](LICENSE)

Agent-first macOS automation CLI for native app automation.

`fsq-mac` is a Python command-line tool for automating macOS applications through Appium Mac2. It is designed for agent and tool use: commands return structured output, sessions are managed explicitly, and higher-level workflows such as trace, replay, code generation, and plugins are built in.

Product position today:

- native app automation first
- browser chrome and simple web content are supported on a best-effort basis through accessibility
- complex web DOM semantics are out of scope for the current backend

## Why fsq-mac

- Built for agent workflows: structured output, explicit sessions, and stable command surfaces instead of ad-hoc scripting glue.
- More replayable than AppleScript, Hammerspoon, or coordinate-driven tools because it records locator-based UI actions, traces, and generated shell scripts.
- More operationally predictable than one-off local scripts because daemon lifecycle, safety gating, trace capture, replay, code generation, and plugin discovery are part of the product.

Demo screenshots and GIF guidance live in [docs/assets/README.md](docs/assets/README.md).

## Install

> **Requires:** macOS, Python 3.10+, Appium with Mac2 driver, and Accessibility permissions.
> See [Quickstart](docs/quickstart.md) for full setup instructions.

```bash
pip install fsq-mac
```

After installation, the CLI is available as `mac`.

## Quickstart

Check the installed version:

```bash
mac --version
```

Run environment diagnostics:

```bash
mac doctor
```

Start a session:

```bash
mac session start
```

Inspect the current application and window:

```bash
mac app current --pretty
mac window current --pretty
```

Main workflow:

```bash
mac element inspect --pretty
mac element click --role AXButton --name OK
mac element type "hello world" --role AXTextField
mac capture screenshot
```

`element inspect` now returns a structured snapshot contract with fields such as `snapshot_id`, `generation`, `backend`, `binding_mode`, `binding_warnings`, and `elements`.

For native app flows, `binding_warnings` is often empty. For browser and web-content flows, warnings may include `WEB_CONTENT_BEST_EFFORT`, which means the current backend is using accessibility rather than DOM-native guarantees.

## Examples

Start a session and inspect the current UI tree:

```bash
mac session start
mac element inspect --pretty
mac capture ui-tree
```

Work with the current application:

```bash
mac app current --pretty
mac window list
mac app list
```

Record and replay a trace:

```bash
mac trace start artifacts/traces/demo
mac trace stop
mac trace replay artifacts/traces/demo
```

Inspect and action responses are machine-consumable. Example success envelope:

```json
{
  "ok": true,
  "command": "element.click",
  "session_id": "s1",
  "data": {
    "resolved_element": {"ref": "e0", "role": "AXButton", "name": "OK"},
    "actionability_used": {"actionable": true, "checks": {"has_ref": true, "has_geometry": true, "visible": true, "enabled": true}},
    "element_bounds": {"x": 10, "y": 20, "width": 80, "height": 40},
    "center": {"x": 50, "y": 40},
    "snapshot_status": "attached"
  },
  "error": null,
  "meta": {"backend": "appium_mac2", "duration_ms": 42}
}
```

Successful element actions can include:

- `resolved_element`
- `actionability_used`
- `element_bounds`
- `center`
- `snapshot_status`
- best-effort `snapshot`

Generate shell commands from a trace:

```bash
mac trace codegen artifacts/traces/demo
```

For repository screenshots and short GIF demos, see [docs/assets/README.md](docs/assets/README.md).

## Exit Codes

- `0` — command succeeded (`ok: true`)
- `1` — command failed (`ok: false`)

## Prerequisites

`fsq-mac` requires:

- macOS
- Python 3.10+
- [Appium](https://appium.io/)
- [appium-mac2-driver](https://github.com/appium/appium-mac2-driver)
- Accessibility permissions granted to the terminal or host process running `mac`

## Documentation

- [Agent Contract](docs/agent-contract.json)
- [Agent Playbook](docs/agent-playbook.md)
- [OpenAPI](docs/openapi.json)
- [Quickstart](docs/quickstart.md)
- [CLI Reference](docs/cli-reference.md)
- [Architecture](docs/architecture.md)
- [Trace & Codegen Guide](docs/trace-codegen.md)
- [Plugins](docs/plugins.md)
- [Manual E2E Test Plan](docs/testing/manual-e2e-test-plan.md)
- [Releasing](docs/releasing.md)
- [Changelog](CHANGELOG.md)
- [Demo Assets Guide](docs/assets/README.md)
- [Demo Recording Plan](docs/assets/demo-recording-plan.md)

## Examples

- [Calculator E2E](examples/calculator-e2e.sh)
- [Trace Replay And Codegen](examples/trace-replay-codegen.sh)

## Development

For local development from source:

```bash
uv sync --group dev
uv run pytest tests/ -v
```

## CI

GitHub Actions runs the repository test suite from `.github/workflows/ci.yml`.
The CI workflow runs `uv run pytest tests/ --junitxml=test-results/junit.xml` and uploads `test-results/junit.xml` plus any generated `artifacts/` directory as workflow artifacts.

## Release

Releases are published to PyPI through GitHub Actions on tags matching `v*`.

See [docs/releasing.md](docs/releasing.md) for the full release process.
GitHub Releases can use the repository release note configuration in [release.yml](.github/release.yml).

## State Directory

Session and daemon state is stored in `~/.fsq-mac/`.

## License

MIT

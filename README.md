# fsq-mac

[![PyPI](https://img.shields.io/pypi/v/fsq-mac.svg)](https://pypi.org/project/fsq-mac/)
[![CI](https://github.com/qunmi/fsq-mac/actions/workflows/ci.yml/badge.svg)](https://github.com/qunmi/fsq-mac/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/fsq-mac.svg)](https://pypi.org/project/fsq-mac/)
[![License](https://img.shields.io/github/license/qunmi/fsq-mac.svg)](LICENSE)

Agent-first macOS automation CLI for native app automation.

`fsq-mac` is a Python command-line tool for automating native macOS applications through Appium Mac2. It is designed for agent and tool use: commands return structured output, sessions are managed explicitly, and higher-level workflows such as trace, replay, code generation, and plugins are built in.

## Why fsq-mac

- Structured, agent-friendly CLI for macOS native app automation.
- Daemon-backed execution with explicit session management and safety gating.
- Advanced workflows including trace capture, replay, code generation, and plugin extensibility.

## Install

Install the published CLI from PyPI:

```bash
uv pip install fsq-mac
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

## Examples

Start a session and inspect the current UI tree:

```bash
mac session start
mac element inspect
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

Generate shell commands from a trace:

```bash
mac trace codegen artifacts/traces/demo
```

## Prerequisites

`fsq-mac` requires:

- macOS
- Python 3.10+
- [Appium](https://appium.io/)
- [appium-mac2-driver](https://github.com/nicedoc/appium-mac2-driver)
- Accessibility permissions granted to the terminal or host process running `mac`

## Documentation

- [Quickstart](docs/quickstart.md)
- [CLI Reference](docs/cli-reference.md)
- [Architecture](docs/architecture.md)
- [Plugins](docs/plugins.md)
- [Manual E2E Test Plan](docs/testing/manual-e2e-test-plan.md)
- [Releasing](docs/releasing.md)
- [Changelog](CHANGELOG.md)
- [Demo Assets Guide](docs/assets/README.md)

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

# Contributing to fsq-mac

Thanks for contributing to `fsq-mac`.

## Development Setup

Clone the repository and install development dependencies:

```bash
uv sync --group dev
```

Run the test suite:

```bash
uv run pytest tests/ -v
```

## Development Guidelines

- Keep changes small and focused.
- Update tests when behavior changes.
- Update docs when user-facing commands or workflows change.
- Preserve existing CLI behavior unless the change is intentional and documented.

## Pull Requests

Before opening a pull request, make sure:

- Tests pass locally.
- New behavior is covered by tests where practical.
- README and docs stay consistent with the actual CLI.
- The pull request description explains the user-visible impact.

## Reporting Issues

Use GitHub Issues for bug reports and feature requests. Include reproduction steps, expected behavior, actual behavior, and environment details when relevant.

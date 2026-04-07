# Changelog

All notable changes to `fsq-mac` will be documented in this file.

The format is based on Keep a Changelog and the project follows semantic versioning where practical.

## [Unreleased]

## [0.2.1] - 2026-04-07

### Fixed

- Changed install command in README from `uv pip install` to `pip install` for broader accessibility.
- Replaced PyPI-dependent badges with static versions so they render correctly before the package is published.
- Fixed CI test `test_readme_prefers_pypi_install_for_users` to match updated install command.
- Fixed CI test `test_app_activate_connected_returns_dict` failing on Linux by mocking the macOS-only `_wait_for_frontmost_app` call.
- Added command timeout (`_run_with_timeout`, default 15s) to prevent `element click` and other driver operations from hanging indefinitely (closes #4).

## [0.2.0] - 2026-04-07

### Added

- Bounded stabilization polling for app launch, app activation, and window focus flows.
- Additional regression tests covering timing-sensitive app and window transitions.
- Manual timing-stability coverage in the end-to-end test plan.

### Changed

- `app_launch()`, `app_activate()`, and `window_focus()` now wait for observable UI state convergence before returning success.
- `wait_app()` and `wait_window()` keep existence-based semantics while using the unified polling path.

### Fixed

- Mapped page source timeout failures to `TIMEOUT` instead of backend-unavailable errors.
- Prevented inspect and related tree operations from hanging indefinitely when the backend becomes unresponsive.

### Added

- Trace recording, replay, static viewer generation, and shell script code generation workflows.
- Plugin discovery for adapters and doctor checks via Python entry points.
- Manual end-to-end test planning and release automation documentation.
- Contributor, security, community, and GitHub template documents for the repository.

### Changed

- Refined the repository presentation with a product-style README, contributor docs, security policy, and GitHub collaboration templates.
- Added regression coverage to keep the exported CLI version aligned with packaging metadata.
- Improved README navigation to highlight trace/codegen documentation and PyPI-first installation.

### Fixed

- Corrected exported CLI version metadata drift so `mac --version` stays aligned with the packaged release.

## [0.1.0] - 2026-04-03

### Added

- Initial CLI foundation for sessions, apps, windows, elements, input, assertions, capture, wait, and doctor commands.
- Structured response envelopes designed for agent consumption.
- Lazy locator support, auto-wait semantics, and Appium Mac2 adapter integration.
- Tree cache invalidation coverage for interactive commands.
- CI coverage for core CLI and daemon behavior.

## [0.1.1] - 2026-04-07

### Added

- Automated PyPI publishing through GitHub Actions using Trusted Publishing.
- Manual end-to-end testing documentation and release process documentation.

### Changed

- Improved CI workflow robustness and caching.
- Updated installation guidance to prefer PyPI for end users.

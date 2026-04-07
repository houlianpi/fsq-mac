# Changelog

All notable changes to `fsq-mac` will be documented in this file.

The format is based on Keep a Changelog and the project follows semantic versioning where practical.

## [Unreleased]

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

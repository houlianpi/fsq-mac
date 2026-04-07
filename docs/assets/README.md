# Demo Assets

This directory is reserved for repository-facing demo assets used in the GitHub README and release notes.

Recommended files:

- `demo-terminal.png` for a static terminal screenshot
- `demo-workflow.gif` for a short end-to-end recording
- `architecture-overview.png` for a simple system diagram

## Recommended Demo Sequence

Use one short workflow that demonstrates the product from install-ready CLI to visible automation output.

Suggested sequence:

1. `mac --version`
2. `mac doctor`
3. `mac session start`
4. `mac app current --pretty`
5. `mac element inspect`
6. `mac trace start artifacts/traces/demo`
7. perform one visible interaction
8. `mac trace stop`
9. `mac trace codegen artifacts/traces/demo`

## Screenshot Guidance

For `demo-terminal.png`:

- Capture a clean terminal window with readable font size.
- Show one successful command with useful structured output.
- Avoid exposing private file paths, tokens, or machine-specific secrets.
- Prefer a narrow crop that reads well in the GitHub README.

## GIF Guidance

For `demo-workflow.gif`:

- Keep the clip between 10 and 20 seconds.
- Focus on one end-to-end workflow, not every feature.
- Start from an already prepared environment to avoid dead time.
- Show visible CLI output and one real macOS interaction.
- Keep file size small enough for fast GitHub page loads.

## Capture Checklist

- Confirm the CLI version shown in the demo matches the latest release.
- Confirm commands in the demo still match the current docs.
- Re-record assets after major CLI syntax changes.
- Use the same commands as the README quickstart where possible.

## README Placement

When assets are available, place them near the top of `README.md`:

- `demo-terminal.png` under `Why fsq-mac` or `Install`
- `demo-workflow.gif` between `Quickstart` and `Examples`

Guidelines:

- Keep GIFs short and focused on one workflow.
- Prefer terminal output and native macOS UI that match the published CLI.
- Refresh assets when the CLI syntax or primary workflows change.

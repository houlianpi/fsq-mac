# Demo Recording Plan

This document describes how to record the first real README demo assets for `fsq-mac`.

## Goal

Produce two assets:

- `docs/assets/demo-terminal.png`
- `docs/assets/demo-workflow.gif`

The assets should make the GitHub README feel real, current, and product-like.

## Environment Preparation

Before recording, confirm:

- `mac --version` shows the latest released version
- Appium is running
- Accessibility permission is already granted
- The demo app is open or ready to launch
- Terminal font size is readable on GitHub without zooming

Recommended demo app:

- `Calculator` for a short visible workflow

## Terminal Screenshot Plan

Capture one still screenshot showing a successful command with meaningful output.

Recommended command:

```bash
mac app current --pretty
```

Alternative commands:

```bash
mac doctor
mac window current --pretty
mac trace codegen artifacts/traces/demo
```

Requirements:

- Use a clean terminal theme with good contrast.
- Avoid showing unrelated shell history.
- Crop tightly around the terminal window.
- Do not expose private paths, tokens, or personal machine details.

## GIF Workflow Plan

Target duration: 10 to 20 seconds.

Use this exact sequence if possible:

```bash
mac --version
mac doctor
mac session start
mac app current --pretty
mac trace start artifacts/traces/demo
```

Then perform one visible interaction in Calculator, for example:

- click `5`
- click `+`
- click `3`
- press `Return`

Finish with:

```bash
mac trace stop
mac trace codegen artifacts/traces/demo
```

## Recording Notes

- Start recording after the terminal is already positioned.
- Keep cursor movement deliberate and minimal.
- Avoid pauses between commands.
- If a command has long output, let it settle before moving on.
- If the app launch is slow, pre-open the app before recording.

## README Placement

After assets are recorded:

1. Add `demo-terminal.png` below `Why fsq-mac` or `Install`
2. Add `demo-workflow.gif` between `Quickstart` and `Examples`
3. Keep the GIF below the fold if it makes the README feel too heavy

## Final Checklist

- The CLI syntax matches the current docs
- The version shown matches the current release
- The commands succeed without manual explanation
- The terminal crop looks good on GitHub desktop width
- The GIF file size is reasonable for fast loading

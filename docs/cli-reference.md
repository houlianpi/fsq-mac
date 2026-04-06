# CLI Reference

All commands follow the pattern: `mac <domain> <action> [args] [flags]`

Global flags available on all commands:
- `--pretty` — human-readable output
- `--json` — JSON output (default)
- `--sid <session-id>` — target a specific session
- `--verbose` / `--debug` — logging verbosity

## session

| Command | Description | Safety |
|---------|-------------|--------|
| `mac session start` | Start a new automation session | SAFE |
| `mac session get` | Get current session info | SAFE |
| `mac session list` | List all active sessions | SAFE |
| `mac session end` | End the current session | SAFE |

```bash
mac session start
mac session list --pretty
mac session end
```

## app

| Command | Description | Safety |
|---------|-------------|--------|
| `mac app launch <bundle_id>` | Launch an application | GUARDED |
| `mac app activate <bundle_id>` | Activate (bring to front) an application | GUARDED |
| `mac app list` | List running applications | SAFE |
| `mac app current` | Get frontmost application info | SAFE |
| `mac app terminate <bundle_id> --allow-dangerous` | Terminate an application | DANGEROUS |

```bash
mac app launch com.apple.calculator
mac app activate com.apple.Safari
mac app list --pretty
mac app current
mac app terminate com.apple.calculator --allow-dangerous
```

## window

| Command | Description | Safety |
|---------|-------------|--------|
| `mac window current` | Get frontmost window info | SAFE |
| `mac window list` | List all windows | SAFE |
| `mac window focus <index>` | Focus a window by index | GUARDED |

```bash
mac window current
mac window list --pretty
mac window focus 0
```

## element

All element commands accept locator flags: `--id`, `--role`, `--name`, `--label`, `--xpath`

| Command | Description | Safety |
|---------|-------------|--------|
| `mac element inspect` | Inspect all visible elements | SAFE |
| `mac element find` | Find elements matching locator | SAFE |
| `mac element click` | Click an element | GUARDED |
| `mac element right-click` | Right-click an element | GUARDED |
| `mac element double-click` | Double-click an element | GUARDED |
| `mac element type <text>` | Type text into an element | GUARDED |
| `mac element scroll <dir>` | Scroll an element | GUARDED |
| `mac element hover` | Hover over an element | GUARDED |
| `mac element drag` | Drag an element | GUARDED |

```bash
mac element inspect --pretty
mac element find --role AXButton
mac element click --role AXButton --name OK
mac element type "hello world" --role AXTextField
mac element scroll down --role AXScrollArea
mac element right-click --name "File"
```

## input

| Command | Description | Safety |
|---------|-------------|--------|
| `mac input key <key>` | Press a single key | GUARDED |
| `mac input hotkey <combo>` | Press a key combination | GUARDED |
| `mac input text <text>` | Type text (no element target) | GUARDED |
| `mac input click-at <x> <y>` | Click at screen coordinates | GUARDED |

```bash
mac input key Return
mac input hotkey cmd+c
mac input text "hello world"
mac input click-at 100 200
```

## assert

All assert commands accept locator flags: `--id`, `--role`, `--name`, `--label`, `--xpath`

| Command | Description | Safety |
|---------|-------------|--------|
| `mac assert visible` | Assert element is visible | SAFE |
| `mac assert enabled` | Assert element is enabled | SAFE |
| `mac assert text <text>` | Assert element text matches | SAFE |
| `mac assert value <value>` | Assert element value matches | SAFE |

```bash
mac assert visible --role AXButton --name OK
mac assert enabled --role AXTextField
mac assert text "Hello" --role AXStaticText
mac assert value "42" --role AXTextField
```

## menu

| Command | Description | Safety |
|---------|-------------|--------|
| `mac menu click <path>` | Click a menu item by path | GUARDED |

```bash
mac menu click "File > Open"
mac menu click "Edit > Copy"
```

## trace

| Command | Description | Safety |
|---------|-------------|--------|
| `mac trace start [path]` | Start recording a trace | SAFE |
| `mac trace stop` | Stop the active trace | SAFE |
| `mac trace status` | Show active trace status | SAFE |
| `mac trace replay <path>` | Replay a saved trace | GUARDED |
| `mac trace viewer <path>` | Generate HTML viewer for a trace | SAFE |
| `mac trace codegen <path> [--output file]` | Generate shell script from trace | SAFE |

```bash
mac trace start
mac trace stop
mac trace status
mac trace replay artifacts/traces/20250101-120000
mac trace viewer artifacts/traces/20250101-120000
mac trace codegen artifacts/traces/20250101-120000
mac trace codegen artifacts/traces/20250101-120000 --output script.sh
```

## capture

| Command | Description | Safety |
|---------|-------------|--------|
| `mac capture screenshot [path]` | Take a screenshot | SAFE |
| `mac capture ui-tree` | Get UI element tree as XML | SAFE |

Flags for screenshot:
- `--element <ref>` — screenshot a specific element (e.g., `e0`)
- `--rect <x,y,w,h>` — screenshot a region

```bash
mac capture screenshot ./screenshot.png
mac capture screenshot --element e0
mac capture screenshot --rect 0,0,400,300
mac capture ui-tree
```

## wait

| Command | Description | Safety |
|---------|-------------|--------|
| `mac wait element <locator>` | Wait for element to appear | SAFE |
| `mac wait window <title>` | Wait for window to appear | SAFE |
| `mac wait app <bundle_id>` | Wait for application to start | SAFE |

All wait commands accept `--timeout <ms>` (default: 10000) and `--strategy <strategy>`.

```bash
mac wait element "OK" --timeout 5000
mac wait window "Main Window"
mac wait app com.apple.calculator
```

## doctor

| Command | Description | Safety |
|---------|-------------|--------|
| `mac doctor` | Run all environment checks | SAFE |
| `mac doctor permissions` | Check Accessibility permissions | SAFE |
| `mac doctor backend` | Check Appium server and Mac2 driver | SAFE |
| `mac doctor plugins` | List discovered plugins | SAFE |

```bash
mac doctor
mac doctor permissions
mac doctor backend
mac doctor plugins
```

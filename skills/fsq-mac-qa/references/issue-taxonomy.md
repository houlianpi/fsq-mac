# Issue Taxonomy

Classification system for issues discovered during macOS application QA testing.

## Severity Levels

| Level | Definition | Examples |
|-------|-----------|----------|
| **critical** | Blocks core workflow, causes data loss, or crashes the app | App crashes on launch; clicking Save deletes data; main window fails to render |
| **high** | Major feature broken or unusable, no workaround | Cannot type in primary text field; menu items unresponsive; keyboard shortcuts do nothing |
| **medium** | Feature works but with noticeable problems, workaround exists | Wrong font in title bar; dialog appears behind main window; scroll doesn't reach bottom |
| **low** | Minor cosmetic or polish issue | 1px misalignment in toolbar; slightly wrong shade of gray; extra whitespace |

## Categories

| Category | Description | What to look for |
|----------|-----------|-----------------|
| **Visual/UI** | Layout, alignment, colors, fonts, spacing | Misaligned elements, wrong colors, clipped text, overlapping elements |
| **Functional** | Incorrect behavior, buttons don't work, crashes | Click does nothing, wrong result from action, app crash, data not saved |
| **UX** | Confusing flow, poor feedback, unexpected behavior | No loading indicator, confusing navigation, no error message on failure |
| **Content** | Typos, placeholder text, missing labels | Lorem ipsum text, "TODO" labels, misspelled menu items |
| **Menu/Shortcut** | Menu items unreachable, shortcuts not working (macOS-specific) | Menu item grayed out incorrectly, hotkey does nothing, wrong shortcut listed |
| **Accessibility** | Missing roles/labels in UI tree, VoiceOver incompatibility | Elements with no `name` or `label` in `mac element inspect`, wrong `role` |

## Evidence Model

Two tiers of evidence based on issue type.

### Interactive/Behavioral Issues

Functional bugs, UX problems — anything involving user interaction.

**Required evidence:**

1. Start trace: `mac trace start qa-screenshots/<round>/trace-ISSUE-NNN`
2. Perform each repro step, taking a screenshot at each step: `mac capture screenshot qa-screenshots/<round>/ISSUE-NNN-stepN.png`
3. Stop trace: `mac trace stop`
4. Document all steps in the issue block with screenshot references

### Static/Visible-on-Load Issues

Typos, misalignment, placeholder text — visible without interaction.

**Required evidence:**

1. Single screenshot: `mac capture screenshot qa-screenshots/<round>/ISSUE-NNN.png`
2. Document in issue block with screenshot reference

## Per-Page Exploration Checklist

Use this checklist at every screen during Explore mode:

1. **Visual scan** — Take a screenshot. Look for layout issues, clipped text, overlapping elements, wrong colors.
2. **Interactive elements** — Run `mac element inspect --pretty`. Click every button, link, and control. Verify each produces the expected response.
3. **Forms** — Find text fields and inputs. Test: empty submit, valid input, boundary values (very long string, special characters), invalid input.
4. **Menu bar** — Use `mac menu click` to traverse each top-level menu and its sub-items. Verify all items are reachable and produce expected behavior.
5. **Keyboard shortcuts** — Test common macOS combos with `mac input hotkey`: `cmd+s` (save), `cmd+z` (undo), `cmd+c`/`cmd+v` (copy/paste), `cmd+q` (quit), `cmd+w` (close window), `cmd+n` (new), `cmd+o` (open).
6. **Multi-window** — If the app supports multiple windows, open several. Test focus switching with `mac window focus`. Verify window list with `mac window list`.
7. **Edge states** — Test with no data, maximum data, after kill/restart (`mac app terminate --allow-dangerous` then `mac app launch`). Test error conditions.

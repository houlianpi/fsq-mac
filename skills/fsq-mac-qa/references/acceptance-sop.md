# Acceptance SOP — fsq-mac QA Skill

Standard Operating Procedures for all QA testing modes, build support, and error recovery.
Follow each step in order. Do not skip steps.

---

## Section 1: Acceptance Mode SOP

Triggered when the user provides a PRD/design spec + target app. All 9 steps (1-9) are mandatory.

### Step 1 — Write Test Cases

1. Read the user-provided PRD or design specification in full.
2. Load `templates/qa-checklist.md`.
3. Generate a filled `qa-checklist.md` covering all 10 categories:
   - First Launch — initial state, permissions dialogs
   - Main Windows — each window renders correctly
   - Core Interactions — buttons, forms, navigation
   - Menu Bar — menu item reachability, correct behavior
   - Keyboard Shortcuts — hotkey combinations
   - Multi-Window — window management, focus behavior
   - Data/Persistence — state management, save/load
   - Design Fidelity — colors, fonts, spacing vs design spec
   - Accessibility — roles/labels in UI tree, VoiceOver compatibility
   - Edge Cases — empty states, boundary values, kill/restart
4. Each category must have at least one testable item with a clear pass/fail criterion.

**HARD GATE**: No test cases, no testing. Do not proceed until the checklist is saved. If the user has no PRD, suggest switching to Explore mode or ask them to provide requirements.

### Step 2 — Environment Check

1. Run `mac doctor`.
2. If any check fails, stop. Show the `suggested_next_action` to the user. Do not proceed.

### Step 3 — Start Session

1. Run `mac session start`. Capture the session ID for all subsequent commands.

### Step 4 — Launch App

- **Bundle ID provided**: Run `mac app launch <bundle_id>`.
- **Source project provided**: Follow the Build Support flow (Section 4).

Then run `mac app current` to confirm the correct app is frontmost.

### Step 5 — Global Screenshots

1. Create directory `qa-screenshots/<round>/` (e.g., `round-1`).
2. Run `mac capture screenshot qa-screenshots/<round>/overview.png`.
3. Navigate to each main screen and capture with descriptive filenames.

### Step 6 — UI Tree Collection

1. Run `mac capture ui-tree` for each major screen.
2. Note element counts to gauge complexity. Use the tree to plan Step 6.

### Step 7 — Item-by-Item Verification

For each checklist item:

1. Perform the action: `mac element click`, `mac element type`, `mac menu click`, `mac input hotkey`, etc.
2. Verify the outcome: `mac assert text/value/visible/enabled`.
3. Pass: mark item as pass. Fail: take screenshot as evidence, mark as fail.
4. Update the report incrementally after each item.
5. After any mutation command, assume element refs may be stale — re-run `mac element inspect` as needed.

### Step 8 — Screenshot Evidence

1. Ensure every fail item has a screenshot showing the failure state.
2. For items with a design spec, capture current state for Design vs Actual comparison.
3. Store evidence in `qa-screenshots/<round>/` with names referencing the checklist item.

### Step 9 — Output Report

1. Load `templates/acceptance-report.md`. Fill in the summary table:

   | Metric | Value |
   |--------|-------|
   | Total items | XX |
   | Pass | XX |
   | Fail | XX |
   | Pending | XX |
   | Pass rate | XX% |
   | P0 (critical) | X |
   | P1 (high) | X |

2. Include full checklist results and issue blocks for all fail items.
3. Determine verdict:
   - **Accepted**: Pass rate >= 90% AND zero P0 (critical) issues (default threshold; user may override).
   - **Not Accepted**: Pass rate < 90% OR any P0 issues.
   - **Conditional**: Pass rate >= 90% but P1 (high) issues remain.

---

## Section 2: Explore Mode SOP

Triggered when the user provides only an app name/bundle ID with no PRD. Goal: autonomous
issue discovery. Target 5-10 well-documented issues. Depth over breadth.

### Step 1 — Setup

1. Run `mac doctor`. Stop on failure, show `suggested_next_action`.
2. Run `mac session start`. Capture session ID.
3. Create directory `qa-screenshots/<round>/`.

### Step 2 — App Discovery

1. `mac app current` to identify the frontmost app.
2. `mac window list` to see all windows. Note app name, bundle ID, window titles.

### Step 3 — UI Mapping

1. `mac element inspect --pretty` to get the full element list.
2. Build a mental map of UI structure: windows, controls, screen relationships.
3. Repeat for each window discovered.

### Step 4 — Interaction Exploration

Work through the per-page checklist for each screen:

1. **Visual scan** — Screenshot. Look for layout issues, misalignment, truncation.
2. **Interactive elements** — `mac element inspect` then `mac element click` each button/link.
3. **Forms** — Fill/submit with `mac element type`. Test empty, invalid, edge-case inputs.
4. **Menu bar** — `mac menu click` to traverse all menu items.
5. **Keyboard shortcuts** — `mac input hotkey` for common combos (Cmd+N, Cmd+W, Cmd+S, etc.).
6. **Multi-window** — Open multiple windows. Test focus, ordering, cross-window interactions.
7. **Edge states** — Empty data, error states, content overflow.

Use `mac wait` for async loading between interactions.

### Step 5 — Screenshot Archive

Capture `mac capture screenshot` for every distinct screen state. Use descriptive filenames.

### Step 6 — Issue Discovery

1. Classify per `references/issue-taxonomy.md` (severity + category).
2. **Interactive bugs**: `mac trace start` then reproduce step-by-step then `mac trace stop`.
3. **Static issues**: Single screenshot is sufficient evidence.
4. Document expected vs actual behavior for each issue.

### Step 7 — Output Report

1. Generate discovery report adapted from `templates/acceptance-report.md`.
2. Produce an issues list (not pass/fail) using standard issue block format (ISSUE-001, etc.).
3. Include summary table of issues by severity and category.

**Key rules**: Test as a user (never read source code). Depth over breadth. Target 5-10 issues.

---

## Section 3: Regression Mode SOP

Triggered when the user provides a recorded trace file path. Goal: detect what changed.

### Step 1 — Setup

1. Run `mac doctor`. Stop on failure.
2. Run `mac session start`. Capture session ID.

### Step 2 — Baseline Replay

1. Run `mac trace replay <path>` with the user-provided trace file.
2. The trace system auto-captures before/after screenshots and UI tree snapshots per step.

### Step 3 — Screenshot Comparison

Review trace artifacts. Compare current screenshots with baseline from the original trace.

### Step 4 — Diff Detection

1. Use `mac assert` commands to verify expected state at each step.
2. Run `mac trace viewer <path>` to generate a visual HTML diff.
3. Note all differences: layout, text, missing elements, new elements.

### Step 5 — Output Report

1. Generate regression report: what changed compared to last run.
2. For each difference: trace step, expected state, actual state, screenshot.
3. Classify as intentional change or regression.

---

## Section 4: Build Support (Source Code Projects)

When the user provides a project path instead of a bundle ID, build before testing.

### Project Detection

| Priority | File Found | Build Strategy |
|----------|------------|----------------|
| 1 | `.xcworkspace` | Use `-workspace` flag |
| 2 | `.xcodeproj` | Use `-project` flag |
| 3 | `Package.swift` | SPM project |
| 4 | None found | Skip build, assume app is installed |

### Build Commands

```bash
# 1. Discover schemes
xcodebuild -list [-workspace|-project <file>]

# 2. Clean build
xcodebuild [-workspace|-project] <file> \
  -scheme <SCHEME> -destination 'platform=macOS' \
  -derivedDataPath build clean build 2>&1 | tail -20

# 3. Find and launch
APP_PATH=$(find build -name "*.app" -type d | head -1)
open "$APP_PATH"
```

After launching, run `mac app current` to get the bundle ID.

### Build Error Handling

On failure: extract errors with `grep "error:"`, report `file:line:message` to user, stop QA.

---

## Section 5: Error Recovery

When fsq-mac returns an error, apply the recovery action below, then retry once. If it
fails again, record the item as a failure and move on.

| Error Code | Recovery Action |
|------------|-----------------|
| `BACKEND_UNAVAILABLE` | Run `mac doctor backend`. Appium likely not running. Pause testing until fixed. |
| `ELEMENT_NOT_FOUND` | Re-run `mac element inspect` to refresh refs. Try `mac wait element` if not loaded yet. |
| `ELEMENT_REFERENCE_STALE` | Refs invalidated by mutation. Re-run `mac element inspect` for fresh refs, then retry. |
| `ELEMENT_AMBIGUOUS` | Locator matches multiple elements. Add specificity (e.g., `--role` + `--name`). |
| `TIMEOUT` | Retry with `--timeout 20000`. If still fails, record as failure. |
| `PERMISSION_DENIED` | Run `mac doctor permissions`. Guide user to System Settings > Privacy & Security > Accessibility. |
| `APP_NOT_FOUND` | Bundle ID incorrect or app not installed. Ask user to verify. |
| `SESSION_NOT_FOUND` | Session expired. Run `mac session start` to create a new one, then retry. |
| `SESSION_CONFLICT` | Another session active. `mac session list` then `mac session end` to clean up. |

### General Recovery Rules

1. After any error, check session validity with `mac session list`.
2. After `ELEMENT_NOT_FOUND` or `ELEMENT_REFERENCE_STALE`, always `mac element inspect` before further interactions.
3. Three consecutive failures on the same operation: record as failure, move to next item.
4. Always capture a screenshot when an error occurs during verification.

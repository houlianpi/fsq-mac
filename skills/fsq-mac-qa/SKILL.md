---
name: fsq-mac-qa
description: >
  macOS application QA testing using fsq-mac CLI. Covers acceptance testing
  (PRD-based), exploratory testing (autonomous discovery), and regression testing
  (trace replay). Use when asked to test a Mac app, QA an application, dogfood,
  run acceptance tests, verify app quality, or 测试/验收/帮我测一下 any macOS application.
---

# fsq-mac-qa

Structured QA testing for macOS applications using the `mac` CLI (fsq-mac). Three modes: **Acceptance** (with PRD), **Explore** (without PRD), **Regression** (with trace).

## Prerequisites

Run these checks on every invocation. Stop immediately if any fails.

```bash
mac doctor                    # Environment, Appium backend, Accessibility permissions
mac session start             # Establish automation session
```

If `mac doctor` fails, show the `suggested_next_action` from the response and guide the user to fix it. Do not proceed until all checks pass.

## Mode Dispatch

Determine the mode from user input:

| Priority | User provides | Mode |
|----------|---------------|------|
| 1 | Trace file path | **Regression** |
| 2 | PRD / design spec + target app | **Acceptance** |
| 3 | Only app name or bundle ID | **Explore** |
| — | Nothing clear | Ask the user what they want to do |

When multiple signals are present, use the highest-priority match.

## Acceptance Mode

Structured verification against a PRD or design spec. Every step is mandatory.

**Full SOP**: See `references/acceptance-sop.md` Section 1.

### Steps (none may be skipped)

1. **Write test cases** — Read the PRD. Fill `templates/qa-checklist.md` with specific verification items across all 10 categories. **HARD GATE: no test cases, no testing.** If no PRD is available, ask the user to provide one or switch to Explore mode.
2. **Environment check** — `mac doctor`
3. **Start session** — `mac session start`
4. **Launch app** — `mac app launch <bundle_id>` or build from source (see Build Support below)
5. **Global screenshots** — Create `qa-screenshots/<round>/`. Screenshot every major screen.
6. **UI tree collection** — `mac capture ui-tree` for each screen
7. **Item-by-item verification** — For each checklist item: perform action (`mac element click/type`) then verify (`mac assert text/value/visible/enabled`). Mark ✅/❌ immediately. Take screenshot evidence for every ❌.
8. **Screenshot comparison** — If design spec available, capture Design vs Actual pairs.
9. **Output report** — Fill `templates/acceptance-report.md`. Calculate pass rate. Verdict: ✅ Accepted (>= 90% pass by default; override with user-specified threshold, zero P0), ❌ Not Accepted, or ⚠️ Conditional.

## Explore Mode

Autonomous issue discovery without a PRD. Test as a user, never read source code.

**Full SOP**: See `references/acceptance-sop.md` Section 2.
**Exploration checklist**: See `references/issue-taxonomy.md` Per-Page Exploration Checklist.

### Steps

1. **Setup** — `mac doctor` + `mac session start` + create `qa-screenshots/<round>/`
2. **App discovery** — `mac app current` + `mac window list`
3. **UI mapping** — `mac element inspect --pretty` to build a map of the current screen
4. **Interaction exploration** — Work through the per-page checklist at every screen:
   - Visual scan (screenshot)
   - Interactive elements (click every button/link)
   - Forms (test empty, valid, boundary, invalid inputs)
   - Menu bar (`mac menu click` each item)
   - Keyboard shortcuts (`mac input hotkey cmd+s`, `cmd+z`, `cmd+c`, `cmd+v`, etc.)
   - Multi-window behavior
   - Edge states (empty data, errors, overflow)
5. **Screenshot archive** — Capture every discovered screen
6. **Issue discovery** — Classify per `references/issue-taxonomy.md`. Record evidence per the Evidence Model.
7. **Output report** — Use `templates/acceptance-report.md` adapted for explore mode (issues list, no pass/fail checklist)

**Target 5-10 well-documented issues, but report the actual number found — fewer or more is fine.** Depth over breadth.

## Regression Mode

Replay a recorded trace and detect differences.

**Full SOP**: See `references/acceptance-sop.md` Section 3.

### Steps

1. **Setup** — `mac doctor` + `mac session start`
2. **Replay** — `mac trace replay <path>` (auto-captures before/after screenshots per step)
3. **Comparison** — Review trace artifacts; run `mac trace viewer <path>` for visual HTML diff
4. **Diff detection** — `mac assert` to verify expected state at key points
5. **Output report** — Regression report: what changed compared to last run

## Build Support

When user provides a source project path instead of a bundle ID:

| Priority | Detect | Build with |
|----------|--------|-----------|
| 1 | `.xcworkspace` | `-workspace` |
| 2 | `.xcodeproj` | `-project` |
| 3 | `Package.swift` | `swift build` |
| 4 | None | Skip build, assume app installed |

```bash
xcodebuild -list [-workspace|-project <file>]
xcodebuild <flag> <file> -scheme <SCHEME> -destination 'platform=macOS' \
  -derivedDataPath build clean build 2>&1 | tail -20
APP_PATH=$(find build -name "*.app" -type d | head -1)
open "$APP_PATH"
mac app current    # Get bundle ID for subsequent commands
```

On build errors: extract with `grep "error:"`, report to user, stop QA until fixed.

## Evidence Model

Classify evidence by issue type. See `references/issue-taxonomy.md` for full details.

| Issue type | Category | Evidence | Commands |
|-----------|----------|---------|---------|
| **Interactive/behavioral** (bugs, UX) | Functional, UX, Menu/Shortcut | Trace + step-by-step screenshots | `mac trace start` → actions with screenshots → `mac trace stop` |
| **Static/visible** (typos, alignment) | Visual/UI, Content, Accessibility | Single screenshot | `mac capture screenshot` |

> **Note:** `mac trace codegen` outputs raw text (not the standard JSON envelope). Parse its output as plain text.

## Output

All modes produce a Markdown report based on `templates/acceptance-report.md`.

- Screenshots saved to `qa-screenshots/<round>/`
- Each issue documented with the ISSUE-NNN block format (severity, category, repro steps, screenshots)
- Summary table with pass/fail metrics and verdict

## Error Recovery

| Error | Recovery |
|-------|---------|
| `BACKEND_UNAVAILABLE` | `mac doctor backend` — Appium not running. Pause testing. |
| `ELEMENT_NOT_FOUND` | `mac element inspect` — refresh refs. Try `mac wait element` if loading. |
| `ELEMENT_REFERENCE_STALE` | `mac element inspect` — refs invalidated by mutation. |
| `ELEMENT_AMBIGUOUS` | Add more locator flags (`--role` + `--name`). |
| `TIMEOUT` | Retry with `--timeout 20000`. Still fails → record as ❌. |
| `PERMISSION_DENIED` | `mac doctor permissions` — grant Accessibility access. |
| `APP_NOT_FOUND` | Verify bundle ID. Ask user to check. |
| `SESSION_NOT_FOUND` | `mac session start` — create new session. |
| `SESSION_CONFLICT` | `mac session list` then `mac session end` — another session active. |

Full error recovery table: `references/acceptance-sop.md` Section 5.
Command syntax reference: `references/fsq-mac-commands.md`.

## Locator Strategy

Interact with elements using semantic locators. NEVER use screenshots to estimate pixel coordinates.

| Priority | Method | When to use |
|----------|--------|-------------|
| 1 (best) | `--role` + `--name` | Default for all interactions |
| 2 | `--id` | When app exposes meaningful accessibility identifiers |
| 3 | `--label` | When name is unavailable but label is set |
| 4 | Element ref (`e0`) | Within the same inspect snapshot only |
| 5 | `--xpath` | Replayable but fragile; use when above fail |
| 6 (last resort) | `mac input click-at` | ONLY for elements not discoverable via accessibility API (e.g., custom canvas). Document why semantic locators failed. |

**Screenshots are for evidence only.** Never use a screenshot to guess coordinates for `click-at`.

## Key Rules

1. **Screenshot archival** — Every key step saves to `qa-screenshots/<round>/`. Use relative paths in reports.
2. **Element ref lifecycle** — After ANY mutation command (click, type, scroll, drag), assume ALL refs (`e0`, `e1`, ...) are stale. Re-run `mac element inspect` before using refs again.
3. **Safety** — GUARDED operations are allowed by default. DANGEROUS operations (`mac app terminate`) require explicit user consent via `--allow-dangerous`.
4. **Report completeness** — Every checklist item must have a ✅/❌/⏳ result. Every ❌ must have screenshot evidence.
5. **Incremental writing** — Append findings to the report immediately after each verification. Do not batch at the end.
6. **User perspective** — Test through UI and Accessibility API only. Never read application source code. You are testing as a user, not auditing code.
7. **Depth over breadth** — In Explore mode, target 5-10 well-documented issues rather than a shallow scan of everything.
8. **Inspect-first interaction** — Always run `mac element inspect` before interacting with elements. Use the structured element data (role, name, label) to target elements, not screenshot-derived coordinates. Prefer `mac element click --role button --name "Save"` over `mac element click e3` over `mac input click-at x y`.

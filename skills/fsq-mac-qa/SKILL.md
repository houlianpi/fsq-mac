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
xcodebuild -version           # Only if user provides a source-code project
```

If `mac doctor` fails, show the `suggested_next_action` from the response and guide the user to fix it. Do not proceed until all checks pass.

## Mode Dispatch

Determine the mode from user input:

| User provides | Mode |
|---------------|------|
| PRD / design spec + target app | **Acceptance** |
| Trace file path | **Regression** |
| Only app name or bundle ID | **Explore** |
| Nothing clear | Ask the user what they want to do |

## Acceptance Mode

Structured verification against a PRD or design spec. Every step is mandatory.

**Full SOP**: See `references/acceptance-sop.md` Section 1.

### Steps (none may be skipped)

0. **Write test cases** — Read the PRD. Fill `templates/qa-checklist.md` with specific verification items across all 10 categories. **HARD GATE: no test cases, no testing.**
1. **Environment check** — `mac doctor`
2. **Start session** — `mac session start`
3. **Launch app** — `mac app launch <bundle_id>` or build from source (see Build Support below)
4. **Global screenshots** — Create `qa-screenshots/<round>/`. Screenshot every major screen.
5. **UI tree collection** — `mac capture ui-tree` for each screen
6. **Item-by-item verification** — For each checklist item: perform action (`mac element click/type`) then verify (`mac assert text/value/visible/enabled`). Mark ✅/❌ immediately. Take screenshot evidence for every ❌.
7. **Screenshot comparison** — If design spec available, capture Design vs Actual pairs.
8. **Output report** — Fill `templates/acceptance-report.md`. Calculate pass rate. Verdict: ✅ Accepted (>= 90% pass, zero P0), ❌ Not Accepted, or ⚠️ Conditional.

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

**Target 5-10 well-documented issues.** Depth over breadth.

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

| Issue type | Evidence | Commands |
|-----------|---------|---------|
| **Interactive/behavioral** (bugs, UX) | Trace + step-by-step screenshots | `mac trace start` → actions with screenshots → `mac trace stop` |
| **Static/visible** (typos, alignment) | Single screenshot | `mac capture screenshot` |

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

Full error recovery table: `references/acceptance-sop.md` Section 5.
Command syntax reference: `references/fsq-mac-commands.md`.

## Key Rules

1. **Screenshot archival** — Every key step saves to `qa-screenshots/<round>/`. Use relative paths in reports.
2. **Element ref lifecycle** — After ANY mutation command (click, type, scroll, drag), assume ALL refs (`e0`, `e1`, ...) are stale. Re-run `mac element inspect` before using refs again.
3. **Safety** — GUARDED operations are allowed by default. DANGEROUS operations (`mac app terminate`) require explicit user consent via `--allow-dangerous`.
4. **Report completeness** — Every checklist item must have a ✅/❌/⏳ result. Every ❌ must have screenshot evidence.
5. **Incremental writing** — Append findings to the report immediately after each verification. Do not batch at the end.
6. **User perspective** — Test through UI and Accessibility API only. Never read application source code. You are testing as a user, not auditing code.
7. **Depth over breadth** — In Explore mode, target 5-10 well-documented issues rather than a shallow scan of everything.

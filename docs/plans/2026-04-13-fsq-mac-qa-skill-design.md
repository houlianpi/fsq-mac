# Design: fsq-mac-qa Skill

**Date:** 2026-04-13
**Status:** Approved
**References:** [ios-app-qa](https://github.com/GhostComplex/skills/tree/main/ios-app-qa), [agent-browser dogfood](https://github.com/vercel-labs/agent-browser/tree/main/skill-data/dogfood)

---

## Overview

`fsq-mac-qa` is a Claude Code skill that uses fsq-mac CLI to perform structured QA testing of macOS applications. It supports three modes: acceptance testing (with PRD), exploratory testing (without PRD), and regression testing (with recorded traces).

## Requirements

- **Test targets**: Any installed macOS app (by bundle ID) + source-code projects (Xcode build → test)
- **Test modes**: Acceptance (structured, PRD-based), Explore (autonomous discovery), Regression (trace replay)
- **Output**: Markdown acceptance report with screenshots and issue evidence
- **Form factor**: Independent Claude Code skill at `~/.claude/skills/fsq-mac-qa/`

## File Structure

```
~/.claude/skills/fsq-mac-qa/
├── SKILL.md                          # Core skill instructions
├── references/
│   ├── fsq-mac-commands.md           # fsq-mac command cheatsheet for Claude
│   ├── acceptance-sop.md             # Acceptance SOP detailed specification
│   └── issue-taxonomy.md             # Issue severity & category taxonomy
└── templates/
    ├── qa-checklist.md               # QA test case checklist template
    └── acceptance-report.md          # Acceptance report template
```

## SKILL.md Design

### Metadata & Triggers

```yaml
name: fsq-mac-qa
description: macOS application QA testing using fsq-mac CLI. Covers acceptance testing,
  exploratory testing, and regression testing. Use when asked to test a Mac app, QA
  an application, dogfood, run acceptance tests, or verify app quality.
```

Trigger phrases: "测试这个 app", "QA 验收", "帮我测一下", "探索式测试", "回归测试",
"run acceptance test", "dogfood this app", "test this Mac app"

### Prerequisites Check

On every invocation, the skill first verifies:

```bash
mac doctor                    # fsq-mac available, Appium backend accessible, permissions granted
mac session start             # Session can be established
xcodebuild -version           # Only if user provides a source project
```

Any failure stops the flow with actionable guidance (leveraging `mac doctor` suggested_next_action).

### Mode Dispatch Logic

```
IF user provides PRD/design spec + target app
  → Acceptance mode
ELIF user provides trace file path
  → Regression mode
ELIF user provides only app name/bundle ID
  → Explore mode
ELSE
  → Ask user what they want to do
```

## Mode 1: Acceptance (Structured Verification)

**Trigger**: User provides PRD/design spec + target application.

### Flow (SOP — every step mandatory)

| Step | Action | fsq-mac Commands |
|------|--------|-----------------|
| 0. Write test cases | Generate qa-checklist.md from PRD | Claude fills template |
| 1. Environment check | Verify fsq-mac is operational | `mac doctor` |
| 2. Start session | Establish automation connection | `mac session start` |
| 3. Launch app | Open target app (bundle ID or build from source) | `mac app launch <bundle_id>` |
| 4. Global screenshots | Capture every major screen | `mac capture screenshot <path>` |
| 5. UI tree collection | Get element tree for each screen | `mac capture ui-tree` |
| 6. Item-by-item verification | Execute operations and assertions per checklist | `mac element click/type` + `mac assert` |
| 7. Screenshot comparison | Capture per-verification-point, compare with design | `mac capture screenshot --element <ref>` |
| 8. Output report | Fill acceptance report template | Claude generates Markdown |

**Key rules**:
- "No test cases, no testing" — Step 0 must complete before proceeding
- Every fail item must have screenshot evidence
- Report includes Design vs Actual screenshot comparison (when design spec available)
- Write findings incrementally — append each result immediately

## Mode 2: Explore (Autonomous Discovery)

**Trigger**: User provides only an app name or bundle ID, no PRD.

### Flow

| Step | Action | fsq-mac Commands |
|------|--------|-----------------|
| 1. Environment + session | Check and connect | `mac doctor` + `mac session start` |
| 2. App discovery | Get current app info | `mac app current` + `mac window list` |
| 3. UI mapping | Inspect elements layer by layer | `mac element inspect` |
| 4. Interaction exploration | Try interactive elements | `mac element click/type` + `mac menu click` |
| 5. Screenshot archive | Capture every discovered screen | `mac capture screenshot` |
| 6. Issue discovery | Record anomalies, unreachable elements, crashes | `mac assert` series |
| 7. Output report | Discovery report (issue list, not pass/fail) | Claude generates Markdown |

**Per-page exploration checklist** (borrowed from dogfood):
1. Visual scan (annotated screenshot)
2. Interactive elements (`mac element inspect` → click every button/link)
3. Forms (fill/submit, test empty/invalid/edge-case inputs)
4. Menu bar (`mac menu click` — traverse all menu items)
5. Keyboard shortcuts (`mac input hotkey` — test common combos)
6. Multi-window behavior
7. Edge states (empty data, error states, overflow)

**Key rules**:
- Start from `mac element inspect` to build a UI map
- Proactively interact with any button, text field, or control discovered
- Use `mac wait` for async loading
- Screenshot every discovered screen
- Test as a user, never look at source code

## Mode 3: Regression (Trace Replay)

**Trigger**: User provides a recorded trace file path.

### Flow

| Step | Action | fsq-mac Commands |
|------|--------|-----------------|
| 1. Environment prep | Check and connect | `mac doctor` + `mac session start` |
| 2. Baseline replay | Replay trace or execute script | `mac trace replay <path>` |
| 3. Screenshot comparison | Trace auto-captures before/after screenshots | Built into trace |
| 4. Diff detection | Compare current results with expected | `mac assert` series |
| 5. Output report | Regression report (list diff items) | Claude generates Markdown |

**Key rules**:
- Leverage `mac trace` before/after screenshots and UI tree snapshots
- Use `mac trace viewer` to generate visual HTML diff
- Report focuses on "what changed compared to last run"

## Build Support (Source Code Projects)

When user provides a source project path instead of a bundle ID:

### Project Detection Priority
1. `.xcworkspace` → workspace build
2. `.xcodeproj` → project build
3. `Package.swift` → SPM project
4. None found → skip build, assume app is installed

### Build Flow

```bash
# Discover schemes
xcodebuild -list [-workspace|-project <file>]

# Clean build for macOS
xcodebuild [-workspace|-project] <file> \
  -scheme <SCHEME> \
  -destination 'platform=macOS' \
  -derivedDataPath build \
  clean build 2>&1 | tail -20

# Find and launch the built .app
APP_PATH=$(find build -name "*.app" -type d | head -1)
open "$APP_PATH"
# Then use mac app current to get bundle ID
```

## Evidence Model (from dogfood)

Issues require evidence proportional to their type:

| Issue Type | Evidence Required | fsq-mac Approach |
|------------|-------------------|-----------------|
| **Interactive/behavioral** (functional bugs, UX issues) | Full repro: trace recording + step-by-step screenshots | `mac trace start` → step-by-step operations with screenshots → `mac trace stop` |
| **Static/visible-on-load** (typos, misalignment, placeholder text) | Single screenshot | `mac capture screenshot` |

## Issue Taxonomy

### Severity Levels
- **critical**: Blocks core workflow, data loss, crash
- **high**: Major feature broken/unusable, no workaround
- **medium**: Feature works with noticeable problems, workaround exists
- **low**: Minor cosmetic or polish issue

### Categories
- **Visual/UI**: Layout, alignment, colors, fonts, spacing
- **Functional**: Buttons don't work, incorrect behavior, crashes
- **UX**: Confusing flow, poor feedback, accessibility issues
- **Content**: Typos, placeholder text, missing labels
- **Menu/Shortcut** (macOS-specific): Menu items unreachable, shortcuts not working
- **Accessibility**: Missing roles/labels in UI tree, VoiceOver incompatibility

## Error Handling Strategy

Leveraging fsq-mac's structured error responses:

| Error Code | Skill Behavior |
|------------|---------------|
| `BACKEND_UNAVAILABLE` | Prompt `mac doctor backend`, pause testing |
| `ELEMENT_NOT_FOUND` | Re-run `mac element inspect`, update refs |
| `ELEMENT_REFERENCE_STALE` | Re-inspect (refs invalidated by mutation) |
| `TIMEOUT` | Increase wait time, retry once; still fails → record as fail |
| `PERMISSION_DENIED` | Prompt user to grant Accessibility permission |
| `APP_NOT_FOUND` | Prompt user to check bundle ID or manually launch |

## Key Constraints

1. **Screenshot archival**: Every key step saves to `qa-screenshots/<round>/`
2. **Element ref management**: After any mutation command, assume refs are stale; re-inspect
3. **Safety classification**: Confirm before GUARDED operations; DANGEROUS (app terminate) requires explicit user consent
4. **Report completeness**: Every checklist item must have ✅/❌/⏳ result; fail items must have screenshots
5. **Incremental writing**: Append findings to report immediately (don't batch at end)
6. **User perspective**: Test through UI and Accessibility API only; never read application source code
7. **Target 5-10 well-documented issues** per explore session (depth over breadth)

## Templates

### QA Checklist Categories (macOS-specific)

1. **First Launch** — initial state, permissions dialogs
2. **Main Windows** — each window renders correctly
3. **Core Interactions** — buttons, forms, navigation
4. **Menu Bar** — menu item reachability, correct behavior
5. **Keyboard Shortcuts** — hotkey combinations
6. **Multi-Window** — window management, focus behavior
7. **Data** — persistence, state management
8. **Design Fidelity** — colors, fonts, spacing vs design spec (if available)
9. **Accessibility** — roles/labels in UI tree, VoiceOver compatibility
10. **Edge Cases** — empty states, boundary values, kill/restart

### Issue Block Format (in acceptance report)

```markdown
### ISSUE-001: [Title]

| Field | Value |
|-------|-------|
| Severity | critical/high/medium/low |
| Category | Functional / Visual / UX / ... |
| Window | [current window title] |
| Trace | [trace file path, if interactive issue] |

**Description**: What's wrong — expected vs actual behavior.

**Repro Steps**:
1. `mac app launch com.example.app`
2. `mac element click e3`  →  ![step2](./qa-screenshots/round/step2.png)
3. `mac element type e5 "test"`  →  ![step3](./qa-screenshots/round/step3.png)
4. Expected X, got Y  →  ![step4](./qa-screenshots/round/step4.png)
```

### Acceptance Report Summary Table

```markdown
| Metric | Value |
|--------|-------|
| Total items | XX |
| ✅ Pass | XX |
| ❌ Fail | XX |
| ⏳ Pending | XX |
| Pass rate | XX% |
| P0 (critical) | X |
| P1 (high) | X |

**Verdict:** ✅ Accepted / ❌ Not Accepted / ⚠️ Conditional
```

**Pass criteria**: Pass rate >= 90%, zero P0 issues.

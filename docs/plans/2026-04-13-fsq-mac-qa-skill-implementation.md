# fsq-mac-qa Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Claude Code skill that uses fsq-mac CLI to perform structured QA testing of macOS applications across three modes: acceptance, explore, and regression.

**Architecture:** Six static files — one SKILL.md (core instructions), three reference docs (command cheatsheet, acceptance SOP, issue taxonomy), and two templates (QA checklist, acceptance report). No code to build or test. All files are Markdown installed to `~/.claude/skills/fsq-mac-qa/`.

**Tech Stack:** Markdown, Claude Code skill format, fsq-mac CLI

---

### Task 1: Create directory structure

**Files:**
- Create: `~/.claude/skills/fsq-mac-qa/references/` (directory)
- Create: `~/.claude/skills/fsq-mac-qa/templates/` (directory)

**Step 1: Create directories**

```bash
mkdir -p ~/.claude/skills/fsq-mac-qa/references
mkdir -p ~/.claude/skills/fsq-mac-qa/templates
```

**Step 2: Verify structure**

Run: `ls -R ~/.claude/skills/fsq-mac-qa/`
Expected: `references/` and `templates/` subdirectories exist, both empty.

---

### Task 2: Create `references/fsq-mac-commands.md`

**Files:**
- Create: `~/.claude/skills/fsq-mac-qa/references/fsq-mac-commands.md`
- Reference: `docs/cli-reference.md` in the fsq-mac repo for exact command syntax

This is the command cheatsheet Claude uses during QA sessions. It must include every fsq-mac command grouped by QA workflow stage, with exact syntax and flags. Focus on the commands most used during testing: element inspection, interaction, assertions, screenshots, traces, and waits.

**Step 1: Write the file**

Content should cover:
- **Session lifecycle**: `mac session start`, `mac session end`
- **App management**: `mac app launch`, `mac app current`, `mac app list`, `mac app activate`, `mac app terminate --allow-dangerous`
- **Window management**: `mac window current`, `mac window list`, `mac window focus`
- **Element inspection**: `mac element inspect`, `mac element find` + locator flags (`--id`, `--role`, `--name`, `--label`, `--xpath`)
- **Element interaction**: `mac element click`, `mac element right-click`, `mac element double-click`, `mac element type`, `mac element scroll`, `mac element hover`, `mac element drag` — note that element refs (`e0`, `e1`, ...) are assigned by inspect/find and become stale after mutations
- **Direct input**: `mac input key`, `mac input hotkey`, `mac input text`, `mac input click-at`
- **Assertions**: `mac assert visible`, `mac assert enabled`, `mac assert text`, `mac assert value` + locator flags
- **Menu navigation**: `mac menu click "Path > To > Item"`
- **Capture**: `mac capture screenshot [path]`, `mac capture screenshot --element <ref>`, `mac capture screenshot --rect x,y,w,h`, `mac capture ui-tree`
- **Wait/polling**: `mac wait element`, `mac wait window`, `mac wait app` + `--timeout`
- **Trace record-replay**: `mac trace start`, `mac trace stop`, `mac trace status`, `mac trace replay`, `mac trace viewer`, `mac trace codegen`
- **Diagnostics**: `mac doctor`, `mac doctor permissions`, `mac doctor backend`
- **Global flags**: `--pretty`, `--json`, `--sid`, `--verbose`, `--debug`, `--strategy`, `--timeout`, `--allow-dangerous`
- **Safety classification**: SAFE (read-only), GUARDED (mutations, default allowed), DANGEROUS (requires `--allow-dangerous`)

Include a "Common QA Patterns" section with short multi-command recipes:
- "Screenshot all visible elements": inspect → iterate refs → screenshot --element
- "Verify a button click produces expected result": inspect → click → wait → assert text
- "Record and replay a user flow": trace start → actions → trace stop → trace replay

**Step 2: Verify**

Run: `wc -l ~/.claude/skills/fsq-mac-qa/references/fsq-mac-commands.md`
Expected: 100-200 lines.

**Step 3: Commit**

```bash
cd ~/Documents/github/fsq-mac
git add ~/.claude/skills/fsq-mac-qa/references/fsq-mac-commands.md
```

Note: Since these files live outside the repo, we will batch-commit at the end (Task 7).

---

### Task 3: Create `references/acceptance-sop.md`

**Files:**
- Create: `~/.claude/skills/fsq-mac-qa/references/acceptance-sop.md`

This document defines the step-by-step SOP for each of the three test modes. Claude reads this when executing the QA workflow.

**Step 1: Write the file**

Content must include three sections:

**Section 1: Acceptance Mode SOP** (8 mandatory steps, none may be skipped):
- Step 0: Write test cases from PRD → fill `qa-checklist.md` template
- Step 1: `mac doctor` → verify environment
- Step 2: `mac session start` → establish connection
- Step 3: `mac app launch <bundle_id>` or build-from-source flow (see Build Support below)
- Step 4: `mac capture screenshot` for every major screen → save to `qa-screenshots/<round>/`
- Step 5: `mac capture ui-tree` for each screen → note element counts and structure
- Step 6: Per-checklist-item verification: `mac element click/type` + `mac assert text/value/visible/enabled`
- Step 7: Per-verification screenshot, compare with design spec if available
- Step 8: Fill `acceptance-report.md` template with results
- Rule: "No test cases, no testing" — Step 0 is a hard gate
- Rule: Every ❌ fail must have screenshot evidence
- Rule: Write findings incrementally — append each result as verified

**Section 2: Explore Mode SOP** (7 steps):
- Step 1: Environment + session setup
- Step 2: `mac app current` + `mac window list` → identify what's running
- Step 3: `mac element inspect` → build UI map of the current screen
- Step 4: Interact with discovered elements (click buttons, fill text fields, navigate menus)
- Step 5: `mac capture screenshot` each discovered screen
- Step 6: Record anomalies using `mac assert` checks + visual observation
- Step 7: Output discovery report (issue list, not pass/fail)
- Per-page exploration checklist (from design): visual scan → interactive elements → forms → menu bar → keyboard shortcuts → multi-window → edge states
- Rule: Test as a user, never read source code
- Rule: Target 5-10 well-documented issues (depth over breadth)

**Section 3: Regression Mode SOP** (5 steps):
- Step 1: Environment prep
- Step 2: `mac trace replay <path>` → replay baseline
- Step 3: Compare screenshots (trace captures before/after automatically)
- Step 4: `mac assert` to detect differences
- Step 5: Regression report (list diff items)
- Rule: Use `mac trace viewer` for visual HTML diff

**Section 4: Build Support** (for source-code projects):
- Detection priority: `.xcworkspace` > `.xcodeproj` > `Package.swift` > skip
- Exact `xcodebuild` commands from design doc
- How to find and launch the built `.app`
- How to get bundle ID via `mac app current`

**Section 5: Error Recovery Table**:
- Map each `ErrorCode` to the recovery action (from design doc)

**Step 2: Verify**

Run: `wc -l ~/.claude/skills/fsq-mac-qa/references/acceptance-sop.md`
Expected: 150-250 lines.

---

### Task 4: Create `references/issue-taxonomy.md`

**Files:**
- Create: `~/.claude/skills/fsq-mac-qa/references/issue-taxonomy.md`

**Step 1: Write the file**

Content:

**Severity Levels** with definitions and examples:
- **critical**: Blocks core workflow, data loss, crash. Example: app crashes when clicking Save
- **high**: Major feature broken, no workaround. Example: cannot type in the main text field
- **medium**: Feature works with problems, workaround exists. Example: wrong font in title bar
- **low**: Minor cosmetic. Example: 1px misalignment in toolbar

**Categories** with descriptions:
- **Visual/UI**: Layout, alignment, colors, fonts, spacing
- **Functional**: Buttons don't work, incorrect behavior, crashes
- **UX**: Confusing flow, poor feedback, accessibility issues
- **Content**: Typos, placeholder text, missing labels
- **Menu/Shortcut**: Menu items unreachable, shortcuts not working (macOS-specific)
- **Accessibility**: Missing roles/labels in UI tree, VoiceOver incompatibility

**Evidence Model** (two tiers):
- Interactive/behavioral issues → full repro with `mac trace start` + step-by-step screenshots
- Static/visible-on-load issues → single `mac capture screenshot`

**Per-Page Exploration Checklist** (used during Explore mode):
1. Visual scan (screenshot)
2. Interactive elements (inspect → click every button/link)
3. Forms (fill/submit, test empty/invalid/edge inputs)
4. Menu bar (traverse all menu items)
5. Keyboard shortcuts (test common combos: cmd+s, cmd+z, cmd+q, etc.)
6. Multi-window behavior
7. Edge states (empty data, error states, overflow)

**Step 2: Verify**

Run: `wc -l ~/.claude/skills/fsq-mac-qa/references/issue-taxonomy.md`
Expected: 60-100 lines.

---

### Task 5: Create `templates/qa-checklist.md`

**Files:**
- Create: `~/.claude/skills/fsq-mac-qa/templates/qa-checklist.md`

**Step 1: Write the file**

Use the template from the design doc. The checklist is a fillable Markdown table with these sections:

Header fields: App Name, Platform (macOS version), Method (fsq-mac CLI), Screenshots directory, Session info.

10 category sections with placeholder rows:
1. First Launch
2. Main Windows
3. Core Interactions
4. Menu Bar
5. Keyboard Shortcuts
6. Multi-Window
7. Data / Persistence
8. Design Fidelity (if design spec available)
9. Accessibility
10. Edge Cases

Each row: `| # | Category | Verification Item | Result (⏳) | Screenshot | Notes |`

Pass criteria: >= 90% pass rate, zero P0 issues.

**Step 2: Verify**

Run: `wc -l ~/.claude/skills/fsq-mac-qa/templates/qa-checklist.md`
Expected: 50-80 lines.

---

### Task 6: Create `templates/acceptance-report.md`

**Files:**
- Create: `~/.claude/skills/fsq-mac-qa/templates/acceptance-report.md`

**Step 1: Write the file**

Template structure from the design doc:

1. **Header**: App Name, Date, Tester (Claude/fsq-mac-qa), Build info, Platform, PRD/Design reference
2. **Summary table**: Total items, Pass/Fail/Pending counts, Pass rate, P0/P1 counts, Verdict
3. **Verification Results sections** (one per category): each with a results table
4. **Design vs Actual** comparison section (optional, only when design spec available): side-by-side screenshot references
5. **Issues Found** section with the issue block format from design:
   - ISSUE-NNN: Title
   - Severity, Category, Window, Trace fields
   - Description (expected vs actual)
   - Repro Steps with embedded screenshot references
6. **Pending Items** table: items that couldn't be verified and why
7. **Conclusion**: 1-2 sentence overall assessment

**Step 2: Verify**

Run: `wc -l ~/.claude/skills/fsq-mac-qa/templates/acceptance-report.md`
Expected: 80-120 lines.

---

### Task 7: Create `SKILL.md`

**Files:**
- Create: `~/.claude/skills/fsq-mac-qa/SKILL.md`

This is the most critical file — it's the entry point that Claude loads when the skill is triggered.

**Step 1: Write the file**

Structure:

**Frontmatter / metadata:**
```yaml
---
name: fsq-mac-qa
description: macOS application QA testing using fsq-mac CLI. Covers acceptance testing,
  exploratory testing, and regression testing. Use when asked to test a Mac app, QA
  an application, dogfood, run acceptance tests, or verify app quality. Triggers on
  "测试这个 app", "QA 验收", "帮我测一下", "探索式测试", "回归测试", "test this Mac app",
  "dogfood this app", "run acceptance test".
---
```

**Section 1: Overview** (3-5 sentences) — what this skill does, three modes.

**Section 2: Prerequisites** — on every invocation, run:
1. `mac doctor` (abort if fail, show suggested_next_action)
2. `mac session start` (abort if fail)
3. `xcodebuild -version` (only if user provides source project)

**Section 3: Mode Dispatch** — the if/elif/else logic from design doc. Clearly state how to determine which mode based on user input.

**Section 4: Acceptance Mode** — reference `references/acceptance-sop.md` for the full SOP. Summarize the 8 mandatory steps here. Emphasize: "No test cases, no testing" is a hard gate.

**Section 5: Explore Mode** — reference `references/acceptance-sop.md` and `references/issue-taxonomy.md`. Summarize the 7 steps. Emphasize: test as a user, depth over breadth, target 5-10 issues.

**Section 6: Regression Mode** — summarize the 5 steps. Emphasize: leverage trace before/after artifacts.

**Section 7: Build Support** — when user provides source project path. Detection priority, build commands, launch flow.

**Section 8: Output** — all modes produce a Markdown report. Use `templates/acceptance-report.md` as the skeleton. Screenshots saved to `qa-screenshots/<round>/`.

**Section 9: Error Recovery** — table mapping ErrorCode → recovery action. Reference `references/fsq-mac-commands.md` for exact command syntax.

**Section 10: Key Rules** (the 7 constraints from design):
1. Screenshot archival to `qa-screenshots/<round>/`
2. Element refs become stale after mutations — re-inspect
3. Safety: confirm GUARDED ops, require explicit consent for DANGEROUS
4. Report completeness: every item needs a result
5. Incremental writing: append findings immediately
6. User perspective only: no source code reading
7. Depth over breadth in explore mode

**Step 2: Verify skill loads correctly**

Run: `cat ~/.claude/skills/fsq-mac-qa/SKILL.md | head -5`
Expected: frontmatter with `name: fsq-mac-qa`.

Run: `ls -R ~/.claude/skills/fsq-mac-qa/`
Expected: all 6 files present under correct subdirectories.

**Step 3: Commit the entire skill to the fsq-mac repo**

Since the skill lives outside the repo at `~/.claude/skills/`, we copy it into the repo for version control:

```bash
cp -r ~/.claude/skills/fsq-mac-qa/ ~/Documents/github/fsq-mac/skills/fsq-mac-qa/
cd ~/Documents/github/fsq-mac
git add skills/fsq-mac-qa/
git commit -m "Add fsq-mac-qa skill for macOS app QA testing"
```

---

### Task 8: End-to-end smoke test

**Files:**
- Verify: all 6 files under `~/.claude/skills/fsq-mac-qa/`

**Step 1: Verify complete file tree**

```bash
find ~/.claude/skills/fsq-mac-qa/ -type f | sort
```

Expected output:
```
~/.claude/skills/fsq-mac-qa/SKILL.md
~/.claude/skills/fsq-mac-qa/references/acceptance-sop.md
~/.claude/skills/fsq-mac-qa/references/fsq-mac-commands.md
~/.claude/skills/fsq-mac-qa/references/issue-taxonomy.md
~/.claude/skills/fsq-mac-qa/templates/acceptance-report.md
~/.claude/skills/fsq-mac-qa/templates/qa-checklist.md
```

**Step 2: Verify no broken cross-references**

Check that SKILL.md references the correct relative paths:
- `references/fsq-mac-commands.md` — referenced in error recovery section
- `references/acceptance-sop.md` — referenced in mode sections
- `references/issue-taxonomy.md` — referenced in explore mode section
- `templates/qa-checklist.md` — referenced in acceptance mode step 0
- `templates/acceptance-report.md` — referenced in output section

```bash
grep -c "references/" ~/.claude/skills/fsq-mac-qa/SKILL.md
grep -c "templates/" ~/.claude/skills/fsq-mac-qa/SKILL.md
```

Expected: both return >= 2.

**Step 3: Verify all fsq-mac commands referenced are valid**

Cross-check that every `mac` command mentioned in the skill files matches the CLI reference:

```bash
grep -oh 'mac [a-z-]* [a-z-]*' ~/.claude/skills/fsq-mac-qa/references/fsq-mac-commands.md | sort -u
```

Compare against `docs/cli-reference.md` in the fsq-mac repo. All commands must exist.

**Step 4: Final commit if any fixes were made**

```bash
cd ~/Documents/github/fsq-mac
git add skills/fsq-mac-qa/
git diff --cached --stat
# Only commit if there are changes
git commit -m "Fix fsq-mac-qa skill after smoke test" || true
```

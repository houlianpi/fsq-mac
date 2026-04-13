# Acceptance Report — [App Name] [Version]

**Date:** YYYY-MM-DD
**Tester:** Claude (fsq-mac-qa skill)
**Build:** [commit hash / version / bundle ID]
**Platform:** macOS [version]
**PRD/Design:** [reference document, or "N/A — Explore mode"]
**Mode:** Acceptance / Explore / Regression

---

## Summary

| Metric | Value |
|--------|-------|
| Total items | XX |
| Pass | XX |
| Fail | XX |
| Pending | XX |
| Pass rate | XX% |
| P0 (critical) | X |
| P1 (high) | X |

**Verdict:** Accepted / Not Accepted / Conditional

> Pass criteria: >= 90% pass rate AND zero P0 issues.

---

## Verification Results

<!-- One subsection per category tested.
     Acceptance mode: use the checklist categories (First Launch, Main Windows, etc.).
     Explore mode: group by discovered screens/areas. -->

### 1. [Category Name]

| # | Item | Result | Screenshot | Notes |
|---|------|--------|------------|-------|
| 1.1 | [description] | [Pass/Fail/Pending] | [link] | [details] |
| 1.2 | [description] | [Pass/Fail/Pending] | [link] | [details] |

<!-- Repeat subsections for each category:
### 2. [Category Name]
### 3. [Category Name]
... -->

#### Design vs Actual

<!-- Include this subsection only in Acceptance mode when a design spec is available. -->

| Design | Actual |
|--------|--------|
| ![design](./qa-screenshots/<round>/design-<section>.png) | ![actual](./qa-screenshots/<round>/actual-<section>.png) |

---

## Issues Found

<!-- Each issue uses the block format below. Number sequentially: ISSUE-001, ISSUE-002, etc.
     Interactive/behavioral issues require full repro with trace + step-by-step screenshots.
     Static/visible-on-load issues require a single screenshot. -->

### ISSUE-001: [Title]

| Field | Value |
|-------|-------|
| Severity | critical / high / medium / low |
| Category | Functional / Visual / UX / Content / Menu-Shortcut / Accessibility |
| Window | [current window title] |
| Trace | [trace path, if interactive issue] |

**Description**: What's wrong — expected behavior vs actual behavior.

**Repro Steps**:
1. `mac app launch com.example.app`
2. `mac element click e3` -> ![step2](./qa-screenshots/<round>/ISSUE-001-step2.png)
3. `mac element type e5 "test"` -> ![step3](./qa-screenshots/<round>/ISSUE-001-step3.png)
4. Expected X, got Y -> ![step4](./qa-screenshots/<round>/ISSUE-001-step4.png)

<!-- ### ISSUE-002: [Title]
     ... repeat block format for each issue ... -->

---

## Pending Items

| # | Item | Reason | When to verify |
|---|------|--------|----------------|
| [X.X] | [description] | [e.g., needs specific device / time-dependent / blocked by bug] | [next round / after fix] |

---

## Conclusion

[1-2 sentences: overall quality assessment, key blockers if any, recommendation for next steps.]

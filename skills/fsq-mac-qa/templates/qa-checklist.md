# QA Acceptance Checklist

## Verification Method
- **App**: [App Name / Bundle ID]
- **Platform**: macOS [version]
- **Method**: fsq-mac CLI automation
- **Screenshots**: `qa-screenshots/<round>/`
- **Session**: `mac session start`

## 1. First Launch
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 1.1 | App opens without crash | :hourglass_flowing_sand: | | |
| 1.2 | Initial window state is correct | :hourglass_flowing_sand: | | |
| 1.3 | Permission dialogs handled cleanly | :hourglass_flowing_sand: | | |

## 2. Main Windows
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 2.1 | Primary window renders fully | :hourglass_flowing_sand: | | |
| 2.2 | Window title is correct | :hourglass_flowing_sand: | | |
| 2.3 | Window size and position are reasonable | :hourglass_flowing_sand: | | |

## 3. Core Interactions
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 3.1 | Buttons respond to clicks | :hourglass_flowing_sand: | | |
| 3.2 | Forms accept and validate input | :hourglass_flowing_sand: | | |
| 3.3 | Navigation between views works | :hourglass_flowing_sand: | | |

## 4. Menu Bar
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 4.1 | All top-level menus reachable | :hourglass_flowing_sand: | | |
| 4.2 | Menu items trigger correct behavior | :hourglass_flowing_sand: | | |
| 4.3 | No incorrectly grayed-out items | :hourglass_flowing_sand: | | |

## 5. Keyboard Shortcuts
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 5.1 | Cmd+S / Cmd+Z / Cmd+C / Cmd+V work | :hourglass_flowing_sand: | | |
| 5.2 | Cmd+Q quits, Cmd+W closes window | :hourglass_flowing_sand: | | |
| 5.3 | Cmd+N opens new window/document | :hourglass_flowing_sand: | | |

## 6. Multi-Window
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 6.1 | Multiple windows can be opened | :hourglass_flowing_sand: | | |
| 6.2 | Focus switching between windows works | :hourglass_flowing_sand: | | |
| 6.3 | Window list reflects all open windows | :hourglass_flowing_sand: | | |

## 7. Data / Persistence
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 7.1 | Data saves correctly | :hourglass_flowing_sand: | | |
| 7.2 | State survives app restart | :hourglass_flowing_sand: | | |
| 7.3 | No data loss on normal close | :hourglass_flowing_sand: | | |

## 8. Design Fidelity
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 8.1 | Colors and fonts match spec | :hourglass_flowing_sand: | | |
| 8.2 | Spacing and layout match spec | :hourglass_flowing_sand: | | |

## 9. Accessibility
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 9.1 | All elements have roles and labels in UI tree | :hourglass_flowing_sand: | | |
| 9.2 | Keyboard navigation reaches all controls | :hourglass_flowing_sand: | | |

## 10. Edge Cases
| # | Verification Item | Result | Screenshot | Notes |
|---|-------------------|--------|------------|-------|
| 10.1 | Empty states display correctly | :hourglass_flowing_sand: | | |
| 10.2 | Boundary values handled gracefully | :hourglass_flowing_sand: | | |
| 10.3 | Kill/restart recovers without corruption | :hourglass_flowing_sand: | | |

## Result Legend
Pass = verified with screenshot evidence | Fail = screenshot + file issue | Pending = blocked, describe in Notes

## Pass Criteria
Pass rate >= 90% (default; user may override threshold), zero P0 issues (crashes, data loss, core flow broken), all fails documented with screenshots.

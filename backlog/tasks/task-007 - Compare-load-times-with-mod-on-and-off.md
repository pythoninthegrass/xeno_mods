---
id: TASK-007
title: Compare load times with mod on and off
status: In Progress
assignee: []
created_date: '2026-10-05 04:10'
updated_date: '2026-10-05 07:40'
labels: []
dependencies:
  - TASK-006
priority: medium
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 6 of docs/PLAN.md. Repeat the baseline protocol with the mod on and off, same save, at least twice each. Report cold and warm numbers against the 19 to 22 s gap and 40 s total.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 At least two runs per condition, cold and warm
- [x] #2 Results table added to docs/load-time-report.md
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Four cold menu-loaded runs (run11/12 mod on, run13/14 mod off). Intro to setup mean 20.08 s on vs 22.54 s off (-2.46 s); queue to playable 39.88 s vs 42.06 s (-2.18 s). Results table in docs/load-time-report.md. AC #1 open: warm loads not measured. scripts/run.py does one cold load per launch, so a warm arm needs a second in-session load (menu return plus reload clicks, not yet proven). Menu route via osascript worked end to end through run.py. contentpacks.json restored to mod enabled. log4net.xml still DEBUG, to be restored when measuring is finished.
<!-- SECTION:NOTES:END -->

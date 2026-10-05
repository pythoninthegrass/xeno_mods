---
id: TASK-007
title: Compare load times with mod on and off
status: Done
assignee: []
created_date: '2026-10-05 04:10'
updated_date: '2026-10-05 14:38'
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
- [x] #1 At least two runs per condition, cold and warm
- [x] #2 Results table added to docs/load-time-report.md
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Four cold menu-loaded runs (run11/12 mod on, run13/14 mod off). Intro to setup mean 20.08 s on vs 22.54 s off (-2.46 s); queue to playable 39.88 s vs 42.06 s (-2.18 s). Results table in docs/load-time-report.md. AC #1 open: warm loads not measured. scripts/run.py does one cold load per launch, so a warm arm needs a second in-session load (menu return plus reload clicks, not yet proven). Menu route via osascript worked end to end through run.py. contentpacks.json restored to mod enabled. log4net.xml still DEBUG, to be restored when measuring is finished.

AC #1 closed 2026-10-05: added scripts/run.py --warm-loads N (test first, 44 tests pass), which reloads the baseline save through the in-game menu without restarting. Runs 20 and 21 (mod off) and 22 and 23 (mod on), each one cold plus two warm loads. Warm intro to setup 23.36 s off vs 20.72 s on (-2.64 s); warm queue to playable 35.12 s vs 32.27 s (-2.85 s). Cold means over all 8 cold runs: -2.30 s and -2.18 s. The pre-setup gap does not shrink warm. A save made with the mod on prompts Missing Content when loaded with the mod off, so warm loads use the baseline save. log4net.xml restored from log4net.xml.orig and contentpacks.json has the mod enabled.
<!-- SECTION:NOTES:END -->

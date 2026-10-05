---
id: TASK-010
title: Exhaust load-time optimization paths available to a mod
status: To Do
assignee: []
created_date: '2026-10-05 15:29'
labels:
  - load-time
dependencies: []
priority: medium
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: find out how much of the roughly 40 s cold (32 to 35 s warm) ground-combat load of Xenonauts 2 under CrossOver on macOS can be removed by a code mod, and ship every change that helps.

Context a new agent needs:
- Read docs/PLAN.md, docs/load-time-report.md and docs/automated-runs.md first. The mod is src/x2_load_profiler (Harmony patches), tests in tests/x2_load_profiler.tests, measurement tool is scripts/run.py (cold load via the main menu, `--warm-loads N` for in-session reloads).
- State so far: a 19 to 22 s silent gap precedes `LoadScreen, Handling Setup for GroundCombat`. TASK-006 raised the concurrent asset bundle load cap from 25 to 200 and TASK-007 measured the gain: about 2.3 to 2.6 s (11%) off that gap, cold and warm. The gap does not shrink on warm loads. It is bound by per-bundle latency, not per-frame polling (UpdateTasks is 4 to 6% of wall time). Each load fetches 8808 asset bundle files, 5497 of them inside the gap. After setup, roughly 20 s cold (11 s warm) remain before the game is playable, undiagnosed, with hitches near +30, +35 and +38 s.
- Caveat on all existing numbers: they were measured with log4net at DEBUG (AssetTask at WARN), which is not the shipping configuration.
- Constraint: only changes a mod can deliver. Edits to game files (optimizing.json, log4net.xml, Assembly-CSharp.dll, bundles) are overwritten by Steam verify or updates, so they are test aids, never the deliverable. Restore any game file you change after measuring (guarded by scripts/run.py).
- Measurement protocol for any claim: same baseline save, mod on and off, at least 2 cold and 2 warm loads per condition via scripts/run.py, compare intro-to-setup and queue-to-playable, error and state-loss counts must match the baseline (5 and 20 per load).

This parent tracks the subtasks, each of which answers one question and either ships a measured improvement or records why the path is closed. The last subtask consolidates the winners.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every subtask is Done, with a recorded outcome of shipped or closed with evidence
- [ ] #2 docs/load-time-report.md lists every path explored, the measured effect and the decision
- [ ] #3 The shipped mod contains only changes with a measured benefit and no regression in errors or state-loss
<!-- AC:END -->

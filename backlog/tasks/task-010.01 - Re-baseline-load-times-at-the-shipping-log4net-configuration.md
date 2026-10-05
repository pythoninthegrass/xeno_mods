---
id: TASK-010.01
title: Re-baseline load times at the shipping log4net configuration
status: Done
assignee:
  - claude
created_date: '2026-10-05 15:30'
updated_date: '2026-10-05 23:00'
labels:
  - load-time
dependencies: []
parent_task_id: TASK-010
priority: high
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first for context and the measurement protocol. All numbers so far were measured with Assets/Configuration/log4net.xml at DEBUG (AssetTask at WARN). The shipping file (kept as log4net.xml.orig in the same folder) sets ERROR and a shorter pattern, so real players pay far less logging cost and the gap and the mod's gain may differ. Measure mod off and mod on with the shipping configuration so every later decision is made against numbers players actually see. The run.py readiness and timing markers come from log lines, so work out which markers survive at ERROR (the profiler mod's own per-second lines may be the only timing source) and make scripts/run.py work at that level without editing game files permanently.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Mod off and mod on, at least 2 cold and 2 warm loads each, measured with the shipping log4net configuration
- [x] #2 scripts/run.py reports intro-to-setup and queue-to-playable at the shipping log level, with new logic covered by tests written first
- [x] #3 docs/load-time-report.md gains a table comparing DEBUG and shipping-level numbers and states whether the TASK-006 gain still holds
- [x] #4 log4net.xml is restored to its original state after the measurements
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Confirm game log4net.xml equals log4net.xml.orig (shipping ERROR config) and that INFO markers and mod WARN lines are absent from output.log at that level.
2. New timing-only mod (separate pack, no cap patch or profiler) with Harmony postfixes at the sites that emit Queued LoadGameCommand, LoadScreen Intro Complete, LoadScreen Handling Setup, LoseFocus and GCUI BlockOnLocalPlayerTurn; each appends a timestamped line to Mods/<timing mod>/markers.txt through a plain StreamWriter (no log4net). Unit tests first for the line format and writer.
3. scripts/run.py: tests first, then parse markers.txt into the same Timings type when output.log lacks the markers; archive markers.txt with the run logs; keep the config-guard hash check (log4net.xml must stay at shipping state).
4. Measure mod off (cap patch disabled, timing mod on) and mod on, 2 cold plus 2 warm each via scripts/run.py --load menu --warm-loads 2, at the shipping config; check errors 5 and state-loss 20 per load.
5. Add DEBUG vs shipping comparison table to docs/load-time-report.md with a verdict on whether the TASK-006 gain holds; update docs/automated-runs.md.
6. Verify log4net.xml hash equals .orig after the runs.
Approved by Lance in session: mod-owned marker file, separate timing-only mod, autonomous game runs.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped: new x2_load_timing mod writes load markers to Mods/x2_load_timing/markers.txt independent of log level; scripts/run.py reads it (tests first, 52 Python and 45 .NET tests green), raises the game window before menu clicks, and archives markers with each run. Measured 2 launches per arm (2 cold + 4 warm loads each) at the shipping log4net config: mod gain at shipping level is 3.0 to 4.9 s (9 to 15%), at least as large as the DEBUG result, so the TASK-006 gain holds. Errors 5 per load unchanged; state-loss is 10 per load at shipping level in both arms. log4net.xml was never modified (identical to .orig). Results and caveats are in docs/load-time-report.md; markers in docs/baseline/shipping. Note: mod-off intro-to-setup is about 1.5 s longer than at DEBUG; host load affects results (keep the display awake and idle).
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-010.01
title: Re-baseline load times at the shipping log4net configuration
status: To Do
assignee: []
created_date: '2026-10-05 15:30'
updated_date: '2026-10-05 17:55'
labels:
  - load-time
dependencies:
  - TASK-011
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
- [ ] #1 Mod off and mod on, at least 2 cold and 2 warm loads each, measured with the shipping log4net configuration
- [ ] #2 scripts/run.py reports intro-to-setup and queue-to-playable at the shipping log level, with new logic covered by tests written first
- [ ] #3 docs/load-time-report.md gains a table comparing DEBUG and shipping-level numbers and states whether the TASK-006 gain still holds
- [ ] #4 log4net.xml is restored to its original state after the measurements
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-10-05 17:55
---
Measurement has moved from macOS/CrossOver to a Linux host running the game under Proton (AlmaLinux, steam-headless container, AMD 780M iGPU, 1920x1080 over noVNC). The existing numbers in docs/load-time-report.md were taken on macOS under CrossOver with Rosetta translation and are not comparable to anything measured on Linux. This re-baseline is therefore a Linux re-baseline: treat the macOS numbers as a separate, historical arm and label both arms by platform in the report. TASK-011 ports scripts/run.py to Linux and must land before this task can run.
---
<!-- COMMENTS:END -->

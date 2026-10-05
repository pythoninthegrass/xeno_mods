---
id: TASK-010.10
title: Measure Mono JIT and first-call cost during the load
status: To Do
assignee: []
created_date: '2026-10-05 15:30'
updated_date: '2026-10-05 15:30'
labels:
  - load-time
dependencies:
  - TASK-010.01
parent_task_id: TASK-010
priority: medium
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. The game runs on Mono (JIT) under Rosetta translation, where compiling managed methods is expensive, and a cold load is about 7 s slower than a warm one in the same session. A candidate cause is first-call JIT compilation of the load path's methods (including generic instantiations). Measure how much of a cold load is JIT time (for example by comparing the first and second load per method with stopwatch instrumentation, or Mono's profiler and runtime statistics if exposed), and test pre-compiling the load path from a background thread at menu time (RuntimeHelpers.PrepareMethod over the methods a ground combat load will call, discovered from a call trace). Check what is in Mono configuration files that a mod can change versus not.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 JIT time during a cold load versus a warm load is measured and reported in seconds
- [ ] #2 Background pre-compilation at menu time is implemented and measured, or closed with the numbers showing it cannot help
- [ ] #3 Any menu-time cost or instability from pre-compilation is measured and reported
- [ ] #4 Errors and state-loss counts match the baseline in every measured run
<!-- AC:END -->

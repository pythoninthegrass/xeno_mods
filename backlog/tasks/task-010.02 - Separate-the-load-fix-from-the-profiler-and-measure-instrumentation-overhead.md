---
id: TASK-010.02
title: Separate the load fix from the profiler and measure instrumentation overhead
status: To Do
assignee: []
created_date: '2026-10-05 15:30'
labels:
  - load-time
dependencies: []
parent_task_id: TASK-010
priority: medium
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. The shipped fix (bundle cap patch) lives in the same mod as the per-second profiler, whose UpdateTasks and CanStart patches cost time themselves. The mod-on versus mod-off comparison therefore understates the fix by the profiler's overhead, and a player should not run profiler patches. Make the instrumentation switchable independently of the fix (default off for the fix-only configuration), then measure fix only versus fix plus profiler versus neither. Decide whether the mod should be split into a fix mod and a profiler mod, or stay one mod with an opt-in switch, and document the decision.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Fix-only, fix plus profiler and neither are each measured with at least 2 cold and 2 warm loads
- [ ] #2 The profiler can be disabled without disabling the fix, with tests written first for the switch logic
- [ ] #3 The overhead of the profiler patches is reported in docs/load-time-report.md
- [ ] #4 The decision on one mod versus two is documented
<!-- AC:END -->

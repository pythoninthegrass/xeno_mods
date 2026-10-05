---
id: TASK-010.02
title: Separate the load fix from the profiler and measure instrumentation overhead
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-05 15:30'
updated_date: '2026-10-05 23:09'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: ProfilerSwitch.Parse(string?) defaulting to off (missing file, true/false, whitespace, garbage -> off); confirm failing.
2. Implement ProfilerSwitch; read profiler.txt in the lifecycle Create; gate UpdateTasksPatch, BundleCanStartPatch, BundleStartPatch, BundleUpdatePatch with [HarmonyPrepare]. Fix patch and AutoLoad untouched.
3. Measure neither / fix only / fix plus profiler: scripts/run.py --load menu --warm-loads 2, 2 launches each (2 cold + 4 warm), shipping log4net, timing mod on, caffeinate -d, same baseline save, errors 5 per load.
4. Report profiler overhead and the one-mod-versus-two decision in docs/load-time-report.md (recommendation: one mod with opt-in switch unless overhead is large); document the flag in docs/automated-runs.md.
5. Conventional commits, no attribution.
<!-- SECTION:PLAN:END -->

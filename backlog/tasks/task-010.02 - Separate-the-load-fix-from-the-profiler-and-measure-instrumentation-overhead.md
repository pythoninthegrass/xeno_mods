---
id: TASK-010.02
title: Separate the load fix from the profiler and measure instrumentation overhead
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 15:30'
updated_date: '2026-10-05 23:32'
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
- [x] #1 Fix-only, fix plus profiler and neither are each measured with at least 2 cold and 2 warm loads
- [x] #2 The profiler can be disabled without disabling the fix, with tests written first for the switch logic
- [x] #3 The overhead of the profiler patches is reported in docs/load-time-report.md
- [x] #4 The decision on one mod versus two is documented
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: ProfilerSwitch.Parse(string?) defaulting to off (missing file, true/false, whitespace, garbage -> off); confirm failing.
2. Implement ProfilerSwitch; read profiler.txt in the lifecycle Create; gate UpdateTasksPatch, BundleCanStartPatch, BundleStartPatch, BundleUpdatePatch with [HarmonyPrepare]. Fix patch and AutoLoad untouched.
3. Measure neither / fix only / fix plus profiler: scripts/run.py --load menu --warm-loads 2, 2 launches each (2 cold + 4 warm), shipping log4net, timing mod on, caffeinate -d, same baseline save, errors 5 per load.
4. Report profiler overhead and the one-mod-versus-two decision in docs/load-time-report.md (recommendation: one mod with opt-in switch unless overhead is large); document the flag in docs/automated-runs.md.
5. Conventional commits, no attribution.

Deviation from step 2: the game runs PatchAll before IModLifecycle.Create, so [HarmonyPrepare] could not see the switch. The gated patches lost their class-level [HarmonyPatch] attributes and are applied explicitly from Create by InstrumentationPatches.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added ProfilerSwitch (tests written first, 5 cases) and moved the profiler, bundle tracker, capture and auto-load patches out of PatchAll into InstrumentationPatches, applied from Create only when profiler.txt is true (auto-load when auto_load.txt exists). The bundle cap fix is unaffected. Measured neither, fix only and fix plus profiler with 2 launches each (2 cold, 4 warm loads per condition, run70-*): the fix removes 3.4 to 3.7 s cold and 1.8 to 2.1 s warm; the profiler adds about 1.3 to 1.5 s cold and nothing measurable warm. Verified gating through bundle_loads.tsv (0 bytes off, 1.9 MB on). Decision: one mod with an opt-in switch, documented in docs/load-time-report.md. Error and state-loss counts matched earlier runs in every launch. Caveat: the cold overhead figure is from 2 launches per arm with about 1.7 s spread.
<!-- SECTION:FINAL_SUMMARY:END -->

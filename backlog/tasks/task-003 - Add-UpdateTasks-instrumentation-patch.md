---
id: TASK-003
title: Add UpdateTasks instrumentation patch
status: In Progress
assignee:
  - claude
created_date: '2026-10-05 04:10'
updated_date: '2026-10-05 04:25'
labels: []
dependencies:
  - TASK-001
references:
  - docs/PLAN.md
priority: high
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 2 of docs/PLAN.md. Harmony prefix/postfix on Common.Content.Managers.ContentManager.UpdateTasks with a Stopwatch. Log one WARN line per second: frames, total ms in UpdateTasks, tasks in _processingTasks, tasks in _pendingTasks, tasks completed, wall-clock ms per frame. Hot path must not allocate. Write the aggregation (counters and per-second rollover) test-first, separate from the Harmony glue.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Aggregation unit tests written first and failing, then passing
- [ ] #2 Patch logs one WARN line per second during a load
- [x] #3 No allocations in the per-frame path
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved by Lance.

Layout (all files snake_case):
- src/x2_load_profiler/update_tasks_stats.cs: pure aggregator, no game or Harmony types. Per-frame Record(...) takes Stopwatch ticks and counts, returns true when a 1 s window has elapsed. A separate method fills a snapshot of the window numbers.
- src/x2_load_profiler/update_tasks_patch.cs: Harmony glue. Prefix stores Stopwatch.GetTimestamp() in a long __state. Postfix reads ticks, gets _processingTasks and _pendingTasks counts via injected private fields (___processingTasks, ___pendingTasks), calls Record, logs one WARN line on rollover.
- x2_load_profiler_lifecycle.cs (renamed from X2LoadProfilerLifecycle.cs): Create calls patcher.CreateClassProcessor(typeof(UpdateTasksPatch)).Patch().
- tests/x2_load_profiler.tests/: xunit on net10, links update_tasks_stats.cs via Compile Include (no game DLLs, no copy-to-game-folder target).

Tasks completed = drop in _processingTasks count across the call (count delta).

TDD order:
1. Write tests: counter accumulation, rollover at 1 s, reset after rollover, wall-clock ms per frame from frame gaps, completed-count delta, zero-frame window.
2. Run, confirm failing (AC1).
3. Implement minimal update_tasks_stats.cs, confirm passing.
4. Write glue, build mod, install into $DATA/Mods.
5. Load a save in game, check output.log for one WARN line per second (AC2).

No allocation (AC3): mutable fields on a single static instance, long/int arithmetic only per frame, no LINQ/closures/boxing/string work; string built only at rollover. Verified by a unit test using GC.GetAllocatedBytesForCurrentThread() around Record; glue verified by code review.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tests written first against a NotImplementedException stub: 11/11 failed. After implementing update_tasks_stats.cs: 11/11 pass (dotnet test in tests/x2_load_profiler.tests).

Glue in update_tasks_patch.cs patches private ContentManager.UpdateTasks; fields are Artitas.Utils.Bag<Common.Content.IAssetTask> (Count is a property, no enumeration). Mod builds and installs into $DATA/Mods/x2_load_profiler.

AC3: aggregator is allocation-checked by unit test; glue allocates only the log string once per second (reviewed, not measured in game).

AC2 open: needs an in-game save load to see one WARN line per second in $DATA/Logs/output.log. Lifecycle file renamed to snake_case per Lance.
<!-- SECTION:NOTES:END -->

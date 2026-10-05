---
id: TASK-003
title: Add UpdateTasks instrumentation patch
status: To Do
assignee: []
created_date: '2026-10-05 04:10'
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
- [ ] #1 Aggregation unit tests written first and failing, then passing
- [ ] #2 Patch logs one WARN line per second during a load
- [ ] #3 No allocations in the per-frame path
<!-- AC:END -->

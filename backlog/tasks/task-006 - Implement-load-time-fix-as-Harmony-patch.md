---
id: TASK-006
title: Implement load-time fix as Harmony patch
status: To Do
assignee: []
created_date: '2026-10-05 04:10'
labels: []
dependencies:
  - TASK-005
priority: high
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 5 of docs/PLAN.md. Candidates in order: skip polling tasks that cannot start yet (blocked by CanStart), cache the AreLoaded dependency check for pending tasks, raise effective concurrency without breaking ordering, remove per-call DEBUG log cost if it still shows. Test-first where logic is separable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Separable logic covered by tests written first
- [ ] #2 Same assets loaded and no new log errors
- [ ] #3 Game reaches a playable state and a save made after the load still loads
<!-- AC:END -->

---
id: TASK-006
title: Implement load-time fix as Harmony patch
status: In Progress
assignee: []
created_date: '2026-10-05 04:10'
updated_date: '2026-10-05 07:33'
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
- [x] #1 Separable logic covered by tests written first
- [x] #2 Same assets loaded and no new log errors
- [ ] #3 Game reaches a playable state and a save made after the load still loads
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Diagnosis (TASK-005) shows the gap is bound by per-bundle latency under the saturated 25-wide cap, and cap 200 cut intro-to-setup by 3.8 s. Candidates 1 and 2 (skip polling, cache AreLoaded) target about 4% of wall time and are not pursued. Implemented candidate 3: Harmony postfix on AssetBundleFileLoadOperation.CanStart that applies a mod-side cap (default 200, override via Mods/x2_load_profiler/bundle_cap.txt, 0 means unlimited, never lowers the game cap). Logic in bundle_concurrency.cs with 8 tests written first.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Run 10 (fix on, default cap 200, auto-load): intro to setup 20.33 s, queue to playable 40.40 s, 8808 bundle loads (same as runs 8 and 9), 5 errors and 20 state-loss, error lines identical to run 8. AC #3 half open: game reaches playable (BlockOnLocalPlayerTurn marker), but a save made after the load and reloaded has not been tested, because that needs in-game input. Needs Lance or an osascript save-and-reload step.
<!-- SECTION:NOTES:END -->

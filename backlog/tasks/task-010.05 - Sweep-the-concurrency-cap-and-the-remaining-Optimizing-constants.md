---
id: TASK-010.05
title: Sweep the concurrency cap and the remaining Optimizing constants
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
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. TASK-006 picked a cap of 200 from two single data points (25 and 200). Sweep the cap (for example 50, 100, 200, 400, unlimited) with repeated runs to find the best value, and test whether a non-constant policy helps (for example a high cap during the plateau and a lower one in the burst, or a cap that adapts to measured latency). Also test the other tunables in Constants.Optimizing that the game reads from optimizing.json: CM_FRAME_LOAD_BUDGET, PROMISE_HANDLING_BUDGET and STRATEGY_INITIALIZE_FRAME_BUDGET, applied from the mod (Harmony or reflection on the static fields) because editing optimizing.json is not deliverable. bundle_cap.txt in the mod folder is the existing override for the cap.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Cap sweep with at least 5 values and at least 2 cold loads each, tabulated with intro-to-setup and queue-to-playable
- [ ] #2 The other three constants are each tested from the mod at 3 or more values
- [ ] #3 The best combination becomes the mod default if it beats cap 200 beyond noise, with tests for any new logic written first
- [ ] #4 An adaptive cap is either implemented and measured or closed with the reason
<!-- AC:END -->

---
id: TASK-010.06
title: Audit the 8808 bundle loads for redundant or avoidable work
status: To Do
assignee: []
created_date: '2026-10-05 15:30'
labels:
  - load-time
dependencies: []
parent_task_id: TASK-010
priority: high
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. Every ground combat load fetches exactly 8808 asset bundle files, 5497 of them in the pre-setup gap, including strategy-layer textures and templates (in run 8, 247 strategy textures and 147 strategy templates were among the slow ones) even though the player is entering a tactical mission. The cheapest possible load is the one that never happens. Capture the full list of bundle loads (name, request time, size, requester or task type, whether it was loaded before in the same session, whether it was unloaded soon after) and classify them: needed for ground combat, needed only by the strategy layer, duplicate loads of the same bundle, loaded then released without use. Quantify how many loads and how many seconds each class accounts for.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A full bundle load list for one cold and one warm load is stored under docs/diagnosis
- [ ] #2 Each load is classified and the counts and estimated seconds per class are reported
- [ ] #3 Duplicate and load-then-release cases are identified by name
- [ ] #4 The report says which classes a mod could safely skip or defer and what evidence shows they are safe
<!-- AC:END -->

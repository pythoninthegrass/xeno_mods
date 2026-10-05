---
id: TASK-010.07
title: Skip or defer avoidable bundle loads
status: To Do
assignee: []
created_date: '2026-10-05 15:30'
updated_date: '2026-10-05 15:30'
labels:
  - load-time
dependencies:
  - TASK-010.01
  - TASK-010.06
parent_task_id: TASK-010
priority: high
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. Act on the classification produced by the bundle audit subtask: remove, share or postpone loads that the audit shows are redundant or not needed to reach a playable ground combat screen (for example answer a duplicate request from an already loaded bundle, or let strategy-only content load after the player is in control). Safety is the hard part: skipping something the game later needs must not cause missing assets, new errors, state loss or a corrupted save. Deferral changes ordering, so it needs the most validation. Do this one class at a time so a regression is attributable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each implemented class has tests written first for its decision logic
- [ ] #2 Each class is measured on its own with the full protocol and kept only if it gains beyond noise
- [ ] #3 Errors and state-loss counts match the baseline, no new log errors, and the loaded game plays and saves correctly (a save made afterwards reloads)
- [ ] #4 Returning to the strategy layer after the mission still works with deferred content, checked in game
<!-- AC:END -->

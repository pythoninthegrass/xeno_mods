---
id: TASK-010.04
title: Test Unity async upload and loading settings applied from the mod
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
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. Only Application.backgroundLoadingPriority has been tried (no effect). Untested Unity knobs that govern how much main-thread time asynchronous loading may use: QualitySettings.asyncUploadTimeSlice, asyncUploadBufferSize, asyncUploadPersistentBuffer, and any related QualitySettings or Physics and rendering settings that cost time while loading. Set them from the mod at startup (and again if the game resets them), sweep sensible values one at a time, and measure. The mod folder already has a unity_experiment.txt mechanism used for the backgroundLoadingPriority test; reuse it where it fits.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each setting is swept over at least 3 values with at least 2 cold loads per value, results tabulated
- [ ] #2 Any setting with a gain beyond run-to-run noise is implemented in the mod with tests where logic is separable and confirmed with the full protocol
- [ ] #3 Settings that do nothing are recorded as closed with the measured numbers
- [ ] #4 Whether the game overwrites each setting during load is checked and documented
<!-- AC:END -->

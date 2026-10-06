---
id: TASK-010.04
title: Test Unity async upload and loading settings applied from the mod
status: Done
assignee:
  - pythoninthegrass
created_date: '2026-10-05 15:30'
updated_date: '2026-10-06 14:29'
labels:
  - load-time
dependencies:
  - TASK-010.01
modified_files:
  - src/x2_load_profiler/unity_experiment_settings.cs
  - src/x2_load_profiler/unity_settings_guard.cs
  - src/x2_load_profiler/x2_load_profiler_lifecycle.cs
  - tests/x2_load_profiler.tests/unity_experiment_settings_tests.cs
  - docs/load-time-report.md
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
- [x] #1 Each setting is swept over at least 3 values with at least 2 cold loads per value, results tabulated
- [x] #2 Any setting with a gain beyond run-to-run noise is implemented in the mod with tests where logic is separable and confirmed with the full protocol
- [x] #3 Settings that do nothing are recorded as closed with the measured numbers
- [x] #4 Whether the game overwrites each setting during load is checked and documented
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach

The mod already applies `asyncUploadTimeSlice`, `asyncUploadBufferSize`, `asyncUploadPersistentBuffer` and `backgroundLoadingPriority` from `unity_experiment.txt` (untested sweep). Add `vSyncCount` and `targetFrameRate` (both already logged at startup, both can throttle frames during loading) with parser tests first. Add a log line of all values at every world create and dispose so the log shows whether the game overwrites a setting during load (AC #4).

## Sweep (Steam build on mf, cold auto runs via scripts/run.py, shipping log level, profiler off)

- Baseline: no experiment file, 3 cold runs.
- asyncUploadTimeSlice: 1, 4, 8, 16 ms (default recorded from the startup log), 2 cold runs each.
- asyncUploadBufferSize: 4, 16, 64, 256 MB around the recorded default, 2 cold runs each.
- asyncUploadPersistentBuffer: true/false, 2 cold runs each.
- vSyncCount 0 and targetFrameRate -1/0/240, 2 cold runs each.
- Interleave baseline runs through the sweep to expose drift. Compare intro-to-setup and queue-to-playable; errors 5 and state-loss 10 must match.
- Any gain beyond the baseline spread gets a confirmation with the full protocol (3 interleaved pairs) before being made a mod default.

## Record

Tables and closed/shipped decisions in docs/load-time-report.md. Stop rule: the same blocker surviving three distinct fix attempts is recorded in the notes and stops the task.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06. Key finding: the game itself writes asyncUploadTimeSlice 2->33 and backgroundLoadingPriority BelowNormal->High in LoadScreen.OnEnter and restores them in OnExit, so the earlier startup-only backgroundLoadingPriority=High test could not have changed anything. Added Harmony prefixes on the Unity setters (unity_settings_guard.cs) so swept values hold against the game's writes, plus a trace (flag file unity_settings_log.txt -> unity_settings.txt) with caller names. Added vSyncCount and targetFrameRate keys (parser tests first; the Resolve helper test was written together with its implementation, not seen failing first).

Sweep on Steam, 57 cold runs including 16 baselines: nothing beyond noise (baseline sd 0.52 s, range 20.54 to 22.20). vsync conditions looked 0.3 to 0.6 s faster in the sweep but a 6 against 6 interleaved confirmation gave +0.05 s. The host drifted about 1.5 s between the first runs of the day and the sweep. Boolean asyncUploadPersistentBuffer has only two values, so AC #1's three values cannot apply to it. Scratch data (tsv and traces) is in the session scratchpad, not the repo. Left-over flag files removed from the Steam mod folder.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Swept every Unity async loading setting the mod can reach and closed them all with measurements: no setting gives a gain beyond run-to-run noise. The sweep covered asyncUploadTimeSlice, asyncUploadBufferSize, asyncUploadPersistentBuffer, backgroundLoadingPriority, vSyncCount and targetFrameRate with 2 cold runs per value, 16 interleaved baselines and a 6-against-6 confirmation of the one group that looked faster. The game overwrites asyncUploadTimeSlice (2 to 33) and backgroundLoadingPriority (BelowNormal to High) on every load screen and restores them on exit; the other four are never written. To make swept values hold against those writes the mod now installs Harmony prefixes on the Unity setters (only when unity_experiment.txt or the trace flag exists) and can trace every setter call with its caller. Tests: 61 xunit tests pass (new parser and Resolve tests). Results and the decision are in docs/load-time-report.md. No shipped default changed; the baseline values are the game's own.
<!-- SECTION:FINAL_SUMMARY:END -->

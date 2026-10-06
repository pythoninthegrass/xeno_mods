---
id: TASK-010.04
title: Test Unity async upload and loading settings applied from the mod
status: Done
assignee:
  - pythoninthegrass
created_date: '2026-10-05 15:30'
updated_date: '2026-10-06 16:13'
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

2026-10-06 (reopened). The sweep recorded above is INVALID. The Harmony prefixes on the Unity setters (unity_settings_guard.cs, first version) stopped the original setters from running, so no swept value was ever stored: the traces' own readbacks at Create and WorldCreate(GroundCombat) show the defaults (asyncUploadTimeSlice=2 with 66 forced, vSyncCount=1 with 0 forced). The hooks also cost about 1.9 s per load (hooked 19.3 -> 21.2 s, bisected to the backgroundLoadingPriority hook). The 'no gain' conclusions and the report section are wrong and are being replaced after a rerun with the per-frame holder (fixed in the task-010.05 branch). Caught while using the same hooks for TASK-010.05, where cap 300 and 400 came out 8 to 10 s slower than the previous day's data.

2026-10-06 (rerun). Fixed holder (per-frame compare and re-apply from an UpdateTasks postfix, commit e48bbfa on task-010.05). Evidence the values now take effect: the trace readbacks at Create and WorldCreate(GroundCombat) show the forced values (priority Normal and slice 8 held while the game's own writes of High and 33 are overridden). Rerun: 36 sweep runs, 16 baselines, 5 control runs with the holder installed and a harmless value (equal to baseline), and a 12-run confirmation of the three borderline conditions. Baseline sd 0.21 s. Findings: priority Low doubles the load (38 s), BelowNormal +1.4 s, vSyncCount=2 +1.0 s, asyncUploadBufferSize=16 +1.2 s; all other values within 0.4 s of baseline and the borderline ones vanished on confirmation. asyncUploadTimeSlice is clamped by Unity to 1..33, so the game's 33 is the maximum. asyncUploadPersistentBuffer is boolean, so only two values exist for AC #1. Mistake log: the first sweep's conclusion was wrong because of the broken setter hooks; docs/load-time-report.md now holds only the valid results.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Swept the Unity async loading settings the mod can reach and closed them: none beats the game's own values. The game raises asyncUploadTimeSlice (2 to 33, Unity's maximum) and backgroundLoadingPriority (BelowNormal to High) on every load screen and restores them on exit; the other four settings are never written. The mod can now hold experiment values against those writes with a per-frame compare-and-reapply (installed only when unity_experiment.txt or the trace flag exists), plus a trace of every change. A first implementation patched the Unity setters with Harmony, which stopped the originals running; its sweep was invalid and is replaced. Valid results (Steam, cold auto-load, baseline 19.5 s, sd 0.21 s): priority Low 38.4 s, BelowNormal +1.4 s, vSyncCount 2 +1.0 s, asyncUploadBufferSize 16 +1.2 s, everything else within noise, with the three borderline conditions confirmed as noise in a 4-against-6 interleaved check. Tests: 66 xunit tests pass (parser, Resolve). Nothing changed in the shipped defaults.
<!-- SECTION:FINAL_SUMMARY:END -->

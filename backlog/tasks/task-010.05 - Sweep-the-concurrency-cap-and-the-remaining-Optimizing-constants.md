---
id: TASK-010.05
title: Sweep the concurrency cap and the remaining Optimizing constants
status: Done
assignee:
  - pythoninthegrass
created_date: '2026-10-05 15:30'
updated_date: '2026-10-06 17:13'
labels:
  - load-time
dependencies:
  - TASK-010.01
modified_files:
  - src/x2_load_profiler/bundle_concurrency.cs
  - src/x2_load_profiler/optimizing_experiment.cs
  - src/x2_load_profiler/optimizing_experiment_patch.cs
  - src/x2_load_profiler/unity_settings_guard.cs
  - src/x2_load_profiler/x2_load_profiler_lifecycle.cs
  - tests/x2_load_profiler.tests/optimizing_experiment_tests.cs
  - tests/x2_load_profiler.tests/bundle_concurrency_tests.cs
  - docs/load-time-report.md
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
- [x] #1 Cap sweep with at least 5 values and at least 2 cold loads each, tabulated with intro-to-setup and queue-to-playable
- [x] #2 The other three constants are each tested from the mod at 3 or more values
- [x] #3 The best combination becomes the mod default if it beats cap 200 beyond noise, with tests for any new logic written first
- [x] #4 An adaptive cap is either implemented and measured or closed with the reason
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Findings from the decompiled game (ilspycmd, tools/ is gitignored)

- `CM_FRAME_LOAD_BUDGET` (`Constants.Optimizing`, static readonly long, default 200) is copied into `AssetConfiguration.frameLoadBudget` and passed to private `ContentManager.UpdateTasks(long maxMilliseconds)`, where it only makes non-async tasks wait once the frame has used that many ms (0 means no limit).
- `PROMISE_HANDLING_BUDGET` (`XenonautsConstants.Optimizing`, static readonly int, default 10) is read on every call of `PhasedFSMSystem` per-frame loop and `SequentialProgressPromise.Update`: ms of world/promise processing per frame.
- `STRATEGY_INITIALIZE_FRAME_BUDGET` (same class, long, default 14) is the argument of `World.Initialize` in `StrategyScreen`.

## Approach

1. Cap: the Linux sweep of TASK-010.03 already has 25, 50, 100, 200, 400, 800 with 2 runs each (AC #1 data). Its 100/200/400 bottom is unresolved (0.1 to 0.4 s), so rerun 100, 150, 200, 300, 400 interleaved, 3 rounds, to resolve it.
2. Constants: new `optimizing_experiment.txt` in the mod folder (`NAME=value`, whitelist of the three names; parser and tests first). CM budget through a Harmony prefix on `UpdateTasks` (`ref long maxMilliseconds`); the two Xenonauts constants through reflection on the static readonly fields at mod create (before their consumers are JIT-compiled), with the read-back value traced. Sweep each at 4 values (CM 0, 50, 200, 1000; promise 2, 10, 30, 100, 1000; strategy 4, 14, 50, 200), 2 cold runs each, baseline interleaved.
3. Adaptive cap: decide from the measured per-cap curve whether a policy can beat the best fixed cap by more than noise; implement only if it can.
4. Best combination becomes the default only if it beats cap 200 beyond noise (interleaved confirmation), with tests first.

Stop rule: the same blocker surviving three distinct fix attempts is recorded in the notes and stops the task.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06. A first cap and constants sweep (44 runs) was taken while the broken Unity setter hooks of TASK-010.04 were installed and is discarded: caps 300 and 400 came out 8 to 10 s slower, contradicting the previous day's data, which exposed the hooks (see TASK-010.04 notes). Rerun with no flag file and no hooks: 44-run sweep, 21-run confirmation, 15-run final interleaved check, all errors 5 and state-loss 10.

Result: cap curve flat 100 to 400; PROMISE_HANDLING_BUDGET 100 is 0.5 s faster, 1000 is 2.2 s slower; CM_FRAME_LOAD_BUDGET and STRATEGY_INITIALIZE_FRAME_BUDGET do nothing measurable. Cap 300 plus promise budget 100: 18.73 s against 19.53 s baseline (five interleaved pairs), shipped build measured 18.56 to 18.78 s. Made the defaults (tests first; red seen as a compile error and a failing DefaultCap test). Not remeasured on macOS CrossOver; the U shape means a slower host may want cap 200. Adaptive cap closed with reasoning, not measured: the flat curve bounds its gain below noise. tools/ilspycmd was installed (gitignored) to read the game's code; the decompile is in the session scratchpad.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Swept the bundle concurrency cap (50, 100, 150, 200, 300, 400) and the three remaining Optimizing constants from the mod. The cap is flat from 100 to 400; PROMISE_HANDLING_BUDGET has a hill with its best near 100 (0.5 s faster; 1000 is 2.2 s slower); CM_FRAME_LOAD_BUDGET and STRATEGY_INITIALIZE_FRAME_BUDGET do nothing measurable. The best combination, cap 300 with PROMISE_HANDLING_BUDGET 100, is 0.80 s (4%) faster than cap 200 with game constants in five interleaved pairs, and is now the mod default; optimizing_experiment.txt applies the constants (frame budget by a prefix on UpdateTasks, the static readonly fields by reflection) and bundle_cap.txt still overrides the cap. Adaptive cap closed with reasoning. An earlier sweep was discarded because the TASK-010.04 setter hooks were installed; the rerun is clean. Tests: 69 xunit tests pass. Risks: measured on one Linux host only, macOS not remeasured, and a slower host may prefer a lower cap.
<!-- SECTION:FINAL_SUMMARY:END -->

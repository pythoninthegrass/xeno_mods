---
id: TASK-010.06
title: Audit the 8808 bundle loads for redundant or avoidable work
status: Done
assignee:
  - claude
created_date: '2026-10-05 15:30'
updated_date: '2026-10-05 23:05'
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
- [x] #1 A full bundle load list for one cold and one warm load is stored under docs/diagnosis
- [x] #2 Each load is classified and the counts and estimated seconds per class are reported
- [x] #3 Duplicate and load-then-release cases are identified by name
- [x] #4 The report says which classes a mod could safely skip or defer and what evidence shows they are safe
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend the profiler mod's bundle_load_patch to write one record per bundle load to its own file (name, request time, start time, done time, size if available, requester or task type, load count per name in session), written outside log4net so shipping log level is irrelevant. Tests first for the record format and per-name counting.
2. Capture one cold and one warm load with the baseline save; store under docs/diagnosis.
3. Classify loads with a script (tests first): needed for ground combat, strategy-only, duplicate, loaded-then-released (needs an unload hook or release evidence from decompiled ContentManager). Report counts and estimated seconds per class.
4. Name duplicates and load-then-release cases in the report.
5. Write which classes a mod could skip or defer and what evidence shows safety in docs/load-time-report.md.
Depends on the marker mechanism from TASK-010.01 only for run timing anchors.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added an opt-in per-load capture to x2_load_profiler (bundle_log.txt flag, writes bundle_loads.tsv with every load and unload) and scripts/analyze_bundles.py (tests first). Captured one cold and one warm load (run60) and stored slices under docs/diagnosis. Findings in docs/load-time-report.md: the 8808 figure is 2609 main-menu startup loads plus 6199 for the load itself, 5497 before setup; 2574 (47%, 75% of summed load time) of the pre-setup loads are assets released at load start and loaded again seconds later (all 6199 in the warm reload); strategy scope is 1864 (34%) of pre-setup loads, 1383 of them reloads; no duplicates or load-then-release inside a window. Skipping the unload of re-requested assets is the safe-looking candidate for TASK-010.07 (needs an errors/state-loss/save parity check); deferring the 481 strategy first loads is not supported without a read trace. Limits: the engine never sets LoadTask.parent so requester is not recoverable; per-asset size is not available (assets are read from resident bundles), bundle name is recorded instead; estimated seconds assume equal wall cost per load.
<!-- SECTION:FINAL_SUMMARY:END -->

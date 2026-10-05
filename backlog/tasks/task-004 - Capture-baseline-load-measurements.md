---
id: TASK-004
title: Capture baseline load measurements
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 04:10'
updated_date: '2026-10-05 04:40'
labels: []
dependencies:
  - TASK-003
references:
  - docs/load-time-report.md
modified_files:
  - docs/load-time-report.md
  - docs/baseline/run1-profiler.txt
  - docs/baseline/run2-profiler.txt
priority: high
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 3 of docs/PLAN.md. Restore optimizing.json to {} first. Fresh game launch, copy the chosen autosave somewhere safe, load the copy once without touching the window. Extract the pre-setup gap from log timestamps (Queued LoadGameCommand, LoadingWorld - Handled LoseFocusScreenReport, LoadScreen Handling Setup for GroundCombat, Creating promise BlockOnLocalPlayerTurn). Run at least twice.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 optimizing.json restored to {} before measuring
- [x] #2 At least two cold baseline runs recorded with gap, total and per-second profiler lines
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Quit the game fully (user).
2. Restore optimizing.json from optimizing.json.orig, diff to confirm {} (AC #1).
3. Copy auto_groundcombat_turn_10_start-62.json to a distinct name in Saves/ellz_1bf479e6/ (approved by user), record checksum.
4. Archive current output.log* so each run's log is isolated.
5. User launches the game, loads the copy once, leaves the window alone until playable (manual, per run).
6. Per run, extract from output.log: timestamps of Queued LoadGameCommand, LoadingWorld - Handled LoseFocusScreenReport, LoadScreen Handling Setup for GroundCombat, Creating promise BlockOnLocalPlayerTurn; pre-setup gap; click-to-playable total; per-second profiler WARN lines.
7. Repeat 1, 4, 5, 6 for at least two cold runs.
8. Add a Baseline (cap 25) section to docs/load-time-report.md; check off ACs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
optimizing.json restored from .orig and cmp-verified (game was still running; value is read at launch). Save copied to Saves/ellz_1bf479e6/user_baseline_turn10-3.json, sha256 ef7d2aeb7b8ed7d76bd403ea58536897daf7192dec2bf0af222e14aeb81ea388. Profiler dll in Mods/x2_load_profiler built 23:29:03.

Run 1 and run 2 recorded in docs/load-time-report.md: gap 21.35 s / 21.30 s, total 42.05 s / 42.92 s. Both runs loaded the auto/ autosave, not the copy (same sha256). Raw logs archived in game Logs/run1-baseline and run2-baseline.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Two cold baseline runs (cap 25, profiler mod on) recorded in docs/load-time-report.md with raw per-second profiler lines in docs/baseline/. Pre-setup gap 21.35 s and 21.30 s; queue to playable 42.05 s and 42.92 s. UpdateTasks accounted for about 6.7% of gap wall time in both runs. Interpretation left to the diagnosis step.
<!-- SECTION:FINAL_SUMMARY:END -->

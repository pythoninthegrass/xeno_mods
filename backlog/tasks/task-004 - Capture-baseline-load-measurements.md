---
id: TASK-004
title: Capture baseline load measurements
status: To Do
assignee: []
created_date: '2026-10-05 04:10'
labels: []
dependencies:
  - TASK-003
references:
  - docs/load-time-report.md
priority: high
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 3 of docs/PLAN.md. Restore optimizing.json to {} first. Fresh game launch, copy the chosen autosave somewhere safe, load the copy once without touching the window. Extract the pre-setup gap from log timestamps (Queued LoadGameCommand, LoadingWorld - Handled LoseFocusScreenReport, LoadScreen Handling Setup for GroundCombat, Creating promise BlockOnLocalPlayerTurn). Run at least twice.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 optimizing.json restored to {} before measuring
- [ ] #2 At least two cold baseline runs recorded with gap, total and per-second profiler lines
<!-- AC:END -->

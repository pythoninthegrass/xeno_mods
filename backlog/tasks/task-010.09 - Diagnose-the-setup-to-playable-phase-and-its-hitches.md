---
id: TASK-010.09
title: Diagnose the setup-to-playable phase and its hitches
status: To Do
assignee: []
created_date: '2026-10-05 15:30'
labels:
  - load-time
dependencies: []
parent_task_id: TASK-010
priority: high
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. After `LoadScreen, Handling Setup for GroundCombat`, about 20 s (cold) or 11 s (warm) still pass before the BlockOnLocalPlayerTurn marker, and run profiles show hitches near +30, +35 and +38 s after the load command. This half of the load has had no diagnosis. The game reports PhasedFSM timers for InitializeMap, Load and TurnControl.Begin (docs/load-time-report.md has cold and warm values). Determine what the time is: main-thread work in the game's phases, content still loading, garbage collection pauses (the hitches are suspicious for this) or shader and material warm-up. Add frame time and GC instrumentation to the mod (frame spikes with GC collection counts and the managed heap size, per-phase wall time) and map each hitch to a cause.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Per-second frame time, GC collection count and heap size are logged for the whole load
- [ ] #2 Each hitch near +30, +35 and +38 s is mapped to a cause with evidence
- [ ] #3 The time between setup and playable is split into named phases with seconds for cold and warm
- [ ] #4 A candidate fix a mod could apply is listed per cause, or the cause is recorded as outside a mod's reach
<!-- AC:END -->

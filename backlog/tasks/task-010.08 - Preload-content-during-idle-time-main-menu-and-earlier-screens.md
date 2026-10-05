---
id: TASK-010.08
title: Preload content during idle time (main menu and earlier screens)
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
priority: medium
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. The game sits idle on the main menu, and during a campaign the player is on the strategy screen for long periods, while the load that follows a click is dominated by loading the same content every time. Test whether work can move earlier: (1) populate the operating system file cache for the bundles a ground combat load will read, with a background thread reading the files; (2) start the game's own content loads for the common ground combat content ahead of the load command. The first is nearly free of ordering risk; the second changes load ordering. Measure the cold-versus-warm difference attributable to file caching first, since warm loads are about 7 s faster and it is unknown whether that is the file cache, Mono JIT or the game's own caches.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The share of the cold-versus-warm difference explained by the OS file cache is measured (for example by reading the bundles before a cold load)
- [ ] #2 File cache prefetch is implemented and measured, or closed with numbers
- [ ] #3 Game-level preloading is either implemented and validated for correctness (no new errors, same assets, saves load) or closed with the reason
- [ ] #4 Startup and menu responsiveness cost of any prefetch is measured and reported
<!-- AC:END -->

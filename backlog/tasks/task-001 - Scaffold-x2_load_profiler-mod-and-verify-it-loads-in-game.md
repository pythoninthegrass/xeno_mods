---
id: TASK-001
title: Scaffold x2_load_profiler mod and verify it loads in game
status: In Progress
assignee: []
created_date: '2026-10-05 04:10'
updated_date: '2026-10-05 04:11'
labels: []
dependencies: []
references:
  - docs/PLAN.md
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 1 of docs/PLAN.md. Mod project under src/x2_load_profiler builds with dotnet and installs into the game's Mods folder. Remaining: enable it from the in-game mod menu and confirm the log line.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Project builds with dotnet build -c Release on macOS
- [x] #2 Build installs DLL, PDB and manifest.json into Mods/x2_load_profiler
- [ ] #3 Mod enabled via the in-game mod menu
- [ ] #4 [X2LoadProfiler] Loaded appears in output.log
<!-- AC:END -->

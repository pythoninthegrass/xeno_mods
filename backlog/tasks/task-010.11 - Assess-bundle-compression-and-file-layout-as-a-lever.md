---
id: TASK-010.11
title: Assess bundle compression and file layout as a lever
status: To Do
assignee: []
created_date: '2026-10-05 15:30'
labels:
  - load-time
dependencies: []
parent_task_id: TASK-010
priority: low
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. If per-bundle cost is dominated by decompression or by many small file reads, the bundle format matters more than scheduling. Inspect the shipped asset bundles (compression type per bundle: LZMA, LZ4 or uncompressed; size distribution; count of tiny files) and test the effect on load time in isolation (for example a standalone load of the same bundles from a script or the mod measuring decompression time). Then decide feasibility from a mod's angle: can a mod ship or generate repacked or uncompressed copies and redirect the game to them without touching Steam-managed files, and is the disk and install-size cost reasonable. The expected outcome may be a closed, documented path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Compression type and size distribution of the bundles loaded in a ground combat load are tabulated
- [ ] #2 Decompression time per bundle is measured and its share of the plateau is reported
- [ ] #3 A feasibility statement says whether a mod can redirect bundle loading to repacked files, with evidence from the game code
- [ ] #4 If feasible and beneficial, a prototype is measured with the full protocol; otherwise the path is closed with the numbers
<!-- AC:END -->

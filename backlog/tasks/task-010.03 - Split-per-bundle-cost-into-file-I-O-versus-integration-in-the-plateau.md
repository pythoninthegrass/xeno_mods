---
id: TASK-010.03
title: Split per-bundle cost into file I/O versus integration in the plateau
status: To Do
assignee: []
created_date: '2026-10-05 15:30'
labels:
  - load-time
dependencies: []
parent_task_id: TASK-010
priority: high
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. In the pre-setup gap, throughput follows Little's law: a plateau of about 13 s at about 35 completions per second (each bundle takes 0.4 to 1 s) and a burst of about 5 s at 500 to 900 per second (20 to 80 ms each). Raising concurrency raised latency almost proportionally, so something serialized sits behind each load. Find out where one bundle's time goes: reading the file from disk through Wine, decompression, or Unity's integration step on the main thread. Add instrumentation (Harmony on the bundle load operation and its completion) that records per bundle the time from request to file read done to integrated, plus file size and compression, and identify what separates plateau bundles from burst bundles.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Per-bundle timing split into at least read and integrate phases is captured for a full load
- [ ] #2 The report names which phase dominates the plateau and which bundle properties (size, compression, type) predict slow loads
- [ ] #3 Findings and raw data under docs/diagnosis are linked from docs/load-time-report.md
- [ ] #4 The next optimization this suggests, or a statement that none exists from a mod, is recorded on this task
<!-- AC:END -->

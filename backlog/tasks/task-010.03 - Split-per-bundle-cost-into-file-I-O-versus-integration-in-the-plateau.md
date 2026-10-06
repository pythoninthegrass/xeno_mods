---
id: TASK-010.03
title: Split per-bundle cost into file I/O versus integration in the plateau
status: In Progress
assignee: []
created_date: '2026-10-05 15:30'
updated_date: '2026-10-06 01:23'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Findings that shape the approach (from decompiled Assembly-CSharp.dll, 2026-10-05):
- Bundle files are opened once per content pack at index time (ContentPackState.CreateIndex, AssetBundle.LoadFromFileAsync), so every bundle is resident before any load. There is no per-bundle file open in the plateau.
- Each AssetBundleFileLoadOperation is one AssetBundle.LoadAssetAsync(relativePath) on a resident bundle. Unity splits that internally into async read and decompress, deserialize on the preload thread, and integrate on the main thread. The managed API only exposes request-to-start and start-to-done, so read versus integrate cannot be timed from inside Assembly-CSharp alone.
- The game runs natively on this Linux host under Proton (Steam at /media/steam, game at /media/steam/steamapps/common/Xenonauts2, prefix at compatdata/538030/pfx), so Linux can observe the Wine process from outside.

Plan:
1. Run environment: set the Linux overrides in .env (BOTTLE, GAME_DIR, DATA_DIR, WINE_USER, LAUNCH_CMD, STEAM_CONSOLE_LOG) for the /media/steam layout and verify a baseline scripts/run.py auto-load run works on this host.
2. Phase split from outside, per thread: sample /proc/<pid>/task/*/stat (CPU ticks and state) every 100 ms through the plateau and burst, keyed by thread name (Unity names Loading.AsyncRead, Loading.PreloadManager and the main thread; check that Wine exposes them). Pair with read syscalls on the bundle files (perf trace or bpftrace, not strace, to keep overhead low) for bytes read and I/O time. Write the sampler as scripts/sample_threads.py, test-first on the parsing and aggregation.
3. Phase split from inside: extend the capture so each L record also carries a first-progress frame time (AssetBundleRequest.progress sampled from the Update postfix) in addition to request-to-start and start-to-done, test-first in BundleRecord. Treat as an experiment: if progress only jumps 0 to 1 it gives no split and the finding is recorded as such.
4. Bundle properties: join each load's bundle name to on-disk size and the UnityFS header compression flag (LZ4, LZMA or none) read from the bundle files, plus asset type, with a script (extend scripts/analyze_bundles.py, test-first), and report which properties predict start-to-done in plateau versus burst.
5. Full cold load with the profiler on, archive raw data under docs/diagnosis/run8x-*, write the findings section in docs/load-time-report.md linking the data, record the next optimization (or that none exists from a mod) on this task.

Constraints: measurement timings are not used for speed claims (instrumentation overhead is about 1.3 to 1.5 s cold). Restore any game file touched. No game files are edited.
<!-- SECTION:PLAN:END -->

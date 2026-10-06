---
id: TASK-010.03
title: Split per-bundle cost into file I/O versus integration in the plateau
status: Done
assignee: []
created_date: '2026-10-05 15:30'
updated_date: '2026-10-06 19:54'
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
- [x] #1 Per-bundle timing split into at least read and integrate phases is captured for a full load
- [x] #2 The report names which phase dominates the plateau and which bundle properties (size, compression, type) predict slow loads
- [x] #3 Findings and raw data under docs/diagnosis are linked from docs/load-time-report.md
- [x] #4 The next optimization this suggests, or a statement that none exists from a mod, is recorded on this task
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-05, Linux results (host runs under Proton, not the macOS CrossOver case). Written up in docs/load-time-report.md (section Where a bundle load's time goes), raw data docs/diagnosis/run89-cap0-* and run90-cap200-*. Code: scripts/sample_threads.py (per-thread CPU from /proc, 15 tests) and profile.txt output in x2_load_profiler (ProfileLine, 2 tests; 56 tests pass).

Findings: bundle files are resident before any load, so each of the 8808 loads is one LoadAssetAsync on a resident bundle. File reading is not a cost (Loading.AsyncRead 0.75 to 0.79 s CPU, zero disk-wait samples). With the shipped cap 200 the pre-setup gap is 5.9 s with main-thread CPU 3.9 s; with no cap it is 18.1 s with main-thread CPU 15.4 s while UpdateTasks stays at 1.8 to 2.0 s, so the extra time is engine-side main-thread work that grows with the number of in-flight requests, not managed polling.

Next optimization this suggests: a cap sweep (TASK-010.05) on Linux, 50 to 800, since neither the main thread nor the deserialize thread is saturated at 200 and loads wait up to 4.4 s for a slot. Whether it transfers to macOS needs the same sweep there.

Still open against the acceptance criteria: AC #1 (a per-load read versus integrate split; only a per-thread split exists, and the AssetBundleRequest.progress experiment is not done), AC #2 (bundle size and compression as predictors are not measured), and the macOS plateau has not been sampled.

2026-10-05, cap sweep on Linux (profiler off, 2 runs per cap, documented in docs/load-time-report.md under Cap sweep on Linux). Intro to setup means: cap 25 8.49 s, 50 6.63 s, 100 5.84 s, 200 5.94 s, 400 6.26 s, 800 8.05 s; unlimited about 18 s (profiler on). The curve has a flat bottom from 100 to 400 that these runs cannot resolve, so the shipped 200 stays and the cap is not a remaining lever on Linux. This closes the 'next optimization' suggested by the thread split and replaces it: the remaining lever is doing fewer loads, since main-thread work rises with load volume and the TASK-010.06 audit found 2574 of the 5497 pre-setup loads are re-loads of assets released at load start. That is TASK-010.07. On macOS the cap sweep has not been run.

2026-10-06, per-load split and bundle properties (commit 6bad429). Capture L lines gain two columns (first nonzero AssetBundleRequest.progress to done, and that first value). Run 93 (cold, profiler and capture on, cap 200, docs/diagnosis/run93-progress-*): progress is 0 then 1.0, and 1.0 is held for a mean 109 ms (fast loads) to 268 ms (slow loads), about 55% of start-to-done, while the load waits for main-thread integration. 63% of loads finish within one frame of progress 1.0. Bundle properties (scripts/analyze_bundles.py --bundle-dir): all 323 bundles are LZ4HC so compression predicts nothing; size is a mild predictor under cap 200 (18% slow at 1 MB or larger, 12% at 64 KB to 1 MB, 0% under 64 KB) and none without the cap (98% slow in every large bucket). The progress sampling itself adds overhead (6.2 s vs 5.9 s intro to setup), so proportions only. AC #4: the lever the split points to is main-thread integration volume, which is fewer loads (TASK-010.07); there is no further mod-side lever on the cap (TASK-010.05). macOS remains unsampled.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a per-load phase split and bundle-property analysis for the plateau. Capture L lines now carry the first nonzero AssetBundleRequest.progress time and value; BundleRecord (tests first, 69 tests pass) and BundleUpdatePatch sample Progress() per frame while capture is on. scripts/analyze_bundles.py reads UnityFS headers (size, compression) and prints slow-versus-fast tables by size, compression and asset type (18 Python tests). Findings in docs/load-time-report.md (Bundle properties against slow loads, Per-load split from progress), raw data docs/diagnosis/run93-progress-*. Result: file reading is not a cost, about 55% of a load's time is the wait for main-thread integration after the worker threads finish, compression is uniform (LZ4HC), size is a weak predictor only under the cap. Next lever is fewer loads (TASK-010.07). Risks: progress sampling perturbs timing (about 0.3 s), per-frame resolution, macOS not sampled.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-005
title: Diagnose the pre-setup content-loading gap
status: To Do
assignee: []
created_date: '2026-10-05 04:10'
updated_date: '2026-10-05 04:55'
labels: []
dependencies:
  - TASK-004
priority: high
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Step 4 of docs/PLAN.md. From the per-second lines decide whether the cost is per-frame polling, throttled completions per frame, or individual load and post-processing steps (JSON parse, deserialize, LoadProcessTask chain). State the finding with numbers in docs/load-time-report.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Finding stated with numbers in docs/load-time-report.md
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
STATUS: DRAFT, NOT YET APPROVED. Lance asked for the plan to be drafted and recorded for a different agent to take over. Present it to Lance and get explicit approval before touching code (step 2 extends the profiler, which is beyond reading existing logs). Do not mark In Progress until the next agent starts.

CONTEXT FOR HANDOFF
- Read docs/PLAN.md and docs/load-time-report.md (including the new "Baseline with profiler (cap 25)" section) first. Raw per-second profiler lines: docs/baseline/run1-profiler.txt, run2-profiler.txt.
- Baseline (TASK-004): pre-setup gap 21.35 s / 21.30 s, queue-to-playable 42.05 s / 42.92 s. Inside the gap UpdateTasks used about 6.7% of wall time (1347 / 1310 ms over ~20 s), frames were about 17 ms (about 60 fps), 4070 / 4017 tasks completed.
- Profiler mod: src/x2_load_profiler (Harmony prefix/postfix on ContentManager.UpdateTasks; aggregation in update_tasks_stats.cs, tests in tests/x2_load_profiler.tests). Installed at $DATA/Mods/x2_load_profiler (enabled in contentpacks.json). Build output must be copied there; check how TASK-001..003 did it (Directory.Build.props, csproj) before assuming.
- Machine state: optimizing.json is {} (restored). log4net.xml is still DEBUG with AssetTask at WARN (restore from log4net.xml.orig when measuring is finished, not before). Paths: $BOTTLE=~/Library/Application Support/CrossOver/Bottles/Steam/drive_c, $GAME=$BOTTLE/Program Files (x86)/Steam/steamapps/common/Xenonauts2, $DATA=$BOTTLE/users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2.
- Run protocol: Lance quits and launches the game and loads the save (agent cannot drive CrossOver). Load auto/auto_groundcombat_turn_10_start-62.json from the menu (the copy user_baseline_turn10-3.json has the same hash but the menu path used so far was the auto file). Before each run, with the game closed, move $DATA/Logs/output.log* into a named folder (e.g. Logs/run3-diag). Verify the loaded save from the "Queued LoadGameCommand" line; do not trust a loose grep of the save name. Log lines wrap, so the timestamp is on the line before the message.
- Repo rules (Lance's CLAUDE.md): TDD for testable logic, conventional commits, NO Claude attribution or Co-Authored-By trailers anywhere, no emojis, no multiline code comments, markdown paragraphs on one line, never rewrite existing implementations without asking, stop and ask rather than assume, commit .serena and backlog changes as separate atomic commits, use mise/fd/rg/jq per global instructions.

WHAT THE EXISTING DATA ALREADY SAYS (run 1, gap window 23:36:00 to 23:36:20)
- Most seconds are at wallMsPerFrame about 16.4 (frame time pinned near a 60 fps cap) with UpdateTasks at 9 to 110 ms of a 1000 ms second. Polling cost (case 1) is not the dominant cost.
- processing sits at about 2500 to 2700 for roughly 13 seconds while completed is only 11 to 76 per second, then completions arrive in bursts (577, 497, 250, 781 per second). That pattern means tasks are waiting on something that finishes in bursts, not that the poll loop is slow. This leans toward case 2 (throttled completions) or case 3 (a per-load step), and the existing counters cannot separate them.
- Unconfirmed hypothesis worth testing: Unity's own async asset-bundle loading and upload pipeline (Application.backgroundLoadingPriority, QualitySettings.asyncUploadTimeSlice / asyncUploadBufferSize, the loading thread) is the bottleneck under Rosetta/Wine, so tasks sit in IsDone-polling until Unity finishes. The earlier cap-200 test (gap only 2 to 3 s shorter) is consistent with this, since raising how many loads are in flight does not help if Unity services them at a fixed rate. The process sits at about 110% CPU (one core), so a single saturated thread is also consistent.

STEPS
1. Mine the existing logs further (no code, no game run). From the run1/run2 profiler files and the archived output.log, tabulate per second: completed, processing, pending, updateMs. Check whether completions-per-second correlates with anything (frame time, pending). Record what separates case 2 from case 3, or state that it cannot be separated. Quick win, do first.
2. [NEEDS LANCE'S APPROVAL, scope beyond reading logs] Extend the profiler, test-first for any aggregation logic (new stats in update_tasks_stats.cs with tests in tests/x2_load_profiler.tests, Harmony glue kept thin and allocation-free in the hot path): (a) at mod load log once: Application.backgroundLoadingPriority, QualitySettings.asyncUploadTimeSlice, asyncUploadBufferSize, asyncUploadPersistentBuffer, Application.targetFrameRate, QualitySettings.vSyncCount; (b) per-second count of tasks started vs completed and, for AssetBundleFileLoadOperation, the number in flight versus the cap (patch CanStart or Start/IsDone; confirm exact members in decomp/Common.Content.AsyncOperations/AssetBundleFileLoadOperation.cs); (c) mean and max start-to-done latency of bundle load operations per second; (d) time spent in the LoadProcessTask / post-processing steps (JSON parse, deserialize) per second if separable via patches on the relevant methods; (e) optionally, main-thread time per frame outside UpdateTasks (Update to LateUpdate stopwatch) to see where the other ~90% of the frame goes. If decomp/ is empty, regenerate per the command in docs/PLAN.md.
3. Run at least two cold diagnostic runs with the extended profiler (same protocol, same save). Archive logs per run. Check each run for new log errors.
4. Decide with a stated rule: case 1 holds if UpdateTasks is a large share of frame time (it is not in the baseline); case 2 holds if frames are fast, in-flight is at or near the cap or Unity is the limiter, and completions per frame stay low; case 3 holds if start-to-done latency or post-processing time per task times task count explains the gap. If the Unity async-loading hypothesis holds, say so explicitly, since the fix would then be changing those Unity settings (a different mechanism from the Harmony UpdateTasks patch in PLAN step 5).
5. Write the finding with numbers into docs/load-time-report.md (new section, one-line paragraphs, tables as in the baseline section), save per-second diagnostic lines under docs/baseline/ or a new docs/diagnosis/ folder, tick AC #1, set the task Done with a final summary, and commit docs and backlog changes as separate conventional commits (suggest "docs: diagnose pre-setup content-loading gap").
6. If step 2 reveals the cause needs more than the above, STOP and ask Lance before adding acceptance criteria or creating follow-up tasks.

OPEN QUESTIONS FOR LANCE
- Approve extending the profiler (step 2), or diagnose from the existing logs only?
- Is touching Unity settings at runtime from the mod acceptable for an experiment, or is this task strictly measure-only (the fix belongs to TASK-006 or later)?

APPROVAL RECORDED (Lance, 2026-10-04): Step 2 is approved, extend the profiler. Changing Unity settings at runtime from the mod is allowed as an experiment (backgroundLoadingPriority, asyncUploadTimeSlice, asyncUploadBufferSize, asyncUploadPersistentBuffer). The STATUS line above (DRAFT, NOT YET APPROVED) is superseded: the plan is approved as written. Measure first (step 3 baseline-style runs with the extended profiler), then run the Unity-settings experiment as separate runs so the diagnosis and the experiment are not mixed; record which settings values were used per run. Still stop and ask before adding acceptance criteria or creating follow-up tasks.
<!-- SECTION:PLAN:END -->

---
id: TASK-005
title: Diagnose the pre-setup content-loading gap
status: In Progress
assignee: []
created_date: '2026-10-05 04:10'
updated_date: '2026-10-05 06:53'
labels: []
dependencies:
  - TASK-004
modified_files:
  - src/x2_load_profiler/bundle_load_patch.cs
  - src/x2_load_profiler/bundle_load_stats.cs
  - src/x2_load_profiler/unity_experiment_settings.cs
  - src/x2_load_profiler/update_tasks_patch.cs
  - src/x2_load_profiler/x2_load_profiler_lifecycle.cs
  - tests/x2_load_profiler.tests/bundle_load_stats_tests.cs
  - tests/x2_load_profiler.tests/unity_experiment_settings_tests.cs
  - tests/x2_load_profiler.tests/x2_load_profiler.tests.csproj
  - docs/diagnosis/run3-profiler.txt
  - docs/diagnosis/run4-profiler.txt
  - docs/diagnosis/run5-profiler.txt
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HANDOFF PROGRESS (2026-10-05). Status stays In Progress; AC #1 not yet met (no report section written). Plan steps 1 to 3 are mostly done; step 4 (decision) and step 5 (report) remain.

DONE
- Step 1: mined run1/run2 profiler lines. Plateau (~13 s, processing 2500 to 2700): 37 and 34 completions per second, UpdateTasks 3.8% of wall time, avg frame 17.5 ms. Burst (~5 s): 507 and 512 completions per second, UpdateTasks 5.8%. Case 1 (per-frame polling) is ruled out. The old counters could not separate case 2 from case 3.
- Step 2: profiler extended, TDD, 25 unit tests pass. New per-second fields: bundleStarted, bundleDone, bundleInFlight, bundleBlockedPolls (CanStart false), bundleMeanMs, bundleMaxMs (Harmony patches in src/x2_load_profiler/bundle_load_patch.cs, aggregation in bundle_load_stats.cs). One-time UnitySettings line at mod load. Config switch: Mods/x2_load_profiler/unity_experiment.txt (key=value for backgroundLoadingPriority, asyncUploadTimeSlice, asyncUploadBufferSize, asyncUploadPersistentBuffer; parser in unity_experiment_settings.cs); logs an 'Experiment applied from <path>' line. Slow-load logging: any bundle load >= 500 ms logs 'SlowBundle ms= type= asset='. Skipped plan items (d) post-processing time and (e) main-thread time outside UpdateTasks, because UpdateTasks is only ~4% of the plateau; add them only if the new data does not settle it.
- Commits: 69af962, 44c1853, 80ce0c5 (fixes an ArgumentException: Assembly.Location is empty for in-memory mod assemblies), 47656f7 (slow-load logging), 854d131 (raw run 3 to 5 lines).

RESULTS (raw per-second lines in docs/diagnosis/run3|run4|run5-profiler.txt; run5 is the High-priority run; the first run5 attempt was invalid because of the Assembly.Location bug and was discarded)
- Run 3 (default, BelowNormal): gap 21.2 s. Run 4 (default): gap 20.2 s. Run 5 (backgroundLoadingPriority=High): gap 19.8 s, queue to playable 43.4 s vs 43.0 s. Patterns and bundle counts are essentially identical across all three (plateau 911/911/914 bundle loads, mean start-to-done 362/361/360 ms; burst 2734/2734/2732 loads, mean 50/51/52 ms; whole gap 5497 loads each). The load is deterministic for this save.
- bundleInFlight is exactly 25 in every second of the gap (the CM_MAX_CONCURRENT_ASSET_BUNDLE_FILES_LOADING cap is always saturated), with about 2600 blocked CanStart polls per frame in the plateau, costing ~4% of wall time.
- Throughput tracks 25 / per-load latency (Little's law): about 35 per second when loads take 0.4 to 1.0 s (plateau), 500 to 900 per second when they take 20 to 80 ms (burst). So the gap is dominated by per-load start-to-done latency, not polling.
- backgroundLoadingPriority=High did NOT change anything, so that hypothesis is falsified. asyncUploadTimeSlice, asyncUploadBufferSize and persistent buffer are untested. Defaults: BelowNormal, timeslice 2, buffer 64, persistent true, targetFrameRate 60, vSyncCount 1. Frames sit at the 60 fps cap (16.4 ms).
- The earlier cap-200 test (gap 2 to 3 s shorter) has not been repeated with the new counters. Repeating it would show whether per-load latency scales with in-flight count (Unity serializes loads) or not.

SEPARATE OBSERVATION (outside this task's scope): main-thread stalls after the content gap with UpdateTasks idle: a 1.1 s frame at ~+30 s, 0.7 s at ~+35 s, 0.4 s at ~+38 s after the load command, in the same places in runs 3, 4 and 5. Lance's screen recording (not in repo; ~43 s total) shows the loading bar at 90% for ~16 s (video 71 to 86 s), then 94%, then playable; Lance says it hitches at multiple spots including 94%. Do NOT create follow-up tasks without asking Lance.

IN FLIGHT
- Run 6 (defaults, slow-bundle logging, no experiment overrides) was about to start; Lance launches the game via Steam and loads the save. unity_experiment.txt currently holds only a comment line. When Lance says it is done, with the game CLOSED move $DATA/Logs/output.log* into a named folder (e.g. Logs/run6-slowbundle). Confirm the save from the 'Queued LoadGameCommand' line and check for new errors (baseline is 5 [ERROR] lines and 20 state-loss matches). Extract the SlowBundle lines and group by type and asset path to see what the ~900 plateau loads have in common. Compare the gap against 19.8 to 21.2 s to see whether the extra logging perturbs timing.

NEXT
1. Analyse run 6 slow-bundle data. 2. Optional experiments, one variable per run, recorded in the report: cap 200 via optimizing.json (original is {}), asyncUploadTimeSlice up, asyncUploadBufferSize up. 3. Apply the decision rule from plan step 4 and write the finding with numbers into docs/load-time-report.md (new section, one-line paragraphs, tables like the baseline section), tick AC #1, set Done with a final summary. 4. Commit docs and backlog separately (conventional commits, no attribution trailers).

MACHINE STATE
- optimizing.json is {}. log4net.xml is still DEBUG with AssetTask at WARN (restore from log4net.xml.orig only when all measuring is finished). Mods/x2_load_profiler/unity_experiment.txt is comment-only. Archived logs under $DATA/Logs: run1-baseline, run2-baseline, run3-diag, run4-diag, run5-invalid, run5-high (the High run).
- The game must be closed before moving logs. The csproj copies the mod build into the mod folder after every build (dotnet via ~/.local/bin/mise exec, DOTNET_ROOT=~/.local/share/mise/dotnet-root).
- Log lines wrap, so the timestamp is on the line before the message. The raw files in docs/diagnosis show the extraction format (paste line pairs, strip the logger prefix).

AUTOMATED RUNS (2026-10-05, from TASK-009, Done): the next agent can drive every run itself; Lance no longer has to quit, launch or load by hand. This supersedes the 'Lance launches the game via Steam and loads the save' protocol above, including the in-flight run 6 instructions. Read docs/automated-runs.md first. Command: `scripts/run.py <run-name>` from the repo root (uv script, `~/.local/bin/mise exec -- uv run --script scripts/run.py <run-name>` if the shebang is not enough). It closes the game, moves leftover output.log* to Logs/pre-<run-name>, launches via `open` on the CrossOver Steam app bundle, loads the baseline save auto/auto_groundcombat_turn_10_start-62.json, waits for the GCUI: BlockOnLocalPlayerTurn marker, quits, and moves the run's logs to Logs/<run-name>. It exits 1 with a message on a wrong save, no queued save, timeout (LOAD_TIMEOUT, default 120 s) or a changed config file. Run names must be new: Logs/run6-auto and Logs/run7-auto already exist from validation, so a slow-bundle run should be e.g. run8-slowbundle. Preconditions: CrossOver Steam running and logged in, Steam Cloud sync disabled for Xenonauts 2 (already done).

LOAD ROUTES: (1) DEFAULT, mod-side auto-load. The x2_load_profiler mod reads Mods/x2_load_profiler/auto_load.txt (save=<path>, reseed=<bool>), which run.py writes and removes itself, and queues the load 0.1 s after the main menu is ready. No input takeover, no permissions needed. It requires the profiler mod to be enabled and built, so it works for all TASK-005 runs. (2) FALLBACK, osascript/JXA menu navigation: `scripts/run.py <run-name> --load menu`. It waits for the main menu, then posts three CoreGraphics mouse clicks through `osascript -l JavaScript` (LOAD GAME 1331,1302; first Turn 10 row 947,426; LOAD SAVE 960,1112, overridable in .env). Use it only when the mod is not loaded, for example the TASK-007 mod-off arm. It takes over the mouse on the host desktop, needs Accessibility and Automation for the terminal, and has not yet been run end to end through run.py (the clicks were proven by hand in the TASK-009 spike). Ask Lance before the first menu-mode run and have him present. See TASK-009 notes for the spike comparison.

EXPERIMENTS AND CONFIG GUARD: run.py hashes optimizing.json ($GAME_DIR), Mods/x2_load_profiler/unity_experiment.txt and Assets/Configuration/log4net.xml when it starts and fails the run if any of them differ at the end. Set up an experiment (cap 200 in optimizing.json, unity_experiment.txt values) BEFORE calling run.py, change one variable per run, and restore the original afterwards (optimizing.json is {}, unity_experiment.txt comment-only). Do not edit those files while a run is in progress. Do not restore log4net.xml from log4net.xml.orig until all measuring is finished. Settings can be overridden with environment variables or a .env in the working directory (see .env.example); do not change them without asking Lance.

CORROBORATING LOGS: run.py prints, per run, the [ERROR] count, the state-loss count (case-insensitive 'state-loss'), queue to setup, queue to playable, last XenonautsLoadScreen Intro Complete to Setup, and LoseFocus to Setup (n/a under auto-load because the LoseFocus line does not exist). Baseline to compare: 5 [ERROR] lines, 20 state-loss matches, queue to setup 22.8 to 23.4 s, queue to playable 42.0 to 43.4 s, intro to setup 22.55 to 22.80 s. Automated auto-load runs so far: run6-auto (intro to setup 22.40 s, queue to playable 43.61 s) and run7-auto (22.82 s, 45.23 s), both 5 errors and 20 state-loss, in $DATA/Logs. The old 19.8 to 21.2 s figure in this task is LoseFocus to Setup from menu-loaded runs 3 to 5 and cannot be compared with auto-loaded runs; compare auto-loaded runs on intro to setup, and compare the profiler per-second lines (bundleInFlight, bundleMeanMs, completions) as before. Corroborate each run beyond the printed numbers: (a) confirm the save from the 'Queued LoadGameCommand' line in Logs/<run-name>/output.log (the script already fails on a mismatch, but spot-check it; the descriptor logs as FD[UNRESOLVED]>FileSystem::<path> under auto-load and FileSystem::<path> from the menu), (b) log lines wrap so the timestamp is on the line before the message, (c) check that the profiler's Experiment applied line matches what you set, (d) check for new [ERROR] records beyond the five baseline ones, and (e) extract SlowBundle lines and the per-second profiler lines into docs/diagnosis the same way as runs 3 to 5. Auto-load queues the command while the boot loading screen's outro is still running and the game logs one 'MoveTo GroundCombat Skip: The previous MoveTo is still animating' line; that is expected and not an error. Because auto-load shifts the start slightly relative to menu-loaded runs 1 to 5, treat a difference under about 0.5 s on intro to setup as noise (run6 and run7 differ by 0.42 s) and repeat a run before drawing a conclusion from a smaller delta.
<!-- SECTION:NOTES:END -->

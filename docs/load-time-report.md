# Xenonauts 2 save load time under CrossOver (macOS)

## Environment

- Game 7.27.11 (Steam, Unity 2022.3.62f2, Mono), run through CrossOver on macOS under Rosetta, D3D11 reported as "AMD Compatibility Mode".
- Save: `auto_groundcombat_turn_13_start-67.json` (about 2.2 MB JSON). Core content pack only; the one Workshop pack present is disabled in `Settings/contentpacks.json`.
- Measured by raising `Assets/Configuration/log4net.xml` to DEBUG with `Common.Content.Tasks.AssetTask` set to WARN, using the game's own `[PhasedFSM.*]` timers and log timestamps.

## Results

| Phase | Cold load (first after launch) | Warm load (third, no restart) |
|---|---|---|
| Click Load to load screen up | about 2 s | about 2 s |
| Silent gap before `LoadScreen, Handling Setup for GroundCombat` | 21.4 s | 22.4 s |
| `InitializeMap` (PhasedFSM) | 10.5 s | 4.7 s |
| `Load` phase (PhasedFSM) | 5.7 s | 4.4 s |
| `TurnControl.Begin` (PhasedFSM) | 1.0 s | 0.8 s |
| Total, click to playable | about 40 s | about 36 s |

The game's own phases shrink when warm. The pre-setup gap does not: it is the largest single piece of every load.

During the gap the process sits at about 110% CPU (one core), so it is CPU-bound on a single thread.

## What happens in the gap

The log reads "MoveTo GroundCombat Canceled: Assets need to be loaded so moving to the LoadingScreen instead", then goes quiet. With `AssetTask` at DEBUG (a 15 second slice of an earlier load) the content manager is loading asset bundle files for the strategy templates, ground combat audio, prefabs, textures and JSON data. In that slice there are about 123,000 `PROCESS(ASYNC) UPDATE::LoadTask.AssetBundleFileLoader` polls against about 640 `SUCCEEDED` completions.

## Likely cause (from decompiled `Assembly-CSharp.dll`)

- `ContentManager.UpdateTasks` (`Common.Content.Managers/ContentManager.cs`) runs once per frame. The `frameLoadBudget` check (`CM_FRAME_LOAD_BUDGET`, 200 ms) only skips tasks where `!IsAsync()`. Every async task has `Process()` called on every update, with no time limit.
- `AssetBundleFileLoadOperation.CanStart` caps in-flight bundle loads at `CM_MAX_CONCURRENT_ASSET_BUNDLE_FILES_LOADING` (default 25). Tasks over the cap stay in the processing list and are polled every frame without doing work, which fits the poll-to-completion ratio above.
- The pending-task loop calls `AreLoaded(...)` over each pending task's dependencies every update, so per-frame cost grows with the number of queued tasks.
- The effect is that throughput is limited to roughly 25 completions per frame while each frame costs more as the queue grows. On a machine where frames are expensive (Rosetta plus Wine), this stretches the load.

This is a hypothesis from reading the code and from log counts, not from a profiler: managed frames are unsymbolicated under Rosetta, so `sample` could not name the hot methods.

## Tunables

Both throttles are read from `optimizing.json` in the game folder, a flat JSON file keyed by static field name (`Constants.Optimizing`): `CM_FRAME_LOAD_BUDGET`, `CM_MAX_CONCURRENT_ASSET_BUNDLE_FILES_LOADING`, plus `PROMISE_HANDLING_BUDGET` and `STRATEGY_INITIALIZE_FRAME_BUDGET`.

## Test result: concurrency cap 200

Test: `{"CM_MAX_CONCURRENT_ASSET_BUNDLE_FILES_LOADING": 200}` in `optimizing.json` (original backed up as `optimizing.json.orig`), fresh game launch, then one load of `auto_groundcombat_turn_10_start-62.json`. The file was read: the log has no "Config file not found: optimizing.json" line.

| | Cap 25 (default), turn 13 save | Cap 200, turn 10 save |
|---|---|---|
| Silent gap before setup | 21.4 s cold, 22.4 s warm | 19.1 s cold |
| `InitializeMap` + `Load` + `TurnControl` (PhasedFSM total) | 17.3 s cold | 16.2 s cold |
| Click to playable | about 40 s | 39.3 s |

The gap shrank by 2 to 3 s and the saves are not identical, so the difference is within what I would expect from save-to-save variation. Raising the concurrent-load cap alone does not remove the gap. The cap hypothesis above is therefore not supported, and the per-frame cost of polling or the cost of each load step may matter more. This needs per-frame instrumentation to settle.

## Suggested next steps

- A small Harmony mod that wraps `ContentManager.UpdateTasks` with a stopwatch and logs once per second: frames, total time in `UpdateTasks`, tasks polled, tasks completed, and time in the pending-dependency loop. That shows whether the gap is per-frame polling cost, frame rate, or per-task load cost, without the log volume of DEBUG logging. The official skeleton mod and `0Harmony.dll` support this.
- Depending on that result, a Harmony prefix or transpiler on `UpdateTasks` to stop polling tasks that cannot start yet and to cache dependency checks for pending tasks.
- Asking Goldhawk whether the async bypass of `frameLoadBudget` and the per-frame poll of non-startable tasks is intended.

## Baseline with profiler (cap 25)

Two cold runs on 2026-10-04 with `optimizing.json` restored to `{}`, the `x2_load_profiler` mod enabled, `log4net.xml` still at DEBUG with `AssetTask` at WARN, and `auto/auto_groundcombat_turn_10_start-62.json` (sha256 `ef7d2aeb7b8ed7d76bd403ea58536897daf7192dec2bf0af222e14aeb81ea388`). Each run is a fresh game launch, one load, no interaction with the window. Per-second profiler lines for the whole session are in `docs/baseline/run1-profiler.txt` and `docs/baseline/run2-profiler.txt`.

| Event | Run 1 | Run 2 |
|---|---|---|
| Queued LoadGameCommand | 23:35:58.092 | 23:38:52.831 |
| LoadingWorld LoseFocus | +1.44 s | +1.76 s |
| Handling Setup for GroundCombat | +22.79 s | +23.06 s |
| BlockOnLocalPlayerTurn promise | +42.05 s | +42.92 s |
| Pre-setup gap (LoseFocus to Setup) | 21.35 s | 21.30 s |
| Total, queue to playable | 42.05 s | 42.92 s |

Profiler totals over the pre-setup gap (about 20 per-second lines each):

| | Run 1 | Run 2 |
|---|---|---|
| Frames | 1145 | 1152 |
| Time in `UpdateTasks` | 1347 ms | 1310 ms |
| Share of gap wall time | 6.7% | 6.6% |
| Tasks completed | 4070 | 4017 |
| Worst second in `UpdateTasks` | 205 ms | 198 ms |
| Worst wall time per frame | 32 ms | 34 ms |

Both runs loaded the `auto/` autosave directly. The copy `Saves/ellz_1bf479e6/user_baseline_turn10-3.json` has the same hash and was not used. Raw logs were archived outside the repo under `Logs/run1-baseline` and `Logs/run2-baseline` in the game's user data folder.

## Diagnosis of the pre-setup gap

Finding: the gap is case 2/3 hybrid dominated by per-bundle start-to-done latency under a saturated 25-wide cap, not by `UpdateTasks` polling. Unity services bundle loads at a roughly fixed rate, so queued loads wait. Raising the cap shortens the gap only partly because per-load latency grows with the number in flight.

Runs 3 to 5 (menu-loaded, `x2_load_profiler` extended with bundle counters, raw lines in `docs/diagnosis/run3-profiler.txt` to `run5-profiler.txt`) show the same deterministic load every time: 5497 bundle loads in the gap, `bundleInFlight` exactly 25 in every second, about 2600 blocked `CanStart` polls per frame in the plateau.

| | Run 3 (default) | Run 4 (default) | Run 5 (`backgroundLoadingPriority=High`) |
|---|---|---|---|
| LoseFocus to Setup | 21.2 s | 20.2 s | 19.8 s |
| Plateau bundle loads / mean start-to-done | 911 / 362 ms | 911 / 361 ms | 914 / 360 ms |
| Burst bundle loads / mean start-to-done | 2734 / 50 ms | 2734 / 51 ms | 2732 / 52 ms |

Throughput follows Little's law with the cap as concurrency: about 35 completions per second while loads take 0.4 to 1.0 s (plateau, about 13 s, `UpdateTasks` 3.8% of wall time in runs 1 and 2) and 500 to 900 per second while they take 20 to 80 ms (burst, about 5 s, 5.8% in runs 1 and 2). Case 1 (per-frame polling) is ruled out. `backgroundLoadingPriority=High` changed nothing, so that Unity-side hypothesis is falsified.

Runs 8 and 9 use the automated auto-load route (`scripts/run.py`), the same save, 5 `[ERROR]` lines and 20 state-loss matches each, raw lines in `docs/diagnosis/run8-profiler.txt` and `run9-profiler.txt`. Only one variable differs.

| | Run 8 (cap 25) | Run 9 (cap 200) |
|---|---|---|
| Intro to setup | 23.60 s | 19.80 s |
| Queue to playable | 44.39 s | 40.85 s |
| Total bundle loads | 8808 | 8808 |
| Seconds with loads completing | 45 | 29 |
| Loads per active second | 196 | 304 |
| Max in flight | 25 | 200 |
| Mean start-to-done (load weighted) | 132 ms | 874 ms |
| Max start-to-done | 2257 ms | 7283 ms |
| Loads taking 500 ms or more | 723 | 3111 |

Eight times the concurrency gives 1.55 times the throughput and 6.6 times the per-load latency. Unity serializes most of the work behind the loads, so latency scales with queue depth and the cap alone is a weak lever, consistent with the earlier 2 to 3 s result. The 3.8 s gain is well above the 0.5 s noise margin of auto-load runs. Cap 200 is a single run and should be repeated before it is relied on.

In run 8 the 723 loads of 500 ms or more are not one asset: 247 strategy textures, 147 strategy templates, 108 common templates, 53 groundcombat templates, 38 groundcombat prefabs, 26 common UI prefabs. No single bundle or type explains the plateau.

The remaining cost after the gap (about 20 s from setup to playable) and the hitches at about +30, +35 and +38 s after the load command are outside this finding. `asyncUploadTimeSlice` and `asyncUploadBufferSize` were not tested.

## Fix result: mod on and off

The fix is a Harmony postfix on `AssetBundleFileLoadOperation.CanStart` in `x2_load_profiler` (`src/x2_load_profiler/bundle_concurrency_patch.cs`) that raises the concurrent bundle load cap from the game's 25 to 200. `Mods/x2_load_profiler/bundle_cap.txt` holds an optional integer override, 0 means unlimited, and the mod never lowers the game's own cap. Run 10 (auto-load) confirms the same 8808 bundle loads and the same 5 `[ERROR]` lines as run 8 without the fix.

All four runs below are cold, menu-loaded through `scripts/run.py --load menu`, same save, `log4net.xml` still at DEBUG with `AssetTask` at WARN, `optimizing.json` restored. Mod off means the `x2_load_profiler` pack set to `Enabled: false` in `contentpacks.json` (confirmed by zero `X2LoadProfiler` log lines). Every run has 5 `[ERROR]` lines and 20 state-loss matches.

| Run | Condition | Intro to setup | Queue to playable |
|---|---|---|---|
| run11-on-menu | mod on | 20.03 s | 40.01 s |
| run12-on-menu | mod on | 20.13 s | 39.75 s |
| run13-off-menu | mod off | 22.50 s | 41.93 s |
| run14-off-menu | mod off | 22.58 s | 42.19 s |
| Mean, on | | 20.08 s | 39.88 s |
| Mean, off | | 22.54 s | 42.06 s |
| Difference | | -2.46 s (-11%) | -2.18 s (-5%) |

The earlier baselines (21.3 s LoseFocus-to-setup gap, 42 to 43 s total) agree with the mod-off arm. The gain is about 2.2 to 2.5 s, smaller than the 3.8 s seen between runs 8 and 9 because those two used different intro anchors and a single sample each.

### Warm loads

Four more launches with `scripts/run.py --load menu --warm-loads 2`: each launch is one cold menu load followed by two in-session reloads of the same baseline save through the in-game menu (no restart), same settings as above. Every launch has 15 `[ERROR]` lines (5 per load) and 60 state-loss matches (20 per load), identical to the single-load runs. Mod off runs come first, then mod on.

| Run | Condition | Cold intro to setup | Cold queue to playable | Warm intro to setup (2 loads) | Warm queue to playable (2 loads) |
|---|---|---|---|---|---|
| run20-off-warm | mod off | 22.66 s | 42.49 s | 23.38, 23.37 s | 35.17, 35.13 s |
| run21-off-warm | mod off | 22.66 s | 41.67 s | 23.34, 23.35 s | 34.79, 35.37 s |
| run22-on-warm | mod on | 20.54 s | 39.71 s | 20.78, 20.72 s | 32.15, 33.13 s |
| run23-on-warm | mod on | 20.49 s | 40.07 s | 20.90, 20.47 s | 32.13, 31.68 s |

| | Mod off | Mod on | Difference |
|---|---|---|---|
| Cold intro to setup (runs 11 to 14, 20 to 23, mean of 4) | 22.60 s | 20.30 s | -2.30 s (-10%) |
| Cold queue to playable (mean of 4) | 42.07 s | 39.89 s | -2.18 s (-5%) |
| Warm intro to setup (mean of 4) | 23.36 s | 20.72 s | -2.64 s (-11%) |
| Warm queue to playable (mean of 4) | 35.12 s | 32.27 s | -2.85 s (-8%) |

The pre-setup gap does not shrink on warm loads with the mod on or off (it grows by 0.4 s with the mod on and 0.8 s off), which matches the earlier 21.4 s cold and 22.4 s warm finding. Warm loads are faster only after setup. The mod removes about 2.3 to 2.6 s of the gap in every condition, about 11%. That leaves roughly 20.5 s of the original 19 to 22 s gap, so the fix is a measured but small gain, not the large reduction the plan hoped for. Runs 20 to 23 use the baseline save for the warm reloads: a save made in-game with the mod on raises a "Missing Content" confirmation when loaded with the mod off.

### Save made after the load

With the mod on, a save made in-game after the load (`user_task006_verify-4.json`, 2.2 MB) was reloaded in the same session: the game reached `BlockOnLocalPlayerTurn` in 33.3 s with the same squad, objectives and 5 `[ERROR]` and 20 state-loss lines as the first load.

## Shipping log level (TASK-010.01)

All earlier numbers were taken with `log4net.xml` at DEBUG. At the shipping configuration (root and every appender at ERROR, identical to `log4net.xml.orig`) the game drops its INFO marker lines and the profiler drops its WARN lines, so `scripts/run.py` had no timing source. The `x2_load_timing` mod now appends a timestamped line to `Mods/x2_load_timing/markers.txt` at the same five points (load command queued, load screen intro and outro complete, `Handling Setup`, `BlockOnLocalPlayerTurn`) without going through log4net, and `run.py` reads that file when it is present. The mod is enabled in both arms below. Mod off means only the `x2_load_profiler` pack (which holds the concurrency patch) is disabled.

Four launches on 2026-10-05, each a menu-loaded cold load plus two in-session reloads of the baseline save (`--load menu --warm-loads 2`), `log4net.xml` unchanged, `optimizing.json` at `{}`. Markers for each launch are in `docs/baseline/shipping/`. Every launch has 15 `[ERROR]` lines (5 per load, same as the DEBUG runs). `state-loss` matches fall from 20 to 10 per load at this level in both arms because half of those lines are INFO or DEBUG, so the check stays valid only as an on/off comparison.

| Run | Condition | Cold intro to setup | Cold queue to playable | Warm intro to setup (2 loads) | Warm queue to playable (2 loads) |
|---|---|---|---|---|---|
| run50-ship-off-warm | mod off | 24.47 s | 43.14 s | 24.25, 24.25 s | 34.37, 34.70 s |
| run52-ship-off-warm | mod off | 24.21 s | 40.95 s | 23.83, 24.39 s | 33.85, 34.50 s |
| run51-ship-on-warm | mod on | 21.87 s | 38.10 s | 21.01, 20.98 s | 31.04, 30.77 s |
| run53-ship-on-warm | mod on | 19.53 s | 36.10 s | 21.57, 21.07 s | 31.65, 31.16 s |

| | DEBUG, mod off | DEBUG, mod on | DEBUG gain | Shipping, mod off | Shipping, mod on | Shipping gain |
|---|---|---|---|---|---|---|
| Cold intro to setup | 22.60 s | 20.30 s | -2.30 s (-10%) | 24.34 s | 20.70 s | -3.64 s (-15%) |
| Cold queue to playable | 42.07 s | 39.89 s | -2.18 s (-5%) | 42.04 s | 37.10 s | -4.94 s (-12%) |
| Warm intro to setup | 23.36 s | 20.72 s | -2.64 s (-11%) | 24.18 s | 21.16 s | -3.02 s (-12%) |
| Warm queue to playable | 35.12 s | 32.27 s | -2.85 s (-8%) | 34.36 s | 31.16 s | -3.20 s (-9%) |

The TASK-006 gain still holds at the shipping level and is somewhat larger in seconds (3.0 to 4.9 s against 2.2 to 2.9 s). Mod-off intro to setup is about 1.5 s longer than at DEBUG, so lighter logging did not make the gap shorter. Possible causes are the timing mod's own hooks (they are in both arms) and a busy host: a smoke run taken while the display was asleep and the machine was in use measured 29.7 s intro to setup, which is why every run here keeps the display awake with `caffeinate -d`. Each cell is the mean of 2 cold or 4 warm loads, so a difference under about 0.5 s should not be read as real.

## Audit of the bundle loads (TASK-010.06)

Capture: one launch (run60-capture, mod on, `bundle_log.txt` present in the mod folder so `x2_load_profiler` records every `AssetBundleFileLoadOperation` and every `ContentManager.InternalUnload` call), a menu-loaded cold load and one in-session warm reload of the baseline save. Raw slices are in `docs/diagnosis/`: `run60-startup-bundle-loads.tsv` (main menu startup), `run60-cold-bundle-loads.tsv`, `run60-warm1-bundle-loads.tsv`, the matching `run60-*-reloaded-after-release.txt` name lists and `run60-markers.txt`. Columns of `L` lines: sequence, completion time, request-to-start ms, start-to-done ms, asset type, relative path, bundle name, content pack, parent (always `-`, see below). `U` lines are unloads. `scripts/analyze_bundles.py` produces the slices and the tables below. Capture timings are not used for any speed claim.

What the numbers mean:

- The "8808 loads per ground combat load" in the earlier sections is the whole session up to the playable point: 2609 loads at main menu startup plus 6199 for the load itself. 5497 of those 6199 finish before `Handling Setup` (the pre-setup gap) and 702 after it. A warm reload makes the same 6199.
- Each record is a single asset read from an already resident bundle (`AssetBundle.LoadAssetAsync(relativePath)`), not a bundle file, so there is no per-load file size. The bundle name is recorded and the asset type stands in for the task type.
- The engine's `LoadTask` has a `parent` argument that no caller sets, so the requester of a load cannot be recovered from the engine. The path (`<kind>/<scope>/...`, scope being `strategy`, `groundcombat` or `common`) is the classification used instead.
- Estimated seconds divide the window's active span (first request to last completion, 19.9 s before setup in the cold load) by each class's share of loads, so they assume every load costs the same wall time. The summed load time column adds the start-to-done latency of every load and is far larger because many loads are in flight at once (up to 200 with the mod); use it for relative cost, not wall time.

Classes in the cold load, before setup (5497 loads, 19.9 s of activity):

| Class | Loads | Est. seconds | Summed load time |
|---|---|---|---|
| Strategy scope (templates 892, textures 459, data 398, audio 60, prefabs 31, ui 24) | 1864 (34%) | 6.7 s | 2310 s (59%) |
| Common scope | 1109 (20%) | 4.0 s | 820 s (21%) |
| Ground combat scope | 2524 (46%) | 9.1 s | 803 s (20%) |
| Released at load start and loaded again (all scopes) | 2574 (47%) | 9.3 s | 2948 s (75%) |
| of which strategy scope | 1383 (25%) | 5.0 s | 2165 s (55%) |
| Strategy scope that is not a reload | 481 (9%) | 1.7 s | 145 s (4%) |
| Loaded more than once inside the same window | 0 | 0 | 0 |
| Loaded, then released again inside the same window | 0 | 0 | 0 |

The scope rows add up to 5497 loads. The reload row overlaps them.

Findings:

1. **Release-then-reload churn is the main avoidable cost.** The main menu loads 2609 assets at startup. When the save load starts, the load screen unloads 2644 assets (2640 distinct) and then loads 2574 of the same paths again within seconds. All 1383 reloaded strategy-scope assets, 610 common templates and 261 maps are in that set. They hold 75% of the summed load time before setup because the strategy templates and textures are the slowest classes. In the warm reload it is total: 6243 unloads, then 6199 loads, every one of them a path that was released earlier in the window.
2. **Strategy-scope content is 34% of the pre-setup loads.** 1383 of the 1864 are the reloads above. 481 are first loads in this process (360 strategy templates among them). The load screen requests all of them from its manifest, so they are not stray loads, but nothing in the capture shows ground combat reading them.
3. **No duplicates and no load-then-release inside one window.** Every path loads exactly once per window. The duplicates are across windows (startup, cold, warm), listed by name in the `*-reloaded-after-release.txt` files: 2574 names for the cold load and 6199 for the warm one.

What a mod could do, and the evidence:

- **Skip the unload of assets the target load will request again (candidate for TASK-010.07).** Evidence it is safe: the same descriptors are loaded again moments after the unload, so the resulting resident assets are the same content; the capture shows no path loaded twice in a window, so there is no case where the second copy differs. Evidence still missing: whether any loaded asset keeps mutable state or post-load processing results that the unload/reload resets (templates are the largest class, 1097 + 892 + 645). The 010.07 experiment has to show an identical error count (5 per load), identical state-loss counts and an identical post-load save before it ships. Upper bound if the whole set were skipped: 2574 of 5497 pre-setup loads, about 9.3 s of the 19.9 s by count. Their 75% share of summed load time suggests the saving could be larger than the count share, because they are the slow classes, but that is not a wall-time measurement.
- **Defer or skip the 481 strategy-scope first loads.** Not supported by the evidence yet. They are requested by the load screen manifest and the capture cannot show whether ground combat ever reads them. Skipping them without a usage trace risks a missing-asset error at the first access, so this needs a read-tracking experiment first.
- **Nothing to remove as duplicate or load-then-release work** inside a single load: both counts are zero.

## Profiler overhead and mod split (TASK-010.02)

`x2_load_profiler` used to apply every patch through the game's `PatchAll`, so the "mod on" arms above ran the per-frame `UpdateTasks` profiler, the `AssetBundleFileLoadOperation` `CanStart`/`Start`/`Update` trackers and the capture hooks along with the fix. Those patches are now applied from `Create` only when `Mods/x2_load_profiler/profiler.txt` contains `true` (default off). The fix (`BundleConcurrencyPatch`, still on `PatchAll`) does not consult the switch. The auto-load patches are applied only when `auto_load.txt` exists. `bundle_log.txt` has an effect only when the profiler is on. Switch logic is `ProfilerSwitch` (`src/x2_load_profiler/profiler_switch.cs`, 5 tests written first), the patch list is `instrumentation_patches.cs`.

Checks that the switch works: two auto-load launches with `bundle_log.txt` present wrote 0 bytes to `bundle_loads.tsv` with the profiler off and 1.9 MB with it on, and the auto-load harness worked in both. The shipping log level drops the profiler's WARN lines, so the logs cannot show which arm had the profiler on; the arm was set by the presence of `profiler.txt`.

Six launches on 2026-10-05 (`run70-*`), each a menu-loaded cold load plus two in-session reloads of the baseline save (`--load menu --warm-loads 2`), shipping `log4net.xml`, `optimizing.json` at `{}`, timing mod on in all arms, interleaved fix, none, profiler, fix, none, profiler. "Neither" means the `x2_load_profiler` pack disabled. Every launch has 15 `[ERROR]` lines and 30 state-loss matches (5 and 10 per load), the same as earlier shipping-level runs.

| Run | Condition | Cold intro to setup | Cold queue to playable | Warm intro to setup (2 loads) | Warm queue to playable (2 loads) |
|---|---|---|---|---|---|
| run70-none-a | neither | 24.24 s | 40.92 s | 23.51, 23.46 s | 33.43, 33.07 s |
| run70-none-b | neither | 22.55 s | 39.10 s | 23.42, 23.55 s | 33.10, 32.99 s |
| run70-fix-a | fix only | 20.29 s | 37.29 s | 21.39, 21.24 s | 31.56, 31.09 s |
| run70-fix-b | fix only | 19.02 s | 35.88 s | 21.65, 21.10 s | 31.43, 31.18 s |
| run70-prof-a | fix plus profiler | 22.00 s | 38.59 s | 21.28, 21.29 s | 31.18, 31.21 s |
| run70-prof-b | fix plus profiler | 20.29 s | 37.18 s | 21.47, 21.19 s | 30.80, 31.24 s |

| | Neither | Fix only | Fix plus profiler | Fix gain (neither to fix only) | Profiler overhead (fix only to fix plus profiler) |
|---|---|---|---|---|---|
| Cold intro to setup (mean of 2) | 23.40 s | 19.66 s | 21.15 s | -3.74 s (-16%) | +1.49 s |
| Cold queue to playable (mean of 2) | 40.01 s | 36.59 s | 37.89 s | -3.42 s (-9%) | +1.30 s |
| Warm intro to setup (mean of 4) | 23.49 s | 21.35 s | 21.31 s | -2.14 s (-9%) | -0.04 s |
| Warm queue to playable (mean of 4) | 33.15 s | 31.32 s | 31.11 s | -1.83 s (-6%) | -0.21 s |

The profiler costs about 1.3 to 1.5 s on the cold load and nothing measurable on warm loads. The cold figure rests on 2 launches per arm with a spread of 1.7 to 1.8 s inside each arm, so it is indicative, not precise; the warm figures agree to within 0.2 s across 4 loads. The fix alone removes 3.4 to 3.7 s from the cold load and 1.8 to 2.1 s from warm loads. The earlier "mod on" gains (3.6 s cold intro to setup at the shipping level) were measured with the profiler running and so understate the cold gain of the fix by about 1.5 s. The fix-only gain is smaller on warm loads here (2.1 s) than the earlier warm figure (3.0 s); the neither arm in this set is 0.7 s faster than the earlier mod-off arm, which fits the run-to-run drift noted above.

### Decision: one mod with an opt-in switch

`x2_load_profiler` stays a single mod. The profiler is a development tool for this repository, and the load fix, the profiler, the capture hooks and the auto-load harness share one lifecycle, one manifest and the `scripts/run.py` install and auto-load flow. Splitting would mean a second manifest, UID, `contentpacks.json` entry and install step for something a player never enables, plus either duplicated code or a shared dependency between two content packs, with no runtime gain: with the switch off the profiler patches are not applied at all, so the fix-only configuration carries zero instrumentation. The shipped default is fix only. Revisit the split only if the profiler is to be distributed to other people.

## Where a bundle load's time goes (TASK-010.03, Linux)

These measurements were taken on the Linux host (Flatpak Steam, game under Proton, `scripts/run.py` auto mode, shipping `log4net.xml`, profiler and capture on), not on macOS. Intro to setup is 5.9 to 6.0 s there with the shipped cap of 200 (runs 81, 85, 88, 90) against 20 to 24 s on macOS, so the 13 s, 35 per second plateau described above does not occur on this host. What carries over is how the cost behaves as the number of loads in flight grows. The macOS split still needs its own run of `scripts/sample_threads.py`.

What a "load" is: every bundle file is opened once per content pack when the pack is indexed (`ContentPackState.CreateIndex`, `AssetBundle.LoadFromFileAsync`), so all bundles are resident before any load. Each of the 8808 loads is one `AssetBundle.LoadAssetAsync` on a resident bundle (`AssetBundleFileLoadOperation`). The managed API shows only request-to-start and start-to-done; Unity's read, deserialize and integrate steps inside it are visible only per thread from outside. `scripts/sample_threads.py` samples `/proc/<pid>/task/*/stat` of the Wine game process every 0.1 s. The game names its main thread "Content Manager Main Thread" (`Constants.cs`), which Linux truncates to "Content Manager". With the profiler on, `Mods/x2_load_profiler/profile.txt` now holds the per-second `UpdateTasks` lines at any log level.

Cold load, pre-setup window (second `Intro Complete` to `Handling Setup`), one run per condition, raw data `docs/diagnosis/run89-cap0-*` and `run90-cap200-*`:

| | Cap 200 (shipped, run 90) | No cap (`bundle_cap.txt` = 0, run 89) |
|---|---|---|
| Window | 5.9 s | 18.1 s |
| Main thread CPU | 3.89 s (66%) | 15.35 s (85%) |
| `UpdateTasks` time (profile.txt) | 2.0 s (34% of wall) | 1.8 s (10% of wall) |
| Main thread CPU outside `UpdateTasks` | about 1.9 s | about 13.6 s |
| `Loading.Preload` (deserialize) CPU | 2.41 s | 5.19 s |
| `Loading.AsyncRead` (file read) CPU | 0.75 s | 0.79 s |
| Disk-wait samples, all threads | 0 | 0 |
| Frames per second | 35 | 17 |
| Loads completed per frame | 21 | 14 |
| Start-to-done, mean / max (run 81 and run 82) | 168 / 797 ms | 3442 / 13272 ms |
| Request-to-start wait, mean / max (run 81 and run 82) | 1163 / 4366 ms | 0 / 1 ms |

Findings:

1. **File reading is not a cost.** The read thread uses under 0.8 s of CPU in both conditions and no thread was ever in disk wait. Reading bundles through Wine is not what limits the load on this host.
2. **Removing the cap makes the load 12 s slower.** All 8808 requests start at once, up to 4183 are in flight, and each takes seconds to finish. Completions settle near 250 per second (about 14 per frame at 17 frames per second), close to the macOS plateau pattern.
3. **The extra time is main-thread work outside `UpdateTasks`.** Main-thread CPU rises from 3.9 s to 15.4 s for the same loads, while the game's own polling stays at 1.8 to 2.0 s. The 11.7 s difference is not the managed polling this task's parent suspected. By elimination it is engine-side work on the main thread that grows with the number of in-flight requests (integrating finished loads and servicing the queue); `/proc` cannot name the function, and the capture cannot separate it further.
4. **Cap 200 is not shown to be optimal.** At cap 200 neither the main thread (66%) nor the deserialize thread (41%) is saturated, and loads wait up to 4.4 s for a slot, so a higher cap below the point where the main-thread overhead appears may help. Only 25 (macOS), 200 and unlimited have been measured. This is the cap sweep of TASK-010.05.

Not done: a per-load split inside `LoadAssetAsync` (the `AssetBundleRequest.progress` experiment), and bundle size and compression as predictors, because loads are single assets read from resident bundles and the capture carries no per-load file size.

### Cap sweep on Linux

Twelve cold auto-load launches on 2026-10-05 with the profiler off (the shipped configuration), `bundle_cap.txt` set per run, two interleaved rounds (`run10a-*`, `run10b-*`, plus `run10c-cap50` replacing a launch that failed before the game started). Every run has 5 `[ERROR]` lines and 10 state-loss matches.

| Cap | Intro to setup (2 runs) | Mean | Queue to playable (2 runs) | Mean |
|---|---|---|---|---|
| 25 (game default) | 8.45, 8.52 s | 8.49 s | 20.68, 20.79 s | 20.74 s |
| 50 | 6.64, 6.61 s | 6.63 s | 18.89, 18.82 s | 18.86 s |
| 100 | 5.96, 5.72 s | 5.84 s | 18.00, 17.77 s | 17.89 s |
| 200 (shipped) | 5.99, 5.89 s | 5.94 s | 18.40, 18.02 s | 18.21 s |
| 400 | 6.32, 6.20 s | 6.26 s | 18.36, 18.21 s | 18.29 s |
| 800 | 8.06, 8.03 s | 8.05 s | 20.15, 19.99 s | 20.07 s |
| Unlimited (profiler on, 5 runs) | 16.7 to 18.6 s | about 18.2 s | 28.6 to 30.8 s | about 30.1 s |

The curve is U-shaped with a flat bottom from 100 to 400. Cap 200 is 0.1 s from the best mean (cap 100), and the spread inside each pair is 0.1 to 0.2 s, so the difference between 100, 200 and 400 is not resolved by these runs. Moving from the game's 25 to 200 saves 2.5 s of intro to setup and 2.5 s to playable on this host, close to the macOS result. Going above 400 loses time: 800 is as slow as 25, and unlimited is 12 s slower, consistent with the main-thread overhead measured above. On Linux there is no further gain from retuning the cap, so the shipped value of 200 stays. The unlimited row was taken with the profiler on, which adds about 1.3 to 1.5 s on cold loads, so it is not directly comparable to the other rows.

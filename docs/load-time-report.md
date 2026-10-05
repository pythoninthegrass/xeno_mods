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

# Plan: fix Xenonauts 2 save-load time with a Harmony mod

Read `load-time-report.md` in this directory first. It holds the measurements, the decompiled-code findings, and the failed config experiment this plan builds on.

## Goal

Cut the roughly 40 s ground-combat load on CrossOver/macOS (Rosetta, Wine). About half of it (19 to 22 s) is a silent content-loading gap before `LoadScreen, Handling Setup for GroundCombat`, and that gap does not shrink on warm loads. The fix has to be a code mod shipped without first-party support.

## Where things stand

- Cause is not yet identified. The hypothesis is per-frame polling cost in `Common.Content.Managers.ContentManager.UpdateTasks`, with the 25-wide async bundle load cap as a secondary suspect. Raising `CM_MAX_CONCURRENT_ASSET_BUNDLE_FILES_LOADING` from 25 to 200 changed the gap by only 2 to 3 s, so the cap alone is not the lever.
- Nothing has been built yet. No mod project exists.
- Rule from the user's global CLAUDE.md: follow TDD for any logic that is testable, no Claude attribution anywhere in the repo or commits, conventional commits, markdown paragraphs on one line (no hard wrapping), no emojis, no multiline code comments, track tasks in `TODO.md`, and stop and ask rather than assume. Do not rewrite or discard existing implementations without asking.

## Machine state to know about and restore

All paths are under the CrossOver bottle `~/Library/Application Support/CrossOver/Bottles/Steam/drive_c/`. Call it `$BOTTLE`. The game folder is `$BOTTLE/Program Files (x86)/Steam/steamapps/common/Xenonauts2` (`$GAME`), and the user data folder is `$BOTTLE/users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2` (`$DATA`).

| File | Current state | Backup | Restore when |
|---|---|---|---|
| `$GAME/Assets/Configuration/log4net.xml` | root and file appender at DEBUG, `Common.Content.Tasks.AssetTask` logger at WARN, pattern includes `[%thread] %logger` | `log4net.xml.orig` | Done measuring (the mod can log through log4net at WARN, so DEBUG is not required) |
| `$GAME/optimizing.json` | `{"CM_MAX_CONCURRENT_ASSET_BUNDLE_FILES_LOADING": 200}` | `optimizing.json.orig` (`{}`) | Before taking baseline measurements, unless the mod is meant to depend on it |

A Steam "verify files" or game update overwrites both. The Workshop Dev Console mod (`steamapps/workshop/content/538030/3726620761`) is installed but disabled in `$DATA/Settings/contentpacks.json`. It is unrelated to load time.

## Key code (decompiled from `Assembly-CSharp.dll`)

- `Common.Content.Managers/ContentManager.cs`: `Update` (line about 268) calls `UpdateTasks(config.frameLoadBudget)` (line about 948). Two loops over `_processingTasks` with a dependency check over `_pendingTasks` in between. The 200 ms budget only skips tasks where `!IsAsync()`, so async tasks are always polled.
- `Common.Content.Tasks/AssetTask.cs`: `Process()` logs a DEBUG "UPDATE" line on every call, then calls `Update()`.
- `Common.Content.Tasks/LoadTask.cs`: `UpdateAsync` creates the request, checks `CanStart()`, starts it, then polls `IsDone`.
- `Common.Content.AsyncOperations/AssetBundleFileLoadOperation.cs`: `CanStart` enforces `maxConcurrentAssetBundleFilesLoading`. `Start` calls `AssetBundle.LoadAssetAsync`.
- `Common/Constants.cs` (`Constants.Optimizing`) and `Xenonauts/XenonautsConstants.cs`: tunables read from `optimizing.json` by field name (`CM_FRAME_LOAD_BUDGET` 200, `CM_MAX_CONCURRENT_ASSET_BUNDLE_FILES_LOADING` 25, `PROMISE_HANDLING_BUDGET` 10, `STRATEGY_INITIALIZE_FRAME_BUDGET` 14, `INK_STORY_EVALUATE_FRAME_BUDGET` 3).
- `Xenonauts/XenonautsMain.cs` (line about 1192): `ContentManager.Update(deltaTime)` is called once per Unity `Update`.

To regenerate the decompiled sources (they were in a session scratchpad and are not kept):

```bash
export DOTNET_ROOT=/opt/homebrew/Cellar/dotnet/10.0.108/libexec
dotnet tool install ilspycmd --tool-path ./tools
./tools/ilspycmd "$GAME/Xenonauts2_Data/Managed/Assembly-CSharp.dll" -p -o ./decomp -r "$GAME/Xenonauts2_Data/Managed"
```

## How mods work (from `GoldhawkInteractive/X2-Modding`)

- Skeleton: `code-skeleton-mod/X2-Example-Mod` targets `netstandard2.1`, references `0Harmony.dll`, `log4net.dll`, `Assembly-CSharp.dll`, `Assembly-CSharp-firstpass.dll`, `UnityEngine.dll` and `UnityEngine.CoreModule.dll` through `Directory.Build.props` (`GameFolder`, `CacheFolder`, `ModInstanceFolder`).
- Entry point: a class implementing `Common.Modding.IModLifecycle` (`Create(Mod, Harmony)`, `Destroy`, `OnWorldCreate`, `OnWorldDispose`, `GetRequiredAssets`). Patches use `[HarmonyPatch(typeof(X), nameof(X.Method))]`.
- Layout of an installed mod (see the Workshop Dev Console, which has `assembly/common/DevConsole.dll` plus `manifest.json`): `manifest.json` (a `VersionedAsset` wrapping a `ContentPackManifest` with `Name`, `UID`, `Version`, `Tags`), `assembly/common/<Mod>.dll`, and optional `.pdb`.
- Local mods go in `$DATA/Mods/<id>` (the folder exists and is empty). The pack must appear as enabled in `$DATA/Settings/contentpacks.json`; the game rewrites this file, so enable it from the in-game mod menu.
- Clone `https://github.com/GoldhawkInteractive/X2-Modding` for the skeleton and the `binaries` folder (it ships `0Harmony.dll` and `log4net.dll`). The game folder already has `0Harmony.dll` in `Managed`.
- Build tooling: `dotnet` 10.0.108 is at `/opt/homebrew/bin/dotnet`. `netstandard2.1` needs no extra reference assemblies, so the skeleton should build on macOS. Confirm this first.

## Steps

1. **Scaffold the repo.** Create the mod project in this repo (suggested: `src/X2LoadProfiler/`), copied from the skeleton with placeholders in `Directory.Build.props` filled in for this machine. Keep machine-specific paths in an untracked override or document them in the README. Add `TODO.md`. Get a no-op mod to build, install into `$DATA/Mods/<id>`, enable, and show its `Log.Warn` line in `$DATA/Logs/output.log`. Commit the working scaffold on its own.
2. **Instrumentation mod (measure before fixing).** Add a Harmony patch on `ContentManager.UpdateTasks` using prefix and postfix with a `Stopwatch`. Once per second log one WARN line: frames, total ms inside `UpdateTasks`, tasks in `_processingTasks`, tasks in `_pendingTasks`, tasks completed, and wall-clock ms per frame. Optionally split the dependency-check loop with a transpiler or a second patch. Keep it allocation-free in the hot path. Unit-test the aggregation (counters and per-second rollover) separately from the Harmony glue, written test-first.
3. **Measure.** Baseline protocol: fresh game launch (quit CrossOver's game fully), load `Saves/ellz_1bf479e6/auto/auto_groundcombat_turn_10_start-62.json` once, do not touch the window during the load. Extract the pre-setup gap with the log timestamps of `Queued LoadGameCommand`, `LoadingWorld - Handled LoseFocusScreenReport`, `LoadScreen, Handling Setup for GroundCombat`, and `Creating promise: ...BlockOnLocalPlayerTurn`. Run the baseline at least twice to see variance, with `optimizing.json` restored to `{}`. Autosaves are rotated by the game, so copy the chosen save somewhere safe first and load the copy.
4. **Diagnose from the per-second lines.** Decide which case holds: frames are slow because of polling cost (fix the polling), frames are fast but few tasks complete per frame (fix the throttling), or individual loads or post-processing (JSON parse, deserialize, `LoadProcessTask` chain) dominate (target those). State the finding with numbers in `docs/load-time-report.md`.
5. **Implement the fix as a Harmony patch**, test-first where logic is separable. Candidates in order of likelihood: skip polling tasks that cannot start yet (blocked by `CanStart`), cache the `AreLoaded` dependency check for pending tasks, raise the effective concurrency without breaking ordering, or remove the per-call DEBUG log cost if it still shows up. Verify behavior parity (same assets loaded, no new log errors, game still reaches a playable state, a save made after the load still loads).
6. **Verify and compare.** Repeat the baseline protocol with the mod on and off, same save, at least twice each. Report cold and warm numbers against the 19 to 22 s gap and the 40 s total.
7. **Write up.** Update `docs/load-time-report.md` with the final numbers and the patch description. Add a README covering build, install, and how to enable the mod. Restore `log4net.xml` and `optimizing.json` from their `.orig` backups when finished unless the user wants them kept.

## Pitfalls seen so far

- `sample` under Rosetta returns unsymbolicated managed frames, so it cannot name hot methods. Use the instrumentation mod for method-level timing.
- DEBUG logging for `AssetTask` writes about 10 MB every 2.5 s, which rotates the 5 backups out within about 15 s and slows the load. Keep that logger at WARN.
- The log is event-driven: long silent stretches at the end of a load are the game waiting for the player, not work. Take the end of a load as the `BlockOnLocalPlayerTurn` promise line, not the next log entry.
- macOS `ls` has no `--time-style`; use `stat -f '%Sm %z %N' -t '%H:%M:%S'`.
- The first load after a launch is slower than later ones, but the pre-setup gap is not (21.4 s cold, 22.4 s warm). Compare like with like and run each condition more than once.

## Open questions for the user

- Where is the mod repo to be committed and which git remote, if any? `~/git/xeno_mods` is not yet a git repository.
- Is it acceptable to leave `log4net.xml` and `optimizing.json` modified during development?

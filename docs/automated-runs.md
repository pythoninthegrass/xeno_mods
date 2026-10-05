# Automated cold runs

`scripts/run.py <run-name>` performs one cold measurement run of Xenonauts 2 under CrossOver without anyone at the keyboard: it closes the game, archives old logs, launches the game, loads the baseline save, waits until the game is playable, quits, and archives the run's logs.

## Usage

```bash
scripts/run.py run7-auto              # auto-load through the x2_load_profiler mod (default)
scripts/run.py run7-menu --load menu  # click through the main menu instead
```

The run name may contain letters, digits, `.`, `_` and `-`. The script refuses to start if `Logs/<run-name>` or `Logs/<prefix><run-name>` already exists. Exit code 0 means the save loaded and the game became playable; exit code 1 prints a clear message on stderr.

On success it prints the `[ERROR]` count, the state-loss count and four timings: queue to setup, queue to playable, last `XenonautsLoadScreen: Intro Complete` to setup, and LoseFocus to setup (only present when the save is loaded through the menu). Compare runs on the intro-to-setup gap; it exists in both load modes.

## Load modes

`auto` (default) writes `Mods/x2_load_profiler/auto_load.txt`, and the mod queues the load 0.1 s after the main menu is ready. It needs no input, no screen coordinates and no macOS permissions. It cannot be used when the profiler mod is disabled, because the mod does the loading.

`menu` waits for the main menu and posts three mouse clicks (LOAD GAME, the first Turn 10 save row, LOAD SAVE) with `osascript -l JavaScript`. Use it for the mod-off arm of the TASK-007 comparison. The save row is positional, so the run still verifies the save from the log.

## Preconditions

- CrossOver Steam is running and logged in.
- Steam Cloud sync is disabled for Xenonauts 2 in the game's Steam properties. Otherwise an "Unable to Sync" dialog blocks the launch; the script fails fast when the latest Steam `console_log.txt` shows a failed sync with no completed launch after it.
- The x2_load_profiler mod is built and installed (`dotnet build` in `src/x2_load_profiler` copies it into the mod folder).
- `uv` is available. The script declares its own dependencies (`python-decouple`).

## Desktop takeover and permissions

Auto mode does not touch the desktop beyond `open` launching the game. Menu mode takes over the mouse on the host desktop while it runs: do not use the machine until it exits. It assumes the game runs full screen on the display whose size matches the click coordinates (2560x1440 points by default).

Menu mode needs these macOS permissions granted to the terminal that runs the script, under System Settings, Privacy and Security: Accessibility (to post mouse events) and Automation. Screen Recording is only needed when verifying menu coordinates with screenshots by hand.

## Verification and failure handling

The run reads the `Queued LoadGameCommand` line from `output.log` and exits non-zero if the queued save is not `SAVE_REL`, if no save was queued, or if the playable marker does not appear within `LOAD_TIMEOUT` seconds.

A `finally` block always terminates the game, removes `auto_load.txt` and compares SHA-256 hashes of `optimizing.json`, `unity_experiment.txt` and `log4net.xml` taken before the run. A changed, created or removed file fails the run and is named in the message.

## Logs

Leftover `output.log*` from before the run go to `Logs/<LEFTOVER_ARCHIVE_PREFIX><run-name>` (default `pre-<run-name>`). The run's own logs are moved to `Logs/<run-name>` after the game quits.

## Configuration

Settings resolve in this order: process environment, `.env` in the directory the script is run from, built-in default. No `.env` is required. `.env.example` documents every key.

## Tests

```bash
scripts/tests/test_run.py
```

The tests cover log parsing, timing anchors, configuration and the snapshot helpers. They need no game, Steam or desktop.

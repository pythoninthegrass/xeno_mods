# Automated cold runs

`scripts/run.py <run-name>` performs one cold measurement run of Xenonauts 2 without anyone at the keyboard: it closes the game, archives old logs, launches the game, loads the baseline save, waits until the game is playable, quits, and archives the run's logs. It runs on macOS, where the game runs under CrossOver, and on Linux, where it runs under Proton. See [Linux and Proton](#linux-and-proton) for what differs.

## Usage

```bash
scripts/run.py run7-auto              # auto-load through the x2_load_profiler mod (default)
scripts/run.py run7-menu --load menu  # click through the main menu instead
scripts/run.py run7-warm --load menu --warm-loads 2  # then reload the same save twice in the same session
```

The run name may contain letters, digits, `.`, `_` and `-`. The script refuses to start if `Logs/<run-name>` or `Logs/<prefix><run-name>` already exists. Exit code 0 means the save loaded and the game became playable; exit code 1 prints a clear message on stderr.

On success it prints the `[ERROR]` count, the state-loss count and four timings: queue to setup, queue to playable, last `XenonautsLoadScreen: Intro Complete` to setup, and LoseFocus to setup (only present when the save is loaded through the menu). Compare runs on the intro-to-setup gap; it exists in both load modes.

## Load modes

`auto` (default) writes `Mods/x2_load_profiler/auto_load.txt`, and the mod queues the load 0.1 s after the main menu is ready. It needs no input, no screen coordinates and no desktop permissions. It cannot be used when the profiler mod is disabled, because the mod does the loading.

`menu` waits for the main menu and posts three mouse clicks (LOAD GAME, the first Turn 10 save row, LOAD SAVE) with `CLICK_CMD`. Use it for the mod-off arm of the TASK-007 comparison. The save row is positional, so the run still verifies the save from the log.

## Profiler switch

The per-second profiler, bundle trackers and capture hooks are applied only when `Mods/x2_load_profiler/profiler.txt` contains `true`, and `bundle_log.txt` has an effect only with the profiler on. The bundle cap fix does not depend on it, and the auto-load patches are applied whenever `auto_load.txt` exists. `run.py` does not write `profiler.txt`; create or remove it before a run to choose the fix-only or fix-plus-profiler arm. At the shipping log level the profiler's WARN lines are dropped, so the file is the only record of which arm ran.

## Warm loads

`--warm-loads N` repeats the load N times after the first one without restarting the game: it opens the in-game menu, LOAD GAME, picks the baseline save row and LOAD SAVE, then waits for the next playable marker and checks the queued path. The first load is cold and the rest are warm; the script prints timings for each. It needs the same desktop access as menu mode. A save made in-game with the profiler enabled triggers a "Missing Content" confirmation when loaded with the profiler disabled, so warm loads use the baseline save, which has no mod dependency. Both load lists are positional (`GAME_MENU_SAVE_ROW`, `MENU_SAVE_ROW`): an extra save above the baseline row shifts it by 55 px.

## Timing source at the shipping log level

At the shipping `log4net.xml` (ERROR everywhere) the game writes none of the marker lines, so `run.py` reads `Mods/x2_load_timing/markers.txt` written by the `x2_load_timing` mod (`src/x2_load_timing`). When that file has entries it is used instead of `output.log`; otherwise `output.log` is parsed as before, so DEBUG runs and old logs still work. The file is archived next to `output.log` as `markers.txt`. Keep the timing pack enabled in `contentpacks.json` for both mod-on and mod-off arms and disable only `x2_load_profiler` for the off arm. `TIMING_MOD_NAME` overrides the folder name.

Menu mode raises the game window with System Events before clicking, since the clicks land on whatever window is frontmost. Keep the display awake (`caffeinate -d uv run run.py ...`): with the display asleep the game does not launch. The save rows are positional. When saves are added the baseline row moves, so set `MENU_SAVE_ROW` and `GAME_MENU_SAVE_ROW` in `scripts/.env` (currently `947,481` and `896,481`).

## Preconditions

These are the macOS preconditions. Linux has its own list under [Linux and Proton](#linux-and-proton).

- CrossOver Steam is running and logged in.
- Steam Cloud sync is disabled for Xenonauts 2 in the game's Steam properties. Otherwise an "Unable to Sync" dialog blocks the launch; the script fails fast when the latest Steam `console_log.txt` shows a failed sync with no completed launch after it.
- The x2_load_profiler mod is built and installed (`dotnet build` in `src/x2_load_profiler` copies it into the mod folder).
- `uv` is available. The script declares its own dependencies (`python-decouple`).

## Desktop takeover and permissions

Auto mode does not touch the desktop beyond launching the game. Menu mode takes over the mouse on the desktop it runs against while it runs: do not use that desktop until it exits. It assumes the game runs full screen on the display whose size matches the click coordinates (2560x1440 points by default, which is the macOS display).

On macOS, menu mode needs these permissions granted to the terminal that runs the script, under System Settings, Privacy and Security: Accessibility (to post mouse events) and Automation. Screen Recording is only needed when verifying menu coordinates with screenshots by hand. Linux needs no equivalent, because `xdotool` posts the events through XTEST.

## Linux and Proton

On Linux the game runs under Proton rather than CrossOver, and the script runs **inside** the steam-headless container, not on the host. Everything it touches lives there: the game process, the Proton prefix, `Logs/output.log`, the mod folder and the X display.

The repo has to be reachable inside the container, and `uv` has to be on the PATH. The steam-headless image puts `~/.local/bin` on the login PATH, so a login shell finds a `uv` installed there; a plain `docker exec` does not, hence `bash -lc`:

```bash
docker exec -u default -e DISPLAY=:55 steamos bash -lc 'cd /path/to/xeno_mods && scripts/run.py run1-auto'
```

What differs from macOS, all of it from the built-in defaults in `PLATFORM_DEFAULTS`:

| Setting | macOS | Linux |
| --- | --- | --- |
| `BOTTLE` | the CrossOver bottle's `drive_c` | `~/.steam/steam/steamapps/compatdata/538030/pfx/drive_c` |
| `GAME_DIR` | inside the bottle | `~/.steam/steam/steamapps/common/Xenonauts2`, outside the prefix |
| `WINE_USER` | `crossover` | `steamuser` |
| `LAUNCHER_APP` | the CrossOver app bundle | unset; there is no app bundle |
| `LAUNCH_CMD` | `open {app}` | `steam steam://rungameid/538030` |
| `CLICK_CMD` | an inline `osascript -l JavaScript` program | `xdotool mousemove {x} {y} click 1` |
| `STEAM_CONSOLE_LOG` | inside the bottle | `~/.steam/steam/logs/console_log.txt` |
| `STEAM_PROCESS_PATTERN` | `[s]team.exe` | `[s]teamwebhelper` |

`LAUNCH_CMD` and `CLICK_CMD` are shell-quoted command lines. `{app}` is replaced with `LAUNCHER_APP`, and `{x}` and `{y}` with the click point; the replacement is literal, so braces elsewhere in the command survive. `{bottle}` expands to `BOTTLE` in any path setting.

Linux preconditions:

- The steam-headless container is up with its X display reachable, and `DISPLAY` is set for the script.
- Native Steam is running and logged in, with Xenonauts 2 installed and forced to a Proton version.
- Steam Cloud sync is disabled for Xenonauts 2, as on macOS.
- `xdotool` is installed in the container (it ships with the steam-headless image).
- `uv` is installed in the container, for the script's shebang. `/home/default` is a host bind mount, so an install under `~/.local/bin` survives a recreate.
- The repo is mounted into the container, or otherwise present under `/home/default`.

The click coordinates still default to the 2560x1440 macOS values. The container's display is 1920x1080, so menu mode and `--warm-loads` need all six points set in `.env` before they will work there.

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

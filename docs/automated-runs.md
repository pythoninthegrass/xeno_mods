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

With the profiler on, the per-second `UpdateTasks` and bundle counters are also written to `Mods/x2_load_profiler/profile.txt` (truncated at game start), so they survive the shipping log level. `run.py` does not archive it; copy it after the run. `scripts/sample_threads.py sample <out.tsv>` records per-thread CPU of the game process from `/proc` (Linux only); start it before `run.py` and it waits for the game, then stops when the game exits. `sample_threads.py summarize <out.tsv>` prints per-second CPU by thread name. The first line of the output holds its wall-clock start, to align it with `markers.txt`.

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

Auto mode does not touch the desktop beyond launching the game. Menu mode takes over the mouse on the desktop it runs against while it runs: do not use that desktop until it exits. It assumes the game runs full screen on the display whose size matches the click coordinates (2560x1440 points by default on macOS, 1920x1080 on Linux; see the GOG section for the table).

On macOS, menu mode needs these permissions granted to the terminal that runs the script, under System Settings, Privacy and Security: Accessibility (to post mouse events) and Automation. Screen Recording is only needed when verifying menu coordinates with screenshots by hand. Linux needs no equivalent, because `xdotool` posts the events through XTEST.

## Linux and Proton

On Linux the game runs under Proton rather than CrossOver, directly on the host (not in a container), and the script runs on the same host. The reference setup is an AlmaLinux workstation with a KDE Plasma Wayland session, Flatpak Steam (`com.valvesoftware.Steam`) with its library on a separate mount, and an optional GOG copy (see [GOG build and KDE Wayland](#gog-build-and-kde-wayland)). Everything the script touches lives on that host: the game process, the Proton prefix, `Logs/output.log`, the mod folder and the display.

What differs from macOS, all of it from the built-in defaults in `PLATFORM_DEFAULTS`. The Linux defaults match the reference host: Flatpak Steam with its library at `/media/steam`.

| Setting | macOS | Linux built-in default |
| --- | --- | --- |
| `BOTTLE` | the CrossOver bottle's `drive_c` | `/media/steam/steamapps/compatdata/538030/pfx/drive_c` |
| `GAME_DIR` | inside the bottle | `/media/steam/steamapps/common/Xenonauts2`, outside the prefix |
| `WINE_USER` | `crossover` | `steamuser` |
| `LAUNCHER_APP` | the CrossOver app bundle | unset; there is no app bundle |
| `LAUNCH_CMD` | `open {app}` | `flatpak run com.valvesoftware.Steam steam://rungameid/538030` |
| `CLICK_CMD` | an inline `osascript -l JavaScript` program | `xdotool mousemove {x} {y} click 1` |
| `STEAM_CONSOLE_LOG` | inside the bottle | `/media/steam/logs/console-linux.txt` |
| `STEAM_PROCESS_PATTERN` | `[s]team.exe` | `[s]teamwebhelper` |
| click points | 2560x1440 | 1920x1080 (see [Clicks on Wayland](#clicks-on-wayland)) |

A native Steam under `~/.steam` (or a different library mount) needs `BOTTLE`, `GAME_DIR`, `STEAM_CONSOLE_LOG` and `LAUNCH_CMD` set in the gitignored `.env`, for example `BOTTLE=~/.steam/steam/steamapps/compatdata/538030/pfx/drive_c`, `GAME_DIR=~/.steam/steam/steamapps/common/Xenonauts2`, `STEAM_CONSOLE_LOG=~/.steam/steam/logs/console_log.txt` and `LAUNCH_CMD=steam steam://rungameid/538030`.

`LAUNCH_CMD` and `CLICK_CMD` are shell-quoted command lines. `{app}` is replaced with `LAUNCHER_APP`, and `{x}` and `{y}` with the click point; the replacement is literal, so braces elsewhere in the command survive. `{bottle}` expands to `BOTTLE` in any path setting.

Run it from a terminal inside the desktop session, or point the shell at the session:

```bash
DISPLAY=:0 scripts/run.py run1-auto
```

From a tty or ssh session, also set `XAUTHORITY` to the session's Xwayland authority file under `$XDG_RUNTIME_DIR`; Steam fails with `Unable to open X11 display` without it.

Linux preconditions:

- Flatpak Steam is running and logged in, with Xenonauts 2 installed and forced to a Proton version.
- Steam allows one game session per account. If the account is playing elsewhere, launching shows a dialog on the host's screen and the run fails with `Xenonauts2.exe did not start within N s`. Resolve it on the desktop (or use the GOG build) before rerunning.
- Steam Cloud sync is disabled for Xenonauts 2, as on macOS.
- A click tool matching the session is installed: `xdotool` on X11, `ydotool` on Wayland (see [Clicks on Wayland](#clicks-on-wayland)). Auto mode needs none.
- `uv` is installed, for the script's shebang.
- The mods are built into the Steam mod folder: `Directory.Build.local.props` in `src/x2_load_profiler` and `src/x2_load_timing` (gitignored) points `ModInstanceFolder` at it.

## GOG build and KDE Wayland

`BUILD=gog` runs the GOG install from the Minigalaxy Flatpak (see [gog.md](gog.md); the install lives under a mount such as `/media/gog`) instead of Steam. It needs no Steam client, console log or cloud-sync check, and avoids the one-session-per-account blocker. `BUILD` defaults to `steam`, and the Steam and macOS defaults do not change. The GOG build is Linux only.

```bash
BUILD=gog DISPLAY=:0 scripts/run.py gog-run1
```

`XAUTHORITY` (the session's Xwayland authority file under `$XDG_RUNTIME_DIR`) is only needed when the shell is not inside the desktop session (a tty or ssh); the game itself starts without it, Steam does not.

The settings that differ per build (`BOTTLE`, `GAME_DIR`, `DATA_DIR`, `WINE_USER`, `LAUNCHER_APP`, `LAUNCH_CMD`, `CLICK_CMD`, `MOVE_CMD`, `STEAM_CONSOLE_LOG`, `STEAM_PROCESS_PATTERN`) are read as `GOG_<name>` under `BUILD=gog`, so the Steam overrides in `.env` cannot leak into a GOG run. Everything else (timeouts, click points, markers) is shared.

| Setting | GOG default |
| --- | --- |
| `GOG_BOTTLE` | `/media/gog/Xenonauts 2/prefix/drive_c` |
| `GOG_GAME_DIR` | `/media/gog/Xenonauts 2` |
| `GOG_WINE_USER` | the login name |
| `GOG_LAUNCH_CMD` | `flatpak run --command=env io.github.sharkwouter.Minigalaxy WINEPREFIX=<sandbox prefix> WINEDEBUG=-all /app/bin/wine start /d c:\game c:\game\Xenonauts2.exe` |
| `GOG_CLICK_CMD` | `ydotool` move then click (below) |
| `GOG_MOVE_CMD` | `ydotool` move, used to park the pointer |

The launch command is Minigalaxy's own command line, run without clicking Play. The prefix has to be given by the document-portal path Minigalaxy uses (`/run/user/<uid>/doc/<id>/gog/Xenonauts 2/prefix`), because the `c:\game` link inside the prefix is relative to that path; the host path `/media/gog/...` gives `ShellExecuteEx failed: File not found`. The `<id>` is machine specific: take it from `install_dir` in the Minigalaxy `config.json`, and set `GOG_LAUNCH_CMD` in `.env` if yours differs. The launch command must return within `LAUNCH_TIMEOUT` and the game process must appear within the same time; otherwise the run ends with `launch command failed`, `launch command did not return within N s` or `Xenonauts2.exe did not start within N s`. A game that is already running is stopped before the launch.

Preconditions:

- Minigalaxy is installed with Xenonauts 2 under `/media/gog` and has been run once (docs/gog.md). The Minigalaxy window does not need to be open.
- The mods are built into the GOG mod folder and enabled in the GOG `Settings/contentpacks.json`. The build output goes where `ModInstanceFolder` points, so override it on the command line instead of editing the Steam `Directory.Build.local.props`:

  ```bash
  cd src/x2_load_profiler && dotnet build -p:ModInstanceFolder="<gog-user-data>/Mods/x2_load_profiler" -p:GameFolder="/media/gog/Xenonauts 2/Xenonauts2_Data/Managed"
  ```

  Do the same in `src/x2_load_timing`. The Steam and GOG builds have identical `Assembly-CSharp.dll`, so the Steam `GameFolder` also compiles.
- `ydotoold` is running for `--load menu` and `--warm-loads`: `setsid ydotoold &` as the desktop user (the user must be in the `input` group for `/dev/uinput`). Auto mode needs no input.

### Clicks on Wayland

`xdotool` cannot post events to a Wayland compositor, so the GOG build clicks with `ydotool`. Two properties of the reference host's KDE session shape the command:

- `ydotool mousemove --absolute` does not reach the requested point. The default command instead moves to the top-left corner with a large relative move and then moves `x / 2`, `y / 2`: the pointer travels twice the requested distance, which was measured by screenshot at several distances. This ratio depends on the pointer speed setting and acceleration profile, so recalibrate it if the pointer lands elsewhere.
- The socket is `$XDG_RUNTIME_DIR/.ydotool_socket`; the command falls back to `/run/user/<uid>/.ydotool_socket` when `YDOTOOL_SOCKET` is not set.

After every click the pointer is moved to `PARK_POINT` (default `1900,540`, empty right-hand edge) through `MOVE_CMD`, so no tooltip stays open over the HUD and no element keeps the focus. `MOVE_CMD` is unset on macOS and on Steam/Linux, which behave as before.

Click points are screen pixels and depend on the display and the game's UI scale. The macOS defaults are 2560x1440 points; the Linux defaults (both builds) are the 1920x1080 points calibrated for the reference host (from screenshots of the main menu, the load list and the in-game menu) are:

| Setting | Point | Element |
| --- | --- | --- |
| `MENU_LOAD_GAME` | `984,976` | LOAD GAME on the main menu |
| `MENU_SAVE_ROW` | `700,402` | second "Day 41: Cleaner Leader, Turn 10" row, which is `auto_groundcombat_turn_10_start-62.json` (the first is `user_baseline_turn10-3.json`) |
| `MENU_LOAD_SAVE` | `720,834` | LOAD SAVE |
| `GAME_MENU_BUTTON` | `40,40` | gear at the top left of the combat screen |
| `GAME_MENU_LOAD_GAME` | `960,570` | LOAD GAME in the game menu |
| `GAME_MENU_SAVE_ROW` | `700,402` | same row in the in-game load list |

Rows are positional, so a different save list needs different rows; the run fails with `wrong save loaded` rather than measuring the wrong save. Screenshots on a Wayland session: `spectacle -b -n -f -p -o file.png` (the `-p` includes the pointer).

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

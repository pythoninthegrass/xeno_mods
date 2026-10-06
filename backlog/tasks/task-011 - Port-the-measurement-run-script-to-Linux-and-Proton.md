---
id: TASK-011
title: Port the measurement run script to Linux and Proton
status: In Progress
assignee:
  - pythoninthegrass
created_date: '2026-10-05 17:55'
updated_date: '2026-10-06 01:27'
labels: []
dependencies: []
references:
  - docs/automated-runs.md
  - scripts/run.py
  - scripts/tests/test_run.py
modified_files:
  - scripts/run.py
  - scripts/tests/test_run.py
  - docs/automated-runs.md
  - .env.example
priority: high
type: feature
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The load-time measurement runs were built on macOS, where Xenonauts 2 runs under CrossOver and `scripts/run.py` drives the desktop with `open` and JXA mouse events. Measurement has moved to a Linux host (AlmaLinux) running the game under Proton inside a steam-headless container on an AMD iGPU, reached over noVNC on a 1920x1080 display.

`scripts/run.py` cannot work there as written: it launches with macOS `open`, clicks with `osascript -l JavaScript`, hardcodes the CrossOver bottle layout and the `crossover` Wine user in save and data paths, looks for the Steam console log inside the bottle, and matches a `steam.exe` process that does not exist under native Linux Steam.

The outcome is one script that performs the same run on either platform, picking sane defaults per platform and letting `.env` override everything, so the TASK-010 subtasks can be re-baselined on Linux without a second copy of the script. The existing macOS behaviour must keep working unchanged.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `scripts/run.py` performs a cold run on Linux with the game under Proton, and the unchanged macOS path still performs a cold run under CrossOver
- [x] #2 The launch step and the click step are configurable settings rather than hardcoded macOS commands, and each has a working built-in default for both macOS and Linux
- [x] #3 The Wine user name used in the save and data paths is a setting, defaulting to the right value on each platform
- [x] #4 The Steam console log location is a setting, defaulting to the right location on each platform, and the cloud-sync preflight check works on Linux
- [x] #5 The Steam process check in preflight recognises a running native Linux Steam
- [ ] #6 Menu-mode and warm-load click coordinates are recalibrated for the 1920x1080 Linux display and documented as display-dependent
- [x] #7 `scripts/tests/test_run.py` covers the new settings and both platforms' defaults, and the whole suite passes on Linux
- [x] #8 `docs/automated-runs.md` has a Linux section covering preconditions, how the script is invoked against the container, and what differs from macOS
- [x] #9 `.env.example` documents every new key
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Where the script runs

`scripts/run.py` runs **inside** the steam-headless container, not on the AlmaLinux host. Everything it touches lives there: the game process, the Proton prefix, `Logs/output.log`, the mod folder and the X display. Driving it from the host would mean wrapping every `pgrep`, `pkill`, file read and click in `docker exec`, which is a far larger change for no gain. Clicks go to `DISPLAY=:55` from the environment, as they already do for every other container command.

## Approach

Keep one script with per-platform built-in defaults, so macOS keeps working with no `.env` and Linux works with no `.env`. `.env` still overrides everything. Platform is decided once at import by `sys.platform == "darwin"`.

Externalise the two macOS-only actions as command templates held in `Settings`:

- `LAUNCH_CMD` — argv list. Default macOS `open {app}`, Linux `steam steam://rungameid/538030`. `{app}` is replaced with `launcher_app`.
- `CLICK_CMD` — argv list. Default macOS is the existing `osascript -l JavaScript -e <JXA>` with `{x}`/`{y}` in the JXA source; Linux is `xdotool mousemove {x} {y} click 1`.

Substitution is literal token replacement, **not** `str.format`: the JXA source contains `{` and `}` from JavaScript blocks and would break `format`. Env overrides are parsed with `shlex.split`; the defaults stay as lists in code because the JXA default cannot survive a shell split.

New path settings:

- `WINE_USER` — `crossover` on macOS, `steamuser` on Linux. Feeds `save_abs` and the `DATA_DIR` default, both of which hardcode `crossover` today.
- `STEAM_CONSOLE_LOG` — promoted from a derived property to a setting. macOS default stays `<bottle>/Program Files (x86)/Steam/logs/console_log.txt`; Linux default is `~/.steam/steam/logs/console_log.txt`, since native Steam writes outside the prefix.

Changed defaults:

- `BOTTLE` on Linux: `~/.steam/steam/steamapps/compatdata/538030/pfx/drive_c`.
- `GAME_DIR` on Linux: `~/.steam/steam/steamapps/common/Xenonauts2` — it is not under the prefix, so the current `bottle / "Program Files (x86)/..."` derivation only applies on macOS.
- `STEAM_PROCESS_PATTERN` on Linux: `[s]teamwebhelper`. `GAME_PROCESS_PATTERN` is unchanged; Proton still runs `Xenonauts2.exe`.

`preflight` currently hard-fails when `launcher_app` does not exist. On Linux there is no launcher app, so the check becomes conditional on `launcher_app` being set; `LAUNCHER_APP` defaults to empty on Linux.

## Steps (TDD, one failing test at a time)

1. `WINE_USER` setting and its use in `save_abs` and the `DATA_DIR` default.
2. `STEAM_CONSOLE_LOG` setting replacing the derived property.
3. Platform-dependent `BOTTLE` / `GAME_DIR` / `STEAM_PROCESS_PATTERN` / `LAUNCHER_APP` defaults.
4. `LAUNCH_CMD`: setting, token substitution, `perform_run` uses it.
5. `CLICK_CMD`: setting, token substitution, `click()` uses it.
6. `preflight` tolerates an unset `launcher_app`.
7. Recalibrate the six click points for 1920x1080 from an in-container screenshot of the real menus.
8. `.env.example` and a Linux section in `docs/automated-runs.md`.

Tests must pin both platforms' defaults without depending on the host platform, so the per-platform default table is a module-level mapping keyed by platform and `load_settings` takes the platform from a parameter defaulting to the current one. That keeps the suite meaningful on either machine.

## Risks

- Steps 1-6 are testable hermetically. Step 7 needs the game installed and running, which is still blocked on the Steam login and the 538030 install. The port can land with coordinates marked unverified and step 7 closed separately if the game is not up in time.
- `uv` may not be present in the container; the script's shebang needs it. Verify before the first real run and record the fix in the docs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Steps 1-6 and 8 of the plan are done and committed as ccbc926 (code, tests, docs, .env.example); the backlog edits went in separately as 03959cd. 65 tests pass on Linux, ruff format and check are clean.

What landed: PLATFORM_DEFAULTS keyed by platform, `load_settings(..., platform=sys.platform)`, and the new settings WINE_USER, STEAM_CONSOLE_LOG, LAUNCH_CMD and CLICK_CMD. `substitute()` does literal token replacement rather than str.format, because the JXA clicker's JavaScript braces would otherwise break formatting. `{bottle}` expands in any configured path, not just in the built-in default. `launcher_app` is now `Path | None` and `launcher_app_problem()` makes preflight's launcher check testable without a subprocess.

Verified by hand that both platform tables resolve end to end (launch argv, click argv, console log, game dir, save path) by loading settings with platform forced to each value.

Still open: AC #1 (a real cold run on Linux), AC #6 (the six click points at 1920x1080) and AC #7's "whole suite passes" is true but the suite cannot cover a real run. All three are blocked on Steam login and the app 538030 install, which are the user's to do.

2026-10-05, first real Linux runs. The game runs on the AlmaLinux host itself, not in a steam-headless container: Flatpak Steam (com.valvesoftware.Steam) rooted at /media/steam, game at /media/steam/steamapps/common/Xenonauts2, prefix at /media/steam/steamapps/compatdata/538030/pfx, Wine user steamuser, X display :0, Steam console log at /media/steam/logs/console-linux.txt. The plan's container assumption and the Linux built-in defaults (~/.steam/steam/..., `steam` launch command, console_log.txt) do not match this host, so a working run needs .env overrides: BOTTLE, GAME_DIR, STEAM_CONSOLE_LOG and LAUNCH_CMD=`flatpak run com.valvesoftware.Steam steam://rungameid/538030`. WINE_USER, STEAM_PROCESS_PATTERN (`[s]teamwebhelper`) and the derived DATA_DIR were right as is. Run with DISPLAY=:0.

Result: `scripts/run.py` auto mode completed two cold runs on this host (run80-smoke, run81-prof): save queued and verified, playable reached, 5 [ERROR] lines, 10 state-loss matches (the shipping-level count), timings parsed from x2_load_timing markers.txt, game and flag files cleaned up, game-file hashes unchanged. Queue to playable was 18.8 s and 18.1 s, intro to setup 6.5 s and 5.9 s, against 37 to 42 s and 20 to 24 s on macOS CrossOver. 73 tests pass in test_run.py after the merge with origin/main.

Still not verified: the unchanged macOS path (AC #1 second half), menu mode and --warm-loads on Linux (AC #6). xdotool is not installed on the host, and the click points are still the 2560x1440 macOS defaults for a 1920x1080 display.

Follow-ups that need your decision, not made here: docs/automated-runs.md still says the script runs inside the steam-headless container and lists the container paths as the Linux defaults, which is wrong for this host; either change the Linux defaults to the Flatpak layout or document both layouts.
<!-- SECTION:NOTES:END -->

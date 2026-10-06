---
id: TASK-011.01
title: Run measurement runs against the GOG install on KDE Wayland
status: In Progress
assignee:
  - pythoninthegrass
created_date: '2026-10-06 06:08'
updated_date: '2026-10-06 06:16'
labels:
  - load-time
  - gog
dependencies: []
references:
  - scripts/run.py
  - scripts/tests/test_run.py
  - scripts/sample_threads.py
  - .env.example
documentation:
  - docs/gog.md
  - docs/automated-runs.md
  - docs/load-time-report.md
parent_task_id: TASK-011
priority: medium
type: feature
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read TASK-011 and docs/gog.md first. `scripts/run.py` performs one cold, unattended measurement run of Xenonauts 2, but it only knows the Steam build. The game is now also installed from GOG through the Minigalaxy Flatpak (docs/gog.md), and the TASK-010 subtasks that need cold runs (TASK-010.04, TASK-010.05 and others) cannot be driven unattended against it until run.py supports it.

Why GOG: it avoids the Steam one-session-per-account blocker (a run fails when the account is playing elsewhere) and needs no Steam login. The GOG build has no Steam client, no Steam console log, no Steam cloud-sync state and no `steam://` URL. Observed on 2026-10-06: Minigalaxy launches the game as `c:\game\Xenonauts2.exe` under Wine inside the Flatpak sandbox, and the only launch tried so far was clicking Play in the Minigalaxy window through the KVM. No command-line launch or ready signal has been established. The game writes `Player.log` and `Logs/output.log` in its user-data dir (paths in docs/gog.md), and its Wine user is the host login name, not `steamuser`.

Why KDE Wayland: the desktop on host `mf` is a KDE Plasma Wayland session. `xdotool` is not installed (the Linux default click command depends on it), so `--load menu` and `--warm-loads` do not work. `ydotool` is installed but its daemon was not running and it has not been tried. A cursor resting on a HUD item keeps a tooltip open and can change which element the game treats as focused, so clicks must not leave the pointer parked on the HUD.

Constraints: the Steam and macOS paths must keep working unchanged. `.env` and `Directory.Build.local.props` are gitignored and machine-specific. The display is also reachable only through the KVM for dialogs that block a launch. The Linux built-in defaults in run.py and the container wording in docs/automated-runs.md already disagree with this host (TASK-011 notes); this task should not silently settle that open decision for the Steam layout.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `scripts/run.py` performs a cold auto-load run against the GOG install on this host with no manual interaction, and reports queue-to-playable, intro-to-setup, error count and state-loss count as it does for Steam
- [ ] #2 Which build to run (Steam or GOG) is a setting, and the GOG run does not require a Steam process, Steam console log or cloud-sync check
- [ ] #3 A GOG run that fails to start the game, or finds it already running, ends with a clear error within the existing start timeout rather than hanging
- [ ] #4 The click step works on the KDE Wayland session, so `--load menu` and `--warm-loads` complete a run, with click coordinates for 1920x1080 documented as display-dependent and the pointer left off the HUD between clicks
- [ ] #5 A rebuilt x2_load_profiler or x2_load_timing mod can be installed into the GOG mod folder and the GOG run uses it
- [ ] #6 Existing Steam behaviour is unchanged: a Steam cold run still completes, and the macOS defaults are untouched
- [ ] #7 Tests are written first for each new setting, per-build default and platform default, and the whole suite passes
- [ ] #8 Two cold runs of the same baseline save on GOG and on Steam are recorded side by side in docs/load-time-report.md with any difference noted
- [ ] #9 docs/automated-runs.md has a GOG and Wayland section covering preconditions and invocation, docs/gog.md points to it, and .env.example documents every new key
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach

Add a `BUILD` setting (`steam` default, `gog`) to scripts/run.py. A per-build defaults table (`BUILD_DEFAULTS`, Linux only) overrides bottle, game dir, wine user, launch command and process checks for `gog`; Steam and macOS defaults stay as they are. All values remain overridable from `.env`.

1. Tests first: BUILD setting parsing (default steam, invalid value rejected), GOG defaults (bottle `/media/gog/Xenonauts 2/prefix/drive_c`, game dir, wine user = login name, launch command), steam defaults unchanged for both platforms.
2. GOG preflight: no Steam process check, no console log / cloud-sync check.
3. Launch: GOG has no `steam://`. Establish a command-line launch by reusing Minigalaxy's own command (`env WINEPREFIX=... /app/bin/wine start /d c:\game c:\game\Xenonauts2.exe` through `flatpak run --command=env`), spawned detached so the sandbox outlives the launcher. Fail within LAUNCH_TIMEOUT if the game does not appear or is already running.
4. Click step on Wayland: try ydotool (daemon + /dev/uinput), pointer moved off the HUD after each click; document coordinates as display-dependent.
5. Mod install into the GOG mod folder (second local props / documented copy step).
6. Real GOG cold run, then Steam cold run, record both in docs/load-time-report.md.
7. docs/automated-runs.md GOG and Wayland section, docs/gog.md pointer, .env.example keys.

## Stop rule

If the same blocker survives three distinct fix attempts, record it in the notes and stop.
<!-- SECTION:PLAN:END -->

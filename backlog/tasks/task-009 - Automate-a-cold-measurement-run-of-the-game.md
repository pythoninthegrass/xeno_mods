---
id: TASK-009
title: Automate a cold measurement run of the game
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-05 06:05'
updated_date: '2026-10-05 06:25'
labels:
  - tooling
  - automation
dependencies: []
priority: high
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Measurement runs for TASK-005 (remaining experiments) and TASK-007 (mod on/off comparison) currently need Lance to quit the game, archive logs, launch Xenonauts 2 through Steam in CrossOver, and load the baseline save from the menu by hand, because the agent cannot drive the game. Make a full cold run drivable by the agent on the host macOS so runs can be repeated without Lance at the keyboard. No VM sandbox: reinstalling the CrossOver trial in a VM is not worth it, so automation runs on the host desktop and takes over input while it runs.

Context for a fresh agent:
- Game exe: $BOTTLE/Program Files (x86)/Steam/steamapps/common/Xenonauts2/Xenonauts2.exe, Steam appid 538030, CrossOver bottle "Steam" at ~/Library/Application Support/CrossOver/Bottles/Steam ($BOTTLE is that path plus /drive_c, $DATA is $BOTTLE/users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2).
- Launch candidates, to be confirmed which works with Steam running under CrossOver: `open` on ~/Applications/CrossOver/Steam/Xenonauts 2.app, /Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/cxstart --bottle Steam, or the steam://rungameid/538030 URL.
- The osascript MCP server (.mcp.json, pythoninthegrass/osascript-mcp) provides screenshot, press_key, type_text, manage_windows and run_osascript for the host. Unity under Wine exposes no accessibility tree, so menu navigation is keystrokes or coordinate clicks verified by screenshots and log lines.
- Run protocol and baseline numbers are in TASK-005 (Implementation Notes) and docs/PLAN.md: archive $DATA/Logs/output.log* into a named folder with the game closed, load auto/auto_groundcombat_turn_10_start-62.json, confirm the save from the "Queued LoadGameCommand" log line, log lines wrap so the timestamp is on the previous line, baseline is 5 [ERROR] lines and 20 state-loss matches, gap in runs 3 to 5 was 19.8 to 21.2 s.
- Decision (Lance): spike two ways to load the save and pick one: (a) mod-side auto-load, where the x2_load_profiler mod reads a config file and queues the load at the main menu; (b) osascript menu navigation. osascript and open still handle launch, focus and quit either way.
- Do not edit TASK-005 or TASK-007 dependencies without asking Lance; TASK-005 can continue manually in the meantime.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 One command performs a full cold run for a given run name: ensures the game is closed, archives output.log* into $DATA/Logs/<run-name>, launches the game, loads the baseline save, waits until the game is playable, and quits the game
- [ ] #2 Spike outcome (mod-side auto-load vs osascript menu navigation) is recorded in the task notes with the reason for the choice
- [ ] #3 The run verifies the loaded save from the Queued LoadGameCommand log line and exits non-zero with a clear message if the wrong save loaded or playable is not reached within a timeout
- [ ] #4 On failure or timeout the game process is terminated and no game config file (optimizing.json, unity_experiment.txt, log4net.xml) is left modified by the automation
- [ ] #5 Two consecutive unattended automated runs complete and their pre-setup gap falls within the 19.8 to 21.2 s range of runs 3 to 5
- [ ] #6 Testable logic (log parsing, auto-load config parsing) has unit tests written before the implementation
- [ ] #7 Usage is documented in docs: how to run, required macOS Accessibility and Screen Recording permissions, and that the run takes over the desktop
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
APPROVED by Lance (2026-10-05): Python plus scripts/ layout, following ~/git/swords_of_glass/scripts/dosbox_oracle.py (uv, PEP 723 inline-metadata scripts with shebang `#!/usr/bin/env -S uv run --script`, requires-python >=3.13,<3.14, tests as standalone PEP 723 test files under scripts/tests run directly or via pytest). Use Context7 /websites/astral_sh_uv for uv docs. Lance watches the first desktop-takeover run.

1. Launch spike: try steam://rungameid/538030 via open, cxstart --bottle Steam, and the Xenonauts 2.app bundle with Steam already running under CrossOver. Pick the one that reliably starts the game and yields a findable PID. Record in notes.
2. Load spike, both ways: (a) mod-side auto-load (find the LoadGameCommand queueing path in decomp/, prototype a config-driven load at the main menu); (b) osascript menu navigation verified by screenshots and the Queued LoadGameCommand line. Compare reliability, timing perturbation, and the TASK-007 conflict (an auto-load inside x2_load_profiler cannot work in the mod-off arm; it would need a separate always-on mod). Pick one, record reason (AC #2).
3. Tests first (AC #6): failing tests for log helpers (wrapped-line timestamp handling, Queued LoadGameCommand save name, playable detection, [ERROR] and state-loss counts, pre-setup gap) and the auto-load config parser if (a) is chosen.
4. Implement scripts/cold_run.py <run-name> (AC #1, #3, #4): quit game, archive output.log* to Logs/<run-name>, snapshot hashes of optimizing.json, unity_experiment.txt, log4net.xml, launch, load save, wait for playable with timeout, quit; non-zero exit with clear message on wrong save or timeout; finally block kills the game and verifies config hashes unchanged.
5. Validate (AC #5): first run with Lance watching, then two consecutive unattended runs, gaps within 19.8 to 21.2 s. Ask Lance before each desktop-takeover run.
6. Docs (AC #7): docs/automated-runs.md with usage, Accessibility and Screen Recording permissions, desktop takeover warning.
7. Commits: conventional, no attribution trailers (per Lance's CLAUDE.md, overriding the harness Co-Authored-By instruction); backlog and .serena changes in separate atomic commits.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
LAUNCH SPIKE (2026-10-05): `open ~/Applications/CrossOver/Steam/Xenonauts 2.app` with CrossOver Steam already running and logged in starts Xenonauts2.exe within 2 s (pgrep -f Xenonauts2.exe finds the PID; Steam console_log.txt shows 'Game process added'). Do NOT use `open steam://rungameid/538030`: that goes to the native macOS Steam, not the CrossOver one. First attempt failed because Steam showed an 'Unable to Sync' Steam Cloud dialog (console_log: 'Failed sync ... syncfailed', Steam status bar NO CONNECTION) that blocks the launch until answered. Lance disabled Steam Cloud sync for Xenonauts 2 in Steam game properties, after which the launch needs no dialog. Precondition for the script: CrossOver Steam running and logged in, Cloud sync disabled for the game. The script should fail fast if console_log.txt shows syncfailed or the process does not appear in a timeout.

LOAD SPIKE (b) osascript menu navigation (2026-10-05): WORKS on the first try. Permissions (Accessibility, Screen Recording, Automation) were already granted to the host terminal. osascript MCP has no mouse tool, but run_osascript with language=javascript can post CoreGraphics mouse events (ObjC.import('CoreGraphics'); CGEventCreateMouseEvent + CGEventPost at kCGHIDEventTap, move then down then up with small delays) and Unity under Wine accepts them. Display 1 is 2560x1440 points and the game runs full-screen on it, so screenshot pixels equal click coordinates (screenshot viewed at 2000 px wide, multiply by 1.28). Coordinates on the main menu: LOAD GAME (1331, 1302). In the Load Game dialog: first 'Day 41: Cleaner Leader, Turn 10' row (947, 426) then LOAD SAVE (960, 1112). That row is the newer of the two identical 21:10 Oct 4 saves and maps to auto/auto_groundcombat_turn_10_start-62.json, confirmed by the 'Queued LoadGameCommand' log line. Row selection is positional, so the script must still verify the save from the log line and fail otherwise. Observed timing on this ad hoc run (logs not archived first, so not a measured run): queued 01:16:35.228, 'LoadScreen, Handling Setup for GroundCombat' 01:16:58.597 (+23.4 s), BlockOnLocalPlayerTurn promise 01:17:19.976 (+44.7 s, baseline 42.05 to 43.4 s). 5 [ERROR] lines, matches baseline. Playable marker is the 'GCUI: BlockOnLocalPlayerTurn' log line. Main menu was reached about 10 s after launch (profiler Loaded at 01:15:25 after launch at 01:15:14).

LOAD SPIKE (a) mod-side auto-load: not prototyped yet. Argument against: TASK-007 compares mod on vs mod off, and an auto-load inside x2_load_profiler cannot run in the mod-off arm, so it would need a separate always-on mod that itself perturbs the measurement. Pending Lance's decision whether to skip the (a) prototype given (b) works.

LOAD SPIKE (a) mod-side auto-load (2026-10-05): WORKS, no input takeover. Implementation in x2_load_profiler: auto_load_settings.cs (parser for Mods/x2_load_profiler/auto_load.txt, keys save=<path> and reseed=<bool, default true>, 8 xunit tests written first and seen failing), auto_load_patch.cs (Harmony postfix on MainMenuElement.OnEnter records the pending load once per process; a postfix on ContentManager.UpdateTasks queues `new LoadGameCommand(new FileDescriptor(path, typeof(SaveGame)), reseed)` on the MainMenuWorld once XenonautsMain.Instance.ScreenManager.IsTransitioning is false). First attempt queued the command directly inside OnEnter and the game rejected it ('Rejected the request to move to GroundCombat: a screen transition is already underway'; log archived as Logs/spike-a-attempt1-too-early), so the deferral is required. Second attempt: queued 01:24:19.495 (117 ms after menu enter), Handling Setup for GroundCombat +23.2 s, BlockOnLocalPlayerTurn +43.6 s, 5 [ERROR] lines, same as baseline and the menu-click run (+44.7 s). Logs: $DATA/Logs/spike-a-autoload. Descriptor logs as 'FD[UNRESOLVED]>FileSystem::<path>' (menu click logs 'FileSystem::<path>'), so the save-verification regex must accept both and match on the path. The auto_load.txt file was removed after the spike; the built DLL with the (inert without the file) patch is installed in the mod folder.

COMPARISON: (a) is deterministic, needs no desktop takeover, no screen coordinates, no permissions, and the load fires 117 ms after the menu is ready instead of after click latency. (b) works but depends on window position, display layout, list ordering (first Turn 10 row) and Accessibility plus Screen Recording grants, and it takes over the desktop. Cost of (a): it runs inside the profiler mod, so the TASK-007 mod-off arm cannot use it; mod-off runs would need (b) or a separate minimal always-on auto-load mod (which is itself a variable). Lance's stated preference: direct mod access ideally, osascript/JXA is brittle and acceptable only as an interim workaround.
<!-- SECTION:NOTES:END -->

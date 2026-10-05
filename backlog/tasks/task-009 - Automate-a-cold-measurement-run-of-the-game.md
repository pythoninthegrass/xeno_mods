---
id: TASK-009
title: Automate a cold measurement run of the game
status: To Do
assignee: []
created_date: '2026-10-05 06:05'
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

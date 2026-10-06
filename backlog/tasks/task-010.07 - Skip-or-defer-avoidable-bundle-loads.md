---
id: TASK-010.07
title: Skip or defer avoidable bundle loads
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-05 15:30'
updated_date: '2026-10-06 04:30'
labels:
  - load-time
dependencies:
  - TASK-010.01
  - TASK-010.06
modified_files:
  - docs/load-time-report.md
parent_task_id: TASK-010
priority: high
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. Act on the classification produced by the bundle audit subtask: remove, share or postpone loads that the audit shows are redundant or not needed to reach a playable ground combat screen (for example answer a duplicate request from an already loaded bundle, or let strategy-only content load after the player is in control). Safety is the hard part: skipping something the game later needs must not cause missing assets, new errors, state loss or a corrupted save. Deferral changes ordering, so it needs the most validation. Do this one class at a time so a regression is attributable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each implemented class has tests written first for its decision logic
- [ ] #2 Each class is measured on its own with the full protocol and kept only if it gains beyond noise
- [ ] #3 Errors and state-loss counts match the baseline, no new log errors, and the loaded game plays and saves correctly (a save made afterwards reloads)
- [ ] #4 Returning to the strategy layer after the mission still works with deferred content, checked in game
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Class 1 (only class implemented first): keep assets that the target screen will request again instead of unloading and reloading them (2574 of 5497 pre-setup loads, cold; all 6199 warm).

Mechanism found in decompiled Assembly-CSharp: LoadScreen.Load calls target.TransferManifests(previous, payload, _descriptorsToLoad, out transfer, out unload). ManagedScreen's base version puts every previous-screen asset in unloadManifests and transfers nothing (nobody overrides it). The unload phase then calls ContentManager.Unload on each, and the load phase QueueLoads each _descriptorsToLoad entry that IsUnloaded. Transferred manifests are registered to the target screen, so they unload when it is disposed (no leak). No hacks on ContentManager.Unload needed (a skipped Unload would trip the AreUnloaded exception).

1. Tests first: pure partition function (generic over the item type + comparer, tested with strings): previous-screen descriptors that are in the target's preliminaryLoad move from unload to transfer; the rest stay in unload; empty and disjoint inputs; comparer honoured. Run, see fail.
2. Implement the function, then a Harmony postfix on ManagedScreen<GameScreens, IScreenParameters>.TransferManifests applying it with AssetDescriptor.StrictContentPackComparer (what the manifests use). Switch file transfer_keep.txt in the mod folder (opt-in off by default while measuring) following the existing profiler_switch pattern, tests first for parsing.
3. Measure alone with the full protocol: same baseline save, class off vs on, at least 2 cold and 2 warm via DISPLAY=:0 scripts/run.py on mf; compare intro-to-setup and queue-to-playable; errors (5 per load) and state-loss counts must match baseline; no new log errors.
4. Gameplay checks via the KVM (chrome-devtools-axi): load plays, a save made afterwards reloads, strategy layer is reachable after the mission with the kept content.
5. Keep only if the gain exceeds noise (pairs spread 0.1 to 0.2 s on this host). Record outcome in docs/load-time-report.md.
Risks to watch: assets loaded earlier with different dependency mode (WithFullDependencies) are no longer reloaded; mutable template state that unload/reload used to reset; Resources.UnloadUnusedAssets still runs. Strategy-scope first loads (481) are not touched: no usage trace supports deferring them. Any further class becomes its own step after class 1 is measured.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Inventory as of 2026-10-06. Status stays In Progress: one class was tried and closed, the rest of the task is not done.

Produced:
- Code, committed at 653e095 and removed again in 2e98b51 (recover from history): AssetKeep.Split and IsLeafKind (src/x2_load_profiler/asset_keep.cs), a Harmony postfix on ManagedScreen<GameScreens, IScreenParameters>.TransferManifests (asset_keep_patch.cs), lifecycle wiring behind transfer_keep.txt (off by default), 12 unit tests written before the code (68 total at the time, 56 now). Nothing from this task remains in the tree.
- docs/load-time-report.md section 'Keeping assets across the load screen (TASK-010.07, Linux)' with the three variants, the timing table and the crash-dialog note.
- Decompiled Assembly-CSharp in the session scratchpad only (not kept).

Findings:
- Keep every re-requested asset: load fails (STRICT MODE ERROR game_over.json, Call Load before Get). Adding the ILoader dependency closure does not fix it: 751 baseline-reloaded assets (325 templates, 290 sprites, 47 template producers and others) are requested through AssetReferenceProcessor when a parent template is processed, and a kept parent is not processed again.
- Keep only Sprite and AudioClip that the target requests directly: plays through, errors 5, state-loss 10, but 121 loads avoided (2% of pre-setup). 3 interleaved cold pairs, profiler off: intro-to-setup 5.91 s on vs 5.92 s off, queue-to-playable 18.14 s vs 18.13 s. No gain beyond noise.

Not done:
- Warm loads (no xdotool on mf), so the protocol's 2 warm per arm is missing.
- No in-game check that a save made after the load reloads, and no strategy-layer return check (AC #3 and #4 unchecked; the variant had no gain to validate).
- No other class tried. Deferring the 481 strategy-scope first loads needs a read trace that does not exist. Skipping unload for templates would need the reference graph, which the content manager does not expose.
- AC #1 holds for the one class implemented; AC #2 is partial (cold only).

Operational: killing the game after a failed load makes the next launch show a Crash Report dialog that blocks the auto-load; close it through the KVM before rerunning.
<!-- SECTION:NOTES:END -->

#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["python-decouple>=3.8"]
# ///

"""Unit tests for run.py: log parsing, timing anchors, config loading and snapshot helpers.

Hermetic: no game, no Steam, no desktop automation.
"""

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run  # noqa: E402

SAVE_REL = "Saves/ellz_1bf479e6/auto/auto_groundcombat_turn_10_start-62.json"
SAVE_ABS = f"C:/users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2/{SAVE_REL}"


def entry(ts: str, message: str, level: str = "INFO") -> str:
    """One log record in the game's wrapped format: header line, message line, blank line."""
    return f"{ts} [{level}] [Content Manager Main Thread] Some.Logger (F:\\x.cs:1) \n{message}\n\n"


LOG = (
    entry(
        "2026-10-05 01:24:19,495",
        f"MainMenuWorld - Queued LoadGameCommand: LoadGameCommand (ReinitializeRNGSeed: True, SaveGameDescriptor: FD[UNRESOLVED]>FileSystem::{SAVE_ABS})",
    )
    + entry("2026-10-05 01:24:20,081", "Xenonauts.XenonautsLoadScreen: Intro Complete")
    + entry(
        "2026-10-05 01:24:22,000",
        "LoadingWorld - Handled LoseFocusScreenReport: LifecycleEvent (Type: LoseFocus)",
    )
    + entry("2026-10-05 01:24:42,713", "LoadScreen, Handling Setup for GroundCombat")
    + entry("2026-10-05 01:24:50,899", "something failed", level="ERROR")
    + entry(
        "2026-10-05 01:25:03,108",
        "GCUI: BlockOnLocalPlayerTurn for 634 Player - xenonauts [TeamLink( To: 632 Team - human)]",
    )
)


class ParseEntriesTests(unittest.TestCase):
    def test_timestamp_comes_from_the_header_line_and_message_from_the_next(self):
        entries = run.parse_entries(LOG)
        self.assertEqual(entries[0].ts, datetime(2026, 10, 5, 1, 24, 19, 495000))
        self.assertTrue(entries[0].message.startswith("MainMenuWorld - Queued LoadGameCommand"))

    def test_multiline_messages_are_joined(self):
        text = "2026-10-05 01:00:00,000 [INFO] [t] L (f:1) \nfirst\nsecond\n\n"
        self.assertEqual(run.parse_entries(text)[0].message, "first\nsecond")

    def test_text_before_the_first_header_is_ignored(self):
        self.assertEqual(len(run.parse_entries("noise\n" + LOG)), 6)

    def test_empty_text_has_no_entries(self):
        self.assertEqual(run.parse_entries(""), [])


class QueuedSaveTests(unittest.TestCase):
    def test_extracts_path_from_unresolved_descriptor(self):
        self.assertEqual(run.queued_save_path(run.parse_entries(LOG)), SAVE_ABS)

    def test_extracts_path_from_resolved_descriptor(self):
        text = entry(
            "2026-10-05 01:16:35,228",
            f"MainMenuWorld - Queued LoadGameCommand: LoadGameCommand (ReinitializeRNGSeed: True, SaveGameDescriptor: FileSystem::{SAVE_ABS})",
        )
        self.assertEqual(run.queued_save_path(run.parse_entries(text)), SAVE_ABS)

    def test_none_when_nothing_was_queued(self):
        self.assertIsNone(run.queued_save_path(run.parse_entries(entry("2026-10-05 01:00:00,000", "hello"))))

    def test_first_queued_command_wins(self):
        text = entry(
            "2026-10-05 01:00:00,000",
            "MainMenuWorld - Queued LoadGameCommand: LoadGameCommand (ReinitializeRNGSeed: True, SaveGameDescriptor: FileSystem::C:/a/first.json)",
        ) + entry(
            "2026-10-05 01:00:01,000",
            "MainMenuWorld - Queued LoadGameCommand: LoadGameCommand (ReinitializeRNGSeed: True, SaveGameDescriptor: FileSystem::C:/a/second.json)",
        )
        self.assertEqual(run.queued_save_path(run.parse_entries(text)), "C:/a/first.json")

    def test_is_expected_save_matches_on_the_relative_path(self):
        self.assertTrue(run.is_expected_save(SAVE_ABS, SAVE_REL))
        self.assertFalse(run.is_expected_save(SAVE_ABS.replace("turn_10", "turn_2"), SAVE_REL))
        self.assertFalse(run.is_expected_save(None, SAVE_REL))

    def test_is_expected_save_accepts_backslash_paths(self):
        self.assertTrue(run.is_expected_save(SAVE_ABS.replace("/", "\\"), SAVE_REL))


class TimingsTests(unittest.TestCase):
    def setUp(self):
        self.t = run.find_timings(run.parse_entries(LOG))

    def test_anchors_are_found(self):
        self.assertEqual(self.t.queued, datetime(2026, 10, 5, 1, 24, 19, 495000))
        self.assertEqual(self.t.setup, datetime(2026, 10, 5, 1, 24, 42, 713000))
        self.assertEqual(self.t.playable, datetime(2026, 10, 5, 1, 25, 3, 108000))

    def test_durations(self):
        self.assertAlmostEqual(self.t.queue_to_setup, 23.218, places=3)
        self.assertAlmostEqual(self.t.queue_to_playable, 43.613, places=3)
        self.assertAlmostEqual(self.t.intro_to_setup, 22.632, places=3)
        self.assertAlmostEqual(self.t.lose_focus_to_setup, 20.713, places=3)

    def test_lose_focus_gap_is_none_without_the_event(self):
        text = LOG.replace("LoadingWorld - Handled LoseFocusScreenReport", "Other")
        t = run.find_timings(run.parse_entries(text))
        self.assertIsNone(t.lose_focus_to_setup)
        self.assertIsNotNone(t.intro_to_setup)

    def test_nothing_is_reported_before_the_queue(self):
        text = entry("2026-10-05 01:00:00,000", "LoadScreen, Handling Setup for GroundCombat") + LOG
        t = run.find_timings(run.parse_entries(text))
        self.assertEqual(t.setup, datetime(2026, 10, 5, 1, 24, 42, 713000))

    def test_intro_complete_after_setup_is_not_the_anchor(self):
        text = LOG + entry("2026-10-05 01:25:02,097", "Xenonauts.XenonautsLoadScreen: Intro Complete")
        t = run.find_timings(run.parse_entries(text))
        self.assertAlmostEqual(t.intro_to_setup, 22.632, places=3)

    def test_everything_is_none_for_an_empty_log(self):
        t = run.find_timings([])
        self.assertIsNone(t.queue_to_playable)
        self.assertIsNone(t.queue_to_setup)


class LoadTimingsTests(unittest.TestCase):
    SECOND_SAVE = SAVE_ABS.replace("auto/auto_groundcombat_turn_10_start-62", "user_x-4")

    def second_load(self) -> str:
        return (
            entry(
                "2026-10-05 01:30:00,000",
                f"GroundCombatWorld - Queued LoadGameCommand: LoadGameCommand (ReinitializeRNGSeed: True, SaveGameDescriptor: FileSystem::{self.SECOND_SAVE})",
            )
            + entry("2026-10-05 01:30:01,000", "Xenonauts.XenonautsLoadScreen: Intro Complete")
            + entry("2026-10-05 01:30:20,000", "LoadScreen, Handling Setup for GroundCombat")
            + entry("2026-10-05 01:30:30,000", "GCUI: BlockOnLocalPlayerTurn for 1")
        )

    def test_one_timings_per_queued_load(self):
        loads = run.find_load_timings(run.parse_entries(LOG + self.second_load()))
        self.assertEqual(len(loads), 2)

    def test_each_load_is_measured_against_its_own_anchors(self):
        loads = run.find_load_timings(run.parse_entries(LOG + self.second_load()))
        self.assertAlmostEqual(loads[0].queue_to_playable, 43.613, places=3)
        self.assertAlmostEqual(loads[1].intro_to_setup, 19.0, places=3)
        self.assertAlmostEqual(loads[1].queue_to_playable, 30.0, places=3)

    def test_last_queued_save_is_the_newest_load(self):
        entries = run.parse_entries(LOG + self.second_load())
        self.assertEqual(run.last_queued_save_path(entries), self.SECOND_SAVE)

    def test_last_queued_save_is_none_without_a_load(self):
        self.assertIsNone(run.last_queued_save_path([]))

    def test_no_loads_for_an_empty_log(self):
        self.assertEqual(run.find_load_timings([]), [])


class CountErrorsTests(unittest.TestCase):
    def test_counts_error_level_records(self):
        self.assertEqual(run.count_errors(LOG), 1)

    def test_ignores_error_text_inside_messages(self):
        self.assertEqual(run.count_errors(entry("2026-10-05 01:00:00,000", "the [ERROR] word")), 0)


class CountStateLossTests(unittest.TestCase):
    def test_counts_every_occurrence_including_the_wrapped_exception_report(self):
        text = entry(
            "2026-10-05 01:00:00,000",
            "[FSM state-loss:inaccessible] state entity deleted",
            level="ERROR",
        ) + entry(
            "2026-10-05 01:00:01,000",
            "Handled ExceptionReport: SyntheticException : [FSM state-loss:inaccessible] x",
        )
        self.assertEqual(run.count_state_loss(text, "state-loss"), 2)

    def test_zero_without_matches(self):
        self.assertEqual(run.count_state_loss(LOG, "state-loss"), 0)


class CloudSyncTests(unittest.TestCase):
    FAIL = '[2026-10-05 01:12:09] GameAction [AppID 538030, ActionID 19] : LaunchApp waiting for user response to SynchronizingCloud "syncfailed"\n'
    DONE = '[2026-10-05 01:23:43] GameAction [AppID 538030, ActionID 23] : LaunchApp changed task to Completed with ""\n'

    def test_pending_when_the_last_sync_failure_has_no_later_completed_launch(self):
        self.assertTrue(run.cloud_sync_blocked(self.DONE + self.FAIL))

    def test_not_pending_once_a_later_launch_completed(self):
        self.assertFalse(run.cloud_sync_blocked(self.FAIL + self.DONE))

    def test_not_pending_without_a_failure(self):
        self.assertFalse(run.cloud_sync_blocked(self.DONE))
        self.assertFalse(run.cloud_sync_blocked(""))


class ArchiveNameTests(unittest.TestCase):
    def test_leftover_logs_are_filed_under_the_run_name(self):
        self.assertEqual(run.leftover_archive_name("run7-auto", "pre-"), "pre-run7-auto")


class ConfigTests(unittest.TestCase):
    def test_precedence_is_process_env_then_env_file_then_default(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".env").write_text("LOAD_TIMEOUT=7\nLAUNCH_TIMEOUT=8\n")
            s = run.load_settings(Path(d), env={"LOAD_TIMEOUT": "5"})
        self.assertEqual(s.load_timeout, 5)
        self.assertEqual(s.launch_timeout, 8)
        self.assertEqual(s.quit_grace, 15)

    def test_naming_and_marker_settings_have_defaults_and_can_be_overridden(self):
        with tempfile.TemporaryDirectory() as d:
            s = run.load_settings(Path(d), env={})
            o = run.load_settings(
                Path(d),
                env={
                    "LEFTOVER_ARCHIVE_PREFIX": "old-",
                    "STATE_LOSS_PATTERN": "boom",
                    "PLAYABLE_MARKER": "ready",
                    "MOD_NAME": "other_mod",
                },
            )
        self.assertEqual(s.leftover_archive_prefix, "pre-")
        self.assertEqual(s.state_loss_pattern, "state-loss")
        self.assertEqual(s.playable_marker, "GCUI: BlockOnLocalPlayerTurn")
        self.assertEqual(s.menu_ready_marker, "XenonautsLoadScreen: Outro Complete")
        self.assertEqual(s.mod_name, "x2_load_profiler")
        self.assertEqual(s.game_process_pattern, "[X]enonauts2.exe")
        self.assertEqual(s.steam_process_pattern, "[s]team.exe")
        self.assertEqual(s.poll_interval, 0.5)
        self.assertEqual(o.leftover_archive_prefix, "old-")
        self.assertEqual(o.state_loss_pattern, "boom")
        self.assertEqual(o.playable_marker, "ready")
        self.assertEqual(o.mod_dir.name, "other_mod")

    def test_defaults_without_an_env_file(self):
        with tempfile.TemporaryDirectory() as d:
            s = run.load_settings(Path(d), env={})
        self.assertEqual(s.load_timeout, 120)
        self.assertEqual(s.save_rel, SAVE_REL)
        self.assertTrue(str(s.data_dir).endswith("Goldhawk Interactive/Xenonauts 2"))

    def test_env_file_in_the_calling_directory_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".env").write_text("LOAD_TIMEOUT=7\nSAVE_REL=Saves/x.json\n")
            s = run.load_settings(Path(d), env={})
        self.assertEqual(s.load_timeout, 7)
        self.assertEqual(s.save_rel, "Saves/x.json")

    def test_process_environment_is_used_when_there_is_no_env_file(self):
        with tempfile.TemporaryDirectory() as d:
            s = run.load_settings(Path(d), env={"LAUNCH_TIMEOUT": "9"})
        self.assertEqual(s.launch_timeout, 9)

    def test_bottle_setting_moves_the_derived_paths(self):
        with tempfile.TemporaryDirectory() as d:
            s = run.load_settings(Path(d), env={"BOTTLE": "/b"})
        self.assertEqual(s.game_dir, Path("/b/Program Files (x86)/Steam/steamapps/common/Xenonauts2"))
        self.assertEqual(
            s.data_dir,
            Path("/b/users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2"),
        )

    def test_menu_points_default_to_the_spike_coordinates(self):
        with tempfile.TemporaryDirectory() as d:
            s = run.load_settings(Path(d), env={})
        self.assertEqual(s.menu_load_game, (1331, 1302))
        self.assertEqual(s.menu_save_row, (947, 426))
        self.assertEqual(s.menu_load_save, (960, 1112))


class ParsePointTests(unittest.TestCase):
    def test_parses_x_comma_y(self):
        self.assertEqual(run.parse_point("1331,1302"), (1331, 1302))
        self.assertEqual(run.parse_point(" 5 , 6 "), (5, 6))

    def test_rejects_bad_input(self):
        for bad in ["", "1", "1,2,3", "a,b"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    run.parse_point(bad)


class AutoLoadTextTests(unittest.TestCase):
    def test_names_the_save_in_the_mod_file_format(self):
        self.assertEqual(run.auto_load_text(SAVE_ABS), f"save={SAVE_ABS}\n")


class RunNameTests(unittest.TestCase):
    def test_accepts_simple_names(self):
        for ok in ["run7", "run7-auto", "mod_off.2"]:
            with self.subTest(ok=ok):
                run.validate_run_name(ok)

    def test_rejects_names_that_escape_the_logs_folder(self):
        for bad in ["", ".", "..", "a/b", "../x", "a b"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    run.validate_run_name(bad)


MARKERS = (
    f"2026-10-05 01:24:19,495 Queued LoadGameCommand:: LoadGameCommand (ReinitializeRNGSeed: True, SaveGameDescriptor: FD[UNRESOLVED]>FileSystem::{SAVE_ABS})\n"
    "2026-10-05 01:24:20,081 XenonautsLoadScreen: Intro Complete\n"
    "2026-10-05 01:24:42,713 LoadScreen, Handling Setup for GroundCombat\n"
    "2026-10-05 01:25:03,108 GCUI: BlockOnLocalPlayerTurn for 634 Player\n"
)


class ParseMarkersTests(unittest.TestCase):
    def test_each_line_is_a_timestamp_then_a_message(self):
        entries = run.parse_markers(MARKERS)
        self.assertEqual(len(entries), 4)
        self.assertEqual(entries[1].ts, datetime(2026, 10, 5, 1, 24, 20, 81000))
        self.assertEqual(entries[1].message, "XenonautsLoadScreen: Intro Complete")

    def test_blank_and_malformed_lines_are_skipped(self):
        text = "\nnot a marker\n2026-10-05 01:24:20,081 ok\n"
        self.assertEqual([e.message for e in run.parse_markers(text)], ["ok"])

    def test_marker_entries_feed_the_same_timing_anchors(self):
        t = run.find_timings(run.parse_markers(MARKERS))
        self.assertAlmostEqual(t.intro_to_setup, 22.632, places=3)
        self.assertAlmostEqual(t.queue_to_playable, 43.613, places=3)
        self.assertIsNone(t.lose_focus_to_setup)

    def test_marker_queue_line_yields_the_save_path(self):
        self.assertEqual(run.queued_save_path(run.parse_markers(MARKERS)), SAVE_ABS)


class TimingEntriesTests(unittest.TestCase):
    def test_markers_win_when_present(self):
        entries = run.timing_entries(LOG, MARKERS)
        self.assertEqual(len(entries), 4)

    def test_log_is_used_when_the_markers_file_is_empty_or_missing(self):
        self.assertEqual(len(run.timing_entries(LOG, "")), len(run.parse_entries(LOG)))


class MarkersFileTests(unittest.TestCase):
    def test_markers_file_lives_in_the_timing_mod_folder(self):
        with tempfile.TemporaryDirectory() as d:
            s = run.load_settings(Path(d), env={"DATA_DIR": "/data"})
        self.assertEqual(s.markers_file, Path("/data/Mods/x2_load_timing/markers.txt"))

    def test_timing_mod_name_can_be_overridden(self):
        with tempfile.TemporaryDirectory() as d:
            s = run.load_settings(Path(d), env={"DATA_DIR": "/data", "TIMING_MOD_NAME": "t"})
        self.assertEqual(s.markers_file, Path("/data/Mods/t/markers.txt"))


class SnapshotTests(unittest.TestCase):
    def test_hash_files_records_missing_files_as_none(self):
        with tempfile.TemporaryDirectory() as d:
            present = Path(d) / "a.json"
            present.write_text("{}")
            hashes = run.hash_files([present, Path(d) / "missing.json"])
        self.assertEqual(len(hashes[present]), 64)
        self.assertIsNone(hashes[Path(d) / "missing.json"])

    def test_changed_files_reports_modified_created_and_removed(self):
        a, b, c, d = (Path(n) for n in "abcd")
        before = {a: "1", b: "2", c: None, d: "4"}
        after = {a: "1", b: "x", c: "3", d: None}
        self.assertEqual(run.changed_files(before, after), [b, c, d])

    def test_changed_files_is_empty_when_nothing_changed(self):
        self.assertEqual(run.changed_files({Path("a"): "1"}, {Path("a"): "1"}), [])


if __name__ == "__main__":
    unittest.main()

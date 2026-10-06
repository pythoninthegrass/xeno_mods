#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["python-decouple>=3.8"]
# ///

"""Unit tests for run.py: log parsing, timing anchors, config loading and snapshot helpers.

Hermetic: no game, no Steam, no desktop automation.
"""

import getpass
import sys
import tempfile
import time
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
            s = run.load_settings(Path(d), env={}, platform="darwin")
            o = run.load_settings(
                Path(d),
                platform="darwin",
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
            s = run.load_settings(Path(d), env={"BOTTLE": "/b"}, platform="darwin")
        self.assertEqual(s.game_dir, Path("/b/Program Files (x86)/Steam/steamapps/common/Xenonauts2"))
        self.assertEqual(
            s.data_dir,
            Path("/b/users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2"),
        )

    def test_macos_menu_points_default_to_the_2560x1440_coordinates(self):
        with tempfile.TemporaryDirectory() as d:
            s = run.load_settings(Path(d), env={}, platform="darwin")
        self.assertEqual(s.menu_load_game, (1331, 1302))
        self.assertEqual(s.menu_save_row, (947, 426))
        self.assertEqual(s.menu_load_save, (960, 1112))
        self.assertEqual(s.game_menu_button, (54, 54))
        self.assertEqual(s.game_menu_load_game, (1280, 760))
        self.assertEqual(s.game_menu_save_row, (896, 426))

    def test_linux_menu_points_default_to_the_1920x1080_coordinates(self):
        for build in ("steam", "gog"):
            s = settings("linux", {"BUILD": build})
            self.assertEqual(s.menu_load_game, (984, 976))
            self.assertEqual(s.menu_save_row, (700, 402))
            self.assertEqual(s.menu_load_save, (720, 834))
            self.assertEqual(s.game_menu_button, (40, 40))
            self.assertEqual(s.game_menu_load_game, (960, 570))
            self.assertEqual(s.game_menu_save_row, (700, 402))

    def test_menu_points_can_be_overridden(self):
        self.assertEqual(settings("linux", {"MENU_LOAD_GAME": "1,2"}).menu_load_game, (1, 2))


def settings(platform: str, env: dict[str, str] | None = None) -> "run.Settings":
    """Settings as loaded on a named platform, with no .env file in the way."""
    with tempfile.TemporaryDirectory() as d:
        return run.load_settings(Path(d), env=env or {}, platform=platform)


class PlatformDefaultsTests(unittest.TestCase):
    """Defaults are pinned per platform so the suite means the same thing on either machine."""

    def test_wine_user_defaults_to_the_prefix_owner_of_each_platform(self):
        self.assertEqual(settings("darwin").wine_user, "crossover")
        self.assertEqual(settings("linux").wine_user, "steamuser")

    def test_wine_user_names_the_data_dir_and_the_save_path(self):
        mac = settings("darwin")
        self.assertIn("users/crossover/AppData", str(mac.data_dir))
        self.assertTrue(mac.save_abs.startswith("C:/users/crossover/AppData"))

    def test_wine_user_can_be_overridden(self):
        s = settings("linux", {"WINE_USER": "bob"})
        self.assertIn("users/bob/AppData", str(s.data_dir))
        self.assertTrue(s.save_abs.startswith("C:/users/bob/AppData"))

    def test_steam_console_log_is_inside_the_bottle_on_macos(self):
        s = settings("darwin", {"BOTTLE": "/b"})
        self.assertEqual(s.steam_console_log, Path("/b/Program Files (x86)/Steam/logs/console_log.txt"))

    def test_steam_console_log_is_outside_the_prefix_on_linux(self):
        s = settings("linux", {"BOTTLE": "/b"})
        self.assertEqual(s.steam_console_log, Path("/media/steam/logs/console-linux.txt"))

    def test_steam_console_log_can_be_overridden(self):
        s = settings("linux", {"STEAM_CONSOLE_LOG": "/tmp/c.txt"})
        self.assertEqual(s.steam_console_log, Path("/tmp/c.txt"))

    def test_bottle_defaults_to_the_crossover_bottle_or_the_proton_prefix(self):
        self.assertTrue(str(settings("darwin").bottle).endswith("CrossOver/Bottles/Steam/drive_c"))
        self.assertEqual(settings("linux").bottle, Path("/media/steam/steamapps/compatdata/538030/pfx/drive_c"))

    def test_game_dir_is_inside_the_bottle_on_macos_and_outside_the_prefix_on_linux(self):
        self.assertEqual(
            settings("darwin", {"BOTTLE": "/b"}).game_dir,
            Path("/b/Program Files (x86)/Steam/steamapps/common/Xenonauts2"),
        )
        self.assertEqual(
            settings("linux", {"BOTTLE": "/b"}).game_dir,
            Path("/media/steam/steamapps/common/Xenonauts2"),
        )

    def test_bottle_token_expands_in_a_configured_path(self):
        s = settings("linux", {"BOTTLE": "/b", "GAME_DIR": "{bottle}/game"})
        self.assertEqual(s.game_dir, Path("/b/game"))

    def test_steam_process_pattern_matches_the_client_of_each_platform(self):
        self.assertEqual(settings("darwin").steam_process_pattern, "[s]team.exe")
        self.assertEqual(settings("linux").steam_process_pattern, "[s]teamwebhelper")

    def test_launcher_app_is_a_macos_only_setting(self):
        self.assertTrue(str(settings("darwin").launcher_app).endswith("Xenonauts 2.app"))
        self.assertIsNone(settings("linux").launcher_app)

    def test_launch_cmd_defaults_to_the_launcher_of_each_platform(self):
        self.assertEqual(settings("darwin").launch_cmd, ("open", "{app}"))
        self.assertEqual(settings("linux").launch_cmd, FLATPAK_STEAM_LAUNCH)

    def test_click_cmd_defaults_to_the_clicker_of_each_platform(self):
        self.assertEqual(settings("darwin").click_cmd[:4], ("osascript", "-l", "JavaScript", "-e"))
        self.assertEqual(settings("linux").click_cmd, ("xdotool", "mousemove", "{x}", "{y}", "click", "1"))


class CommandTemplateTests(unittest.TestCase):
    def test_substitute_replaces_tokens_and_leaves_other_braces_alone(self):
        argv = ["a", "{x}", "function f() { g({y}); }"]
        self.assertEqual(
            run.substitute(argv, {"{x}": "1", "{y}": "2"}),
            ["a", "1", "function f() { g(2); }"],
        )

    def test_launch_command_fills_in_the_app_path(self):
        s = settings("darwin", {"LAUNCHER_APP": "/A/Xenonauts 2.app"})
        self.assertEqual(run.launch_command(s), ["open", "/A/Xenonauts 2.app"])

    def test_launch_command_on_linux_goes_straight_to_the_steam_app_id(self):
        self.assertEqual(run.launch_command(settings("linux")), list(FLATPAK_STEAM_LAUNCH))

    def test_click_command_fills_in_the_coordinates(self):
        self.assertEqual(
            run.click_command(settings("linux"), (7, 9)),
            ["xdotool", "mousemove", "7", "9", "click", "1"],
        )

    def test_click_command_keeps_the_jxa_body_intact(self):
        argv = run.click_command(settings("darwin"), (7, 9))
        self.assertEqual(argv[:4], ["osascript", "-l", "JavaScript", "-e"])
        self.assertIn("click(7, 9);", argv[-1])
        self.assertIn("function post(type, x, y) {", argv[-1])

    def test_a_platform_without_a_launcher_app_passes_the_launcher_check(self):
        self.assertIsNone(run.launcher_app_problem(settings("linux")))

    def test_a_configured_launcher_app_must_exist(self):
        problem = run.launcher_app_problem(settings("darwin", {"LAUNCHER_APP": "/nope/Xenonauts 2.app"}))
        self.assertIn("/nope/Xenonauts 2.app", problem)

    def test_launch_cmd_override_is_split_like_a_shell_command(self):
        s = settings("linux", {"LAUNCH_CMD": "flatpak run com.valvesoftware.Steam 'steam://rungameid/1'"})
        self.assertEqual(run.launch_command(s), ["flatpak", "run", "com.valvesoftware.Steam", "steam://rungameid/1"])


FLATPAK_STEAM_LAUNCH = ("flatpak", "run", "com.valvesoftware.Steam", "steam://rungameid/538030")
GOG_WINEPREFIX = "WINEPREFIX=/run/user/1000/doc/5cf27610/gog/Xenonauts 2/prefix"


class BuildTests(unittest.TestCase):
    def test_build_defaults_to_steam(self):
        self.assertEqual(settings("linux").build, "steam")
        self.assertEqual(settings("darwin").build, "steam")

    def test_an_unknown_build_is_rejected(self):
        with self.assertRaises(ValueError):
            settings("linux", {"BUILD": "epic"})

    def test_the_gog_build_is_linux_only(self):
        with self.assertRaises(ValueError):
            settings("darwin", {"BUILD": "gog"})

    def test_steam_defaults_are_the_same_with_the_build_set_explicitly(self):
        for platform in ("linux", "darwin"):
            self.assertEqual(settings(platform, {"BUILD": "steam"}), settings(platform))

    def test_gog_defaults_point_at_the_minigalaxy_install(self):
        s = settings("linux", {"BUILD": "gog"})
        self.assertEqual(s.bottle, Path("/media/gog/Xenonauts 2/prefix/drive_c"))
        self.assertEqual(s.game_dir, Path("/media/gog/Xenonauts 2"))
        self.assertEqual(s.wine_user, getpass.getuser())
        self.assertEqual(
            s.data_dir,
            Path(
                f"/media/gog/Xenonauts 2/prefix/drive_c/users/{getpass.getuser()}/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2"
            ),
        )

    def test_gog_save_path_uses_the_login_name(self):
        s = settings("linux", {"BUILD": "gog"})
        self.assertTrue(s.save_abs.startswith(f"C:/users/{getpass.getuser()}/AppData/"))

    def test_gog_has_no_steam_client_settings(self):
        s = settings("linux", {"BUILD": "gog"})
        self.assertIsNone(s.steam_console_log)
        self.assertEqual(s.steam_process_pattern, "")

    def test_gog_launches_through_the_minigalaxy_wine(self):
        argv = run.launch_command(settings("linux", {"BUILD": "gog"}))
        self.assertEqual(argv[:4], ["flatpak", "run", "--command=env", "io.github.sharkwouter.Minigalaxy"])
        self.assertIn(GOG_WINEPREFIX, argv)
        self.assertEqual(argv[-5:], ["/app/bin/wine", "start", "/d", "c:\\game", "c:\\game\\Xenonauts2.exe"])

    def test_gog_values_can_be_overridden(self):
        s = settings("linux", {"BUILD": "gog", "GOG_WINE_USER": "bob", "GOG_GAME_DIR": "/g", "GOG_LAUNCH_CMD": "true"})
        self.assertEqual(s.wine_user, "bob")
        self.assertEqual(s.game_dir, Path("/g"))
        self.assertEqual(run.launch_command(s), ["true"])

    def test_steam_overrides_do_not_leak_into_the_gog_build(self):
        s = settings(
            "linux",
            {"BUILD": "gog", "BOTTLE": "/steam", "GAME_DIR": "/steam/g", "LAUNCH_CMD": "steam x", "WINE_USER": "steamuser"},
        )
        self.assertEqual(s.bottle, Path("/media/gog/Xenonauts 2/prefix/drive_c"))
        self.assertEqual(s.game_dir, Path("/media/gog/Xenonauts 2"))
        self.assertEqual(run.launch_command(s)[0], "flatpak")
        self.assertEqual(s.wine_user, getpass.getuser())

    def test_gog_overrides_do_not_leak_into_the_steam_build(self):
        s = settings("linux", {"GOG_BOTTLE": "/gog", "GOG_LAUNCH_CMD": "true"})
        self.assertEqual(run.launch_command(s), list(FLATPAK_STEAM_LAUNCH))

    def test_gog_shares_the_generic_settings(self):
        s = settings("linux", {"BUILD": "gog", "LOAD_TIMEOUT": "9", "MENU_LOAD_GAME": "1,2"})
        self.assertEqual((s.load_timeout, s.menu_load_game), (9, (1, 2)))

    def test_gog_preflight_needs_no_steam(self):
        s = settings("linux", {"BUILD": "gog", "GOG_STEAM_PROCESS_PATTERN": "[n]o-such-process-xyz"})
        self.assertFalse(run.needs_steam(s))
        run.preflight(s)

    def test_steam_preflight_still_needs_steam(self):
        self.assertTrue(run.needs_steam(settings("linux")))
        self.assertTrue(run.needs_steam(settings("darwin")))


class StartGameTests(unittest.TestCase):
    def quick(self, launch_cmd: str) -> "run.Settings":
        return settings(
            "linux",
            {
                "LAUNCH_CMD": launch_cmd,
                "GAME_PROCESS_PATTERN": "[n]o-such-game-process-xyz",
                "LAUNCH_TIMEOUT": "1",
                "POLL_INTERVAL": "0.1",
            },
        )

    def test_a_game_that_never_appears_fails_within_the_launch_timeout(self):
        started = time.monotonic()
        with self.assertRaisesRegex(run.RunError, "did not start within 1 s"):
            run.start_game(self.quick("true"))
        self.assertLess(time.monotonic() - started, 5)

    def test_a_failing_launch_command_is_a_clear_error(self):
        with self.assertRaisesRegex(run.RunError, "launch command failed"):
            run.start_game(self.quick("false"))

    def test_a_launch_command_that_hangs_is_cut_off_at_the_timeout(self):
        started = time.monotonic()
        with self.assertRaisesRegex(run.RunError, "launch command did not return within 1 s"):
            run.start_game(self.quick("sleep 30"))
        self.assertLess(time.monotonic() - started, 5)

    def test_a_missing_launch_binary_is_a_clear_error(self):
        with self.assertRaisesRegex(run.RunError, "launch command failed"):
            run.start_game(self.quick("/nonexistent/launcher"))


class PointerTests(unittest.TestCase):
    def test_gog_clicks_with_ydotool_for_the_wayland_session(self):
        argv = run.click_command(settings("linux", {"BUILD": "gog"}), (7, 9))
        self.assertEqual(argv[:2], ["sh", "-c"])
        self.assertIn("ydotool", argv[2])
        self.assertIn("$((7 / 2))", argv[2])
        self.assertIn("$((9 / 2))", argv[2])
        self.assertIn("ydotool click", argv[2])

    def test_gog_parks_the_pointer_off_the_hud_after_a_click(self):
        s = settings("linux", {"BUILD": "gog"})
        argv = run.park_command(s)
        self.assertIn("ydotool", argv[-1])
        self.assertIn(f"$(({s.park_point[0]} / 2))", argv[-1])
        self.assertNotIn("ydotool click", argv[-1])

    def test_steam_clicks_are_unchanged_and_do_not_park(self):
        self.assertEqual(settings("linux").click_cmd, ("xdotool", "mousemove", "{x}", "{y}", "click", "1"))
        self.assertIsNone(run.park_command(settings("linux")))
        self.assertIsNone(run.park_command(settings("darwin")))

    def test_park_point_and_move_command_can_be_overridden(self):
        s = settings("linux", {"PARK_POINT": "5,6", "MOVE_CMD": "mv {x} {y}"})
        self.assertEqual(s.park_point, (5, 6))
        self.assertEqual(run.park_command(s), ["mv", "5", "6"])

    def test_menu_mode_raises_the_game_only_on_macos(self):
        self.assertTrue(run.needs_raise(settings("darwin")))
        self.assertFalse(run.needs_raise(settings("linux")))


class ParsePointTests(unittest.TestCase):
    def test_parses_x_comma_y(self):
        self.assertEqual(run.parse_point("1331,1302"), (1331, 1302))
        self.assertEqual(run.parse_point(" 5 , 6 "), (5, 6))

    def test_rejects_bad_input(self):
        for bad in ["", "1", "1,2,3", "a,b"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
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
            with self.subTest(bad=bad), self.assertRaises(ValueError):
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

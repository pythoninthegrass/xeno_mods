#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""Unit tests for sample_threads.py: /proc stat parsing, per-interval CPU deltas, row format and per-name summaries."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sample_threads as st  # noqa: E402


def stat_line(tid, comm, state, utime, stime):
    # fields after the command name: state, ppid .. cmajflt (10 fields), utime, stime, then filler
    return f"{tid} ({comm}) {state} 1 1 1 0 -1 4194560 100 0 0 0 {utime} {stime} 0 0 20 0 5 0 12345 1000 200"


class ParseStatTests(unittest.TestCase):
    def test_reads_name_state_and_cpu_ticks(self):
        parsed = st.parse_stat(stat_line(42, "UnityMain", "R", 700, 30))
        self.assertEqual(parsed, st.ThreadStat("UnityMain", "R", 730))

    def test_name_may_contain_spaces_and_parentheses(self):
        parsed = st.parse_stat(stat_line(7, "Loading (Async) x", "D", 5, 6))
        self.assertEqual(parsed, st.ThreadStat("Loading (Async) x", "D", 11))


class CpuDeltaTests(unittest.TestCase):
    def test_delta_against_previous_sample(self):
        previous = {1: 100, 2: 50}
        current = {1: st.ThreadStat("main", "R", 130), 2: st.ThreadStat("io", "S", 50)}
        self.assertEqual(st.cpu_deltas(previous, current), {1: 30, 2: 0})

    def test_new_thread_counts_all_its_ticks(self):
        current = {9: st.ThreadStat("worker", "R", 12)}
        self.assertEqual(st.cpu_deltas({}, current), {9: 12})

    def test_exited_thread_is_dropped(self):
        current = {1: st.ThreadStat("main", "R", 10)}
        self.assertEqual(st.cpu_deltas({1: 5, 2: 99}, current), {1: 5})


class RowTests(unittest.TestCase):
    def test_round_trip(self):
        row = st.Row(12.5, 31, "Loading.Preload", "R", 4)
        self.assertEqual(st.parse_row(st.format_row(row)), row)

    def test_tabs_in_names_do_not_break_the_row(self):
        row = st.Row(1.0, 2, "a\tb", "S", 1)
        self.assertEqual(st.parse_row(st.format_row(row)).name, "a b")

    def test_only_active_threads_are_worth_recording(self):
        self.assertTrue(st.is_active("S", 1))
        self.assertTrue(st.is_active("R", 0))
        self.assertTrue(st.is_active("D", 0))
        self.assertFalse(st.is_active("S", 0))


class PickGamePidTests(unittest.TestCase):
    def test_prefers_the_process_with_the_most_threads(self):
        self.assertEqual(st.pick_game_pid([(100, 2), (200, 74), (300, 1)]), 200)

    def test_no_candidates(self):
        self.assertIsNone(st.pick_game_pid([]))


class DefaultPatternTests(unittest.TestCase):
    def test_matches_the_wine_command_line_only(self):
        self.assertRegex(r"S:\steamapps\common\Xenonauts2\Xenonauts2.exe", st.DEFAULT_PATTERN)
        self.assertNotRegex(
            "c:\\windows\\system32\\steam.exe /media/steam/steamapps/common/Xenonauts2/Xenonauts2.exe", st.DEFAULT_PATTERN
        )
        self.assertNotRegex("S:\\steamapps\\common\\Xenonauts2XXexe", st.DEFAULT_PATTERN)


class SummaryTests(unittest.TestCase):
    rows = [
        st.Row(0.1, 1, "main", "R", 8),
        st.Row(0.1, 2, "worker", "R", 5),
        st.Row(0.1, 3, "worker", "D", 0),
        st.Row(1.2, 1, "main", "R", 10),
        st.Row(1.2, 2, "worker", "R", 2),
    ]

    def test_groups_cpu_by_name_and_bucket(self):
        summary = st.summarize(self.rows, bucket_seconds=1.0)
        self.assertEqual(summary[0]["main"].cpu_seconds, 0.08)
        self.assertEqual(summary[0]["worker"].cpu_seconds, 0.05)
        self.assertEqual(summary[1]["main"].cpu_seconds, 0.10)

    def test_counts_threads_and_blocked_samples(self):
        worker = st.summarize(self.rows, bucket_seconds=1.0)[0]["worker"]
        self.assertEqual(worker.threads, 2)
        self.assertEqual(worker.disk_wait_samples, 1)

    def test_share_of_one_core_is_cpu_over_bucket_length(self):
        main = st.summarize(self.rows, bucket_seconds=2.0)[0]["main"]
        self.assertAlmostEqual(main.cpu_seconds / 2.0, 0.09)

    def test_empty_input(self):
        self.assertEqual(st.summarize([], bucket_seconds=1.0), {})


if __name__ == "__main__":
    unittest.main()

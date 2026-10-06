#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""Unit tests for analyze_bundles.py: record parsing, windowing, classification and per-class summaries."""

import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyze_bundles as ab  # noqa: E402

P = "Assets/Assets/xenonauts"


def load(seq, done, queue, ms, kind, path, bundle="b"):
    return f"L\t{seq}\t2026-10-05 18:00:{done}\t{queue}\t{ms}\t{kind}\t{path}\t{bundle}\txenonauts\t-"


def unload(at, kind, path):
    return f"U\t2026-10-05 18:00:{at}\t{kind}\t{path}"


TSV = "\n".join(
    [
        load(1, "10.000", "5.0", "100.0", "Texture2D", f"{P}/texture/strategy/a.png"),
        unload("11.000", "Texture2D", f"{P}/texture/strategy/a.png"),
        load(2, "12.000", "0.0", "50.0", "Texture2D", f"{P}/texture/strategy/a.png"),
        load(3, "13.000", "1.0", "20.0", "GameObject", f"{P}/prefab/groundcombat/x.prefab"),
        load(4, "14.000", "1.0", "20.0", "GameObject", f"{P}/prefab/groundcombat/x.prefab"),
    ]
)


class ParseTests(unittest.TestCase):
    def test_loads_and_unloads_are_separated_and_timed(self):
        loads, unloads = ab.parse_tsv(TSV)
        self.assertEqual(len(loads), 4)
        self.assertEqual(len(unloads), 1)
        first = loads[0]
        self.assertEqual(first.done, datetime(2026, 10, 5, 18, 0, 10))
        self.assertAlmostEqual((first.done - first.start).total_seconds(), 0.1)
        self.assertAlmostEqual((first.start - first.request).total_seconds(), 0.005)

    def test_blank_and_unknown_lines_are_skipped(self):
        loads, unloads = ab.parse_tsv("\nX\tjunk\n")
        self.assertEqual((loads, unloads), ([], []))


class ClassifyTests(unittest.TestCase):
    def test_kind_and_scope_come_from_the_path(self):
        self.assertEqual(ab.classify(f"{P}/template/strategy/a.json"), ("template", "strategy"))
        self.assertEqual(ab.classify(f"{P}/audio/groundcombat/a.wav"), ("audio", "groundcombat"))
        self.assertEqual(ab.classify(f"{P}/ui/common/components/b.prefab"), ("ui", "common"))

    def test_anything_else_is_other(self):
        self.assertEqual(ab.classify("Saves/x.json"), ("other", "other"))
        self.assertEqual(ab.classify(f"{P}/texture/weird/a.png"), ("texture", "other"))


class WindowTests(unittest.TestCase):
    def test_records_are_assigned_by_boundary_times(self):
        loads, unloads = ab.parse_tsv(TSV)
        boundaries = [datetime(2026, 10, 5, 18, 0, 12, 500000)]
        windows = ab.split_windows(loads, unloads, boundaries)
        self.assertEqual([len(w.loads) for w in windows], [2, 2])
        self.assertEqual(len(windows[0].unloads), 1)


class FlagTests(unittest.TestCase):
    def setUp(self):
        loads, unloads = ab.parse_tsv(TSV)
        self.window = ab.Window(loads, unloads)

    def test_duplicate_paths_are_the_ones_loaded_more_than_once(self):
        self.assertEqual(
            ab.duplicate_paths(self.window), {f"{P}/prefab/groundcombat/x.prefab": 2, f"{P}/texture/strategy/a.png": 2}
        )

    def test_released_then_reloaded_needs_an_unload_before_the_load_request(self):
        flagged = ab.reloaded_after_release(self.window)
        self.assertEqual([load.seq for load in flagged], [2])

    def test_loaded_then_released_needs_an_unload_after_the_load_finished(self):
        flagged = ab.released_after_load(self.window)
        self.assertEqual([load.seq for load in flagged], [1])

    def test_reloaded_names_are_sorted_and_unique(self):
        window = ab.Window(self.window.loads + self.window.loads, self.window.unloads)
        self.assertEqual(ab.reloaded_names(window), [f"{P}/texture/strategy/a.png"])


class SummaryTests(unittest.TestCase):
    def test_counts_and_estimated_seconds_split_the_active_span_by_load_share(self):
        loads, unloads = ab.parse_tsv(TSV)
        rows = ab.summarize(ab.Window(loads, unloads))
        by_class = {r.key: r for r in rows}
        self.assertEqual(by_class[("texture", "strategy")].count, 2)
        self.assertEqual(by_class[("prefab", "groundcombat")].count, 2)
        total_span = (loads[-1].done - loads[0].request).total_seconds()
        self.assertAlmostEqual(sum(r.est_seconds for r in rows), total_span)
        self.assertAlmostEqual(by_class[("texture", "strategy")].est_seconds, total_span / 2)

    def test_latency_sum_is_the_summed_start_to_done_time(self):
        loads, unloads = ab.parse_tsv(TSV)
        rows = {r.key: r for r in ab.summarize(ab.Window(loads, unloads))}
        self.assertAlmostEqual(rows[("texture", "strategy")].latency_seconds, 0.15)


if __name__ == "__main__":
    unittest.main()

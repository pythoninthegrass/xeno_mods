#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""
Usage:
    sample_threads.py sample <out.tsv> [--interval SECONDS] [--pattern REGEX] [--wait SECONDS]
    sample_threads.py summarize <out.tsv> [--bucket SECONDS]

Args:
    out.tsv: per-thread CPU samples; the first line is a comment holding the wall-clock start time
    --interval: seconds between samples (default 0.1)
    --pattern: pgrep -f pattern of the game process (default matches the Wine-side S:\\...\\Xenonauts2.exe command line)
    --wait: seconds to wait for the game process to appear (default 180)
    --bucket: summary window in seconds (default 1.0)

Note:
    Linux only. Samples /proc/<pid>/task/*/stat of the game process and records, per thread and interval, the CPU ticks
    used and the scheduler state, so a load can be split by thread (main, loading, worker) without touching the game.
    Start it before scripts/run.py launches the game; it waits for the process and stops when it exits.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PureWindowsPath

CLOCK_TICKS_PER_SECOND = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
DEFAULT_INTERVAL = 0.1
# The game process command line is the Wine-side Windows path; the launcher wrappers only mention the Unix path
DEFAULT_PATTERN = "^" + re.escape(str(PureWindowsPath("S:/steamapps/common/Xenonauts2/Xenonauts2.exe")))
DEFAULT_WAIT = 180.0
DISK_WAIT_STATE = "D"
RUNNING_STATE = "R"


@dataclass(frozen=True)
class ThreadStat:
    name: str
    state: str
    ticks: int


@dataclass(frozen=True)
class Row:
    t_s: float
    tid: int
    name: str
    state: str
    ticks: int


@dataclass
class Summary:
    ticks: int = 0
    tids: set[int] = field(default_factory=set)
    running_samples: int = 0
    disk_wait_samples: int = 0

    @property
    def cpu_seconds(self) -> float:
        return self.ticks / CLOCK_TICKS_PER_SECOND

    @property
    def threads(self) -> int:
        return len(self.tids)


def parse_stat(text: str) -> ThreadStat:
    # The command name sits in parentheses and may itself contain spaces and parentheses, so split on the last one
    name_start = text.index("(") + 1
    name_end = text.rindex(")")
    rest = text[name_end + 1 :].split()
    return ThreadStat(text[name_start:name_end], rest[0], int(rest[11]) + int(rest[12]))


def cpu_deltas(previous: dict[int, int], current: dict[int, ThreadStat]) -> dict[int, int]:
    return {tid: stat.ticks - previous.get(tid, 0) for tid, stat in current.items()}


def is_active(state: str, ticks: int) -> bool:
    return ticks > 0 or state in (RUNNING_STATE, DISK_WAIT_STATE)


def format_row(row: Row) -> str:
    return "\t".join((f"{row.t_s:.3f}", str(row.tid), row.name.replace("\t", " "), row.state, str(row.ticks)))


def parse_row(line: str) -> Row:
    t_s, tid, name, state, ticks = line.rstrip("\n").split("\t")
    return Row(float(t_s), int(tid), name, state, int(ticks))


def summarize(rows: list[Row], bucket_seconds: float) -> dict[int, dict[str, Summary]]:
    buckets: dict[int, dict[str, Summary]] = defaultdict(lambda: defaultdict(Summary))
    for row in rows:
        summary = buckets[int(row.t_s // bucket_seconds)][row.name]
        summary.ticks += row.ticks
        summary.tids.add(row.tid)
        summary.running_samples += row.state == RUNNING_STATE
        summary.disk_wait_samples += row.state == DISK_WAIT_STATE
    return {index: dict(names) for index, names in buckets.items()}


def pick_game_pid(candidates: list[tuple[int, int]]) -> int | None:
    # Several processes match the pattern (launcher wrappers, the game itself); the game has by far the most threads
    return max(candidates, key=lambda pid_threads: pid_threads[1])[0] if candidates else None


def find_game_pid(pattern: str) -> int | None:
    result = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    candidates = []
    for line in result.stdout.split():
        pid = int(line)
        try:
            candidates.append((pid, len(os.listdir(f"/proc/{pid}/task"))))
        except OSError:
            continue
    return pick_game_pid(candidates)


def read_threads(pid: int) -> dict[int, ThreadStat]:
    threads = {}
    try:
        tids = os.listdir(f"/proc/{pid}/task")
    except OSError:
        return threads
    for tid in tids:
        try:
            threads[int(tid)] = parse_stat(Path(f"/proc/{pid}/task/{tid}/stat").read_text())
        except (OSError, ValueError):
            continue
    return threads


def sample(out: Path, interval: float, pattern: str, wait: float) -> int:
    deadline = time.monotonic() + wait
    pid = find_game_pid(pattern)
    while pid is None:
        if time.monotonic() > deadline:
            print(f"no process matching {pattern} within {wait:.0f} s", file=sys.stderr)
            return 1
        time.sleep(0.2)
        pid = find_game_pid(pattern)

    started = time.monotonic()
    previous: dict[int, int] = {}
    with out.open("w") as handle:
        handle.write(f"# start {datetime.now():%Y-%m-%d %H:%M:%S.%f} pid {pid} interval {interval}\n")
        while True:
            threads = read_threads(pid)
            if not threads:
                break
            now = time.monotonic() - started
            for tid, ticks in cpu_deltas(previous, threads).items():
                if is_active(threads[tid].state, ticks):
                    handle.write(format_row(Row(now, tid, threads[tid].name, threads[tid].state, ticks)) + "\n")
            previous = {tid: stat.ticks for tid, stat in threads.items()}
            time.sleep(interval)
    return 0


def print_summary(path: Path, bucket_seconds: float) -> None:
    lines = path.read_text().splitlines()
    print(lines[0] if lines and lines[0].startswith("#") else "# start unknown")
    rows = [parse_row(line) for line in lines if line and not line.startswith("#")]
    print("second\tname\tthreads\tcpu_s\tcores\trunning_samples\tdisk_wait_samples")
    for index, names in sorted(summarize(rows, bucket_seconds).items()):
        for name, summary in sorted(names.items(), key=lambda item: -item[1].ticks):
            cores = summary.cpu_seconds / bucket_seconds
            print(
                f"{index * bucket_seconds:.0f}\t{name}\t{summary.threads}\t{summary.cpu_seconds:.2f}\t{cores:.2f}"
                f"\t{summary.running_samples}\t{summary.disk_wait_samples}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sample per-thread CPU of the game process.")
    commands = parser.add_subparsers(dest="command", required=True)
    sampling = commands.add_parser("sample")
    sampling.add_argument("out", type=Path)
    sampling.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    sampling.add_argument("--pattern", default=DEFAULT_PATTERN)
    sampling.add_argument("--wait", type=float, default=DEFAULT_WAIT)
    summary = commands.add_parser("summarize")
    summary.add_argument("path", type=Path)
    summary.add_argument("--bucket", type=float, default=1.0)
    args = parser.parse_args(argv)

    if args.command == "sample":
        return sample(args.out, args.interval, args.pattern, args.wait)
    print_summary(args.path, args.bucket)
    return 0


if __name__ == "__main__":
    sys.exit(main())

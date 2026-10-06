#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = []
# ///

"""
Usage:
    analyze_bundles.py <bundle_loads.tsv> <markers.txt> [--out-dir DIR] [--prefix NAME]

Args:
    bundle_loads.tsv: per-load capture written by x2_load_profiler when bundle_log.txt exists in the mod folder
    markers.txt: the same run's x2_load_timing markers, used to find the queued and setup times
    --out-dir: where the per-load TSV slices go (default docs/diagnosis); --prefix names them

Note:
    Splits the capture into the startup, cold and warm loads, classifies each load by asset kind and scope,
    flags duplicates and load/release churn, and prints markdown tables. With R lines in the capture it also lists the pre-setup loads that were never read afterwards. See docs/load-time-report.md.
"""

import argparse
import struct
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import run

TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
SCOPES = {"strategy", "groundcombat", "common"}
PATH_PREFIX = "Assets/Assets/xenonauts/"


@dataclass(frozen=True)
class Load:
    seq: int
    done: datetime
    start: datetime
    request: datetime
    type: str
    path: str
    bundle: str
    pack: str
    parent: str


@dataclass(frozen=True)
class Unload:
    at: datetime
    type: str
    path: str


@dataclass(frozen=True)
class Read:
    at: datetime
    type: str
    path: str


@dataclass(frozen=True)
class BundleInfo:
    size: int
    compression: str


@dataclass(frozen=True)
class PredictorRow:
    key: str
    slow: int
    fast: int
    mean_ms: float


COMPRESSION = {0: "none", 1: "lzma", 2: "lz4", 3: "lz4hc"}
SIZE_BUCKETS = [(64 * 1024, "<64 KB"), (1024 * 1024, "64 KB-1 MB")]
SLOW_MS = 300.0


@dataclass
class Window:
    loads: list[Load] = field(default_factory=list)
    unloads: list[Unload] = field(default_factory=list)


@dataclass(frozen=True)
class ClassRow:
    key: tuple[str, str]
    count: int
    est_seconds: float
    latency_seconds: float


def parse_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT)


def parse_reads(text: str) -> list[Read]:
    """First reads of a loaded asset (R lines): when the game first called Get on it after each load."""
    reads = []
    for line in text.splitlines():
        cols = line.split("\t")
        if cols[0] == "R" and len(cols) == 4:
            reads.append(Read(parse_time(cols[1]), cols[2], cols[3]))
    return reads


def unread_loads(loads: list[Load], reads: list[Read], cutoff: datetime) -> list[Load]:
    """Loads whose asset was not read between the load finishing and the cutoff."""
    read_times: defaultdict[str, list[datetime]] = defaultdict(list)
    for r in reads:
        read_times[r.path].append(r.at)
    return [x for x in loads if not any(x.done <= t <= cutoff for t in read_times[x.path])]


def parse_tsv(text: str) -> tuple[list[Load], list[Unload]]:
    loads: list[Load] = []
    unloads: list[Unload] = []
    for line in text.splitlines():
        cols = line.split("\t")
        if cols[0] == "L" and len(cols) in (10, 11, 12):
            done = datetime.strptime(cols[2], TIME_FORMAT)
            start = done - timedelta(milliseconds=float(cols[4]))
            request = start - timedelta(milliseconds=float(cols[3]))
            loads.append(Load(int(cols[1]), done, start, request, cols[5], cols[6], cols[7], cols[8], cols[9]))
        elif cols[0] == "U" and len(cols) == 4:
            unloads.append(Unload(datetime.strptime(cols[1], TIME_FORMAT), cols[2], cols[3]))
    return loads, unloads


def parse_bundle_header(data: bytes, file_size: int) -> BundleInfo:
    """Compression of the block table from a UnityFS header (signature, version, two version strings, size, two table sizes, flags)."""
    if not data.startswith(b"UnityFS\x00"):
        raise ValueError("not a UnityFS bundle")
    pos = len(b"UnityFS\x00") + 4
    for _ in range(2):
        pos = data.index(b"\x00", pos) + 1
    (flags,) = struct.unpack(">I", data[pos + 16 : pos + 20])
    return BundleInfo(file_size, COMPRESSION[flags & 0x3])


def read_bundle_infos(bundle_dir: Path, names: set[str]) -> dict[str, BundleInfo]:
    infos = {}
    for name in names:
        path = bundle_dir / name
        if path.is_file():
            with path.open("rb") as f:
                infos[name] = parse_bundle_header(f.read(256), path.stat().st_size)
    return infos


def size_bucket(info: BundleInfo | None) -> str:
    if info is None:
        return "unknown"
    return next((label for limit, label in SIZE_BUCKETS if info.size < limit), ">=1 MB")


def latency_by(
    loads: list[Load], key: Callable[[Load, dict[str, BundleInfo]], str], infos: dict[str, BundleInfo], slow_ms: float = SLOW_MS
) -> list[PredictorRow]:
    """Per key, how many loads took at least slow_ms from start to done, and the mean start-to-done time."""
    groups: defaultdict[str, list[float]] = defaultdict(list)
    for x in loads:
        groups[key(x, infos)].append((x.done - x.start).total_seconds() * 1000)
    rows = [
        PredictorRow(k, sum(v >= slow_ms for v in ms), sum(v < slow_ms for v in ms), sum(ms) / len(ms))
        for k, ms in groups.items()
    ]
    return sorted(rows, key=lambda r: -(r.slow + r.fast))


def predictor_table(title: str, rows: list[PredictorRow]) -> str:
    out = [f"| {title} | Slow (>= {SLOW_MS:.0f} ms) | Fast | Mean start-to-done |", "|---|---|---|---|"]
    out += [f"| {r.key} | {r.slow} | {r.fast} | {r.mean_ms:.0f} ms |" for r in rows]
    return "\n".join(out)


def classify(path: str) -> tuple[str, str]:
    """(asset kind, scope) from `Assets/Assets/xenonauts/<kind>/<scope>/...`."""
    if not path.startswith(PATH_PREFIX):
        return ("other", "other")
    parts = path[len(PATH_PREFIX) :].split("/")
    kind = parts[0]
    scope = parts[1] if len(parts) > 2 and parts[1] in SCOPES else "other"
    return (kind, scope)


def split_windows(loads: list[Load], unloads: list[Unload], boundaries: list[datetime]) -> list[Window]:
    """One window per boundary plus the one before the first; loads go by request time, unloads by time."""
    windows = [Window() for _ in range(len(boundaries) + 1)]
    index = lambda t: sum(1 for b in boundaries if t >= b)  # noqa: E731
    for item in loads:
        windows[index(item.request)].loads.append(item)
    for item in unloads:
        windows[index(item.at)].unloads.append(item)
    return windows


def until(window: Window, cutoff: datetime) -> Window:
    return Window([x for x in window.loads if x.done <= cutoff], [x for x in window.unloads if x.at <= cutoff])


def duplicate_paths(window: Window) -> dict[str, int]:
    counts = Counter(x.path for x in window.loads)
    return {path: n for path, n in counts.items() if n > 1}


def reloaded_after_release(window: Window) -> list[Load]:
    """Loads of a path that was unloaded before the load was requested."""
    first_unload: dict[str, datetime] = {}
    for u in sorted(window.unloads, key=lambda x: x.at):
        first_unload.setdefault(u.path, u.at)
    return [x for x in window.loads if x.path in first_unload and first_unload[x.path] <= x.request]


def reloaded_names(window: Window) -> list[str]:
    return sorted({x.path for x in reloaded_after_release(window)})


def released_after_load(window: Window) -> list[Load]:
    """Loads of a path that was unloaded after the load finished."""
    last_unload: dict[str, datetime] = {}
    for u in window.unloads:
        last_unload[u.path] = max(u.at, last_unload.get(u.path, u.at))
    return [x for x in window.loads if x.path in last_unload and last_unload[x.path] >= x.done]


def summarize(window: Window) -> list[ClassRow]:
    """Per (kind, scope) load count, summed start-to-done time and a share of the window's active span."""
    if not window.loads:
        return []
    span = (max(x.done for x in window.loads) - min(x.request for x in window.loads)).total_seconds()
    counts: Counter[tuple[str, str]] = Counter()
    latency: defaultdict[tuple[str, str], float] = defaultdict(float)
    for x in window.loads:
        key = classify(x.path)
        counts[key] += 1
        latency[key] += (x.done - x.start).total_seconds()
    total = len(window.loads)
    rows = [ClassRow(k, n, span * n / total, latency[k]) for k, n in counts.items()]
    return sorted(rows, key=lambda r: -r.count)


def format_tsv(window: Window) -> str:
    lines = []
    for x in sorted(window.loads, key=lambda x: x.request):
        done = x.done.strftime(TIME_FORMAT)[:-3]
        lines.append(
            f"L\t{x.seq}\t{done}\t{(x.start - x.request).total_seconds() * 1000:.1f}\t{(x.done - x.start).total_seconds() * 1000:.1f}"
            f"\t{x.type}\t{x.path}\t{x.bundle}\t{x.pack}\t{x.parent}"
        )
    lines += [f"U\t{u.at.strftime(TIME_FORMAT)[:-3]}\t{u.type}\t{u.path}" for u in sorted(window.unloads, key=lambda u: u.at)]
    return "\n".join(lines) + "\n"


def markdown_table(rows: list[ClassRow]) -> str:
    out = ["| Kind | Scope | Loads | Est. seconds | Summed load time |", "|---|---|---|---|---|"]
    out += [f"| {r.key[0]} | {r.key[1]} | {r.count} | {r.est_seconds:.1f} s | {r.latency_seconds:.1f} s |" for r in rows]
    out.append(
        f"| total | | {sum(r.count for r in rows)} | {sum(r.est_seconds for r in rows):.1f} s | {sum(r.latency_seconds for r in rows):.1f} s |"
    )
    return "\n".join(out)


def describe(name: str, window: Window) -> str:
    reloaded = reloaded_after_release(window)
    released = released_after_load(window)
    dups = duplicate_paths(window)
    reloaded_rows = summarize(Window(reloaded, []))
    parts = [
        f"### {name}",
        f"{len(window.loads)} loads, {len(window.unloads)} unloads, {len(dups)} paths loaded more than once, "
        f"{len(reloaded)} loads of a path released earlier in the same window, {len(released)} loads released again afterwards.",
        markdown_table(summarize(window)),
        "Loads of a path released earlier in the window:",
        markdown_table(reloaded_rows) if reloaded_rows else "none",
    ]
    return "\n\n".join(parts)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Classify a bundle load capture.")
    parser.add_argument("tsv", type=Path)
    parser.add_argument("markers", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("docs/diagnosis"))
    parser.add_argument("--prefix", default="capture")
    parser.add_argument(
        "--bundle-dir", type=Path, help="folder with the game's bundle files; adds the size and compression predictor tables"
    )
    args = parser.parse_args(argv)

    loads, unloads = parse_tsv(args.tsv.read_text())
    reads = parse_reads(args.tsv.read_text())
    entries = run.parse_markers(args.markers.read_text())
    queued = [e.ts for e in entries if run.QUEUED_MARKER in e.message]
    windows = split_windows(loads, unloads, queued)
    names = ["startup"] + [f"load {i + 1} ({'cold' if i == 0 else 'warm'})" for i in range(len(queued))]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for i, (name, window) in enumerate(zip(names, windows, strict=True)):
        label = "startup" if i == 0 else ("cold" if i == 1 else f"warm{i - 1}")
        (args.out_dir / f"{args.prefix}-{label}-bundle-loads.tsv").write_text(format_tsv(window))
        (args.out_dir / f"{args.prefix}-{label}-reloaded-after-release.txt").write_text("\n".join(reloaded_names(window)) + "\n")
        print(describe(name, window))
        if i > 0:
            setup = next((e.ts for e in entries if run.SETUP_MARKER in e.message and e.ts > queued[i - 1]), None)
            if setup is not None:
                before = until(window, setup)
                print(describe(f"{name}, before setup", before))
                if reads:
                    unread = unread_loads(before.loads, reads, max(r.at for r in reads))
                    print(f"Loads before setup never read afterwards in this capture ({len(unread)} of {len(before.loads)}):")
                    print(markdown_table(summarize(Window(unread, []))))
                if args.bundle_dir:
                    infos = read_bundle_infos(args.bundle_dir, {x.bundle for x in before.loads})
                    tables = [
                        ("Bundle size", lambda x, i: size_bucket(i.get(x.bundle))),
                        ("Compression", lambda x, i: i[x.bundle].compression if x.bundle in i else "unknown"),
                        ("Asset type", lambda x, i: x.type),
                    ]
                    print("\n\n".join(predictor_table(t, latency_by(before.loads, k, infos)) for t, k in tables))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

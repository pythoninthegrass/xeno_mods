#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["python-decouple>=3.8"]
# ///

"""
Usage:
    run.py <run-name> [--load auto|menu]

Args:
    run-name: folder under $DATA/Logs that receives the run's output.log*
    --load: auto queues the save from the x2_load_profiler mod (default); menu clicks through the main menu with JXA

Note:
    Performs one cold measurement run of Xenonauts 2 under CrossOver: close the game, archive logs, launch,
    load the baseline save, wait until playable, quit, archive the run's logs.
    Menu mode takes over mouse input on the host desktop. See docs/automated-runs.md.
"""

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

DEFAULT_BOTTLE = "~/Library/Application Support/CrossOver/Bottles/Steam/drive_c"
DEFAULT_LAUNCHER_APP = "~/Applications/CrossOver/Steam/Xenonauts 2.app"
DEFAULT_SAVE_REL = "Saves/ellz_1bf479e6/auto/auto_groundcombat_turn_10_start-62.json"
DEFAULT_GAME_PROCESS_PATTERN = "[X]enonauts2.exe"
DEFAULT_STEAM_PROCESS_PATTERN = "[s]team.exe"
DEFAULT_PLAYABLE_MARKER = "GCUI: BlockOnLocalPlayerTurn"
DEFAULT_MENU_READY_MARKER = "XenonautsLoadScreen: Outro Complete"
DEFAULT_STATE_LOSS_PATTERN = "state-loss"
DEFAULT_MOD_NAME = "x2_load_profiler"
DEFAULT_LEFTOVER_ARCHIVE_PREFIX = "pre-"
QUEUED_MARKER = "Queued LoadGameCommand"
SETUP_MARKER = "Handling Setup for GroundCombat"
INTRO_MARKER = "XenonautsLoadScreen: Intro Complete"
LOSE_FOCUS_MARKER = "LoadingWorld - Handled LoseFocusScreenReport"

HEADER_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}) \[(\w+)\] ")
QUEUED_PATH_RE = re.compile(
    r"SaveGameDescriptor: (?:FD\[[A-Z]+\]>)?FileSystem::(.+?)\)?\s*$"
)
RUN_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class RunError(Exception):
    """A failure the run reports to the user and turns into exit code 1."""


@dataclass(frozen=True)
class Entry:
    ts: datetime
    message: str
    level: str = ""


@dataclass(frozen=True)
class Timings:
    queued: datetime | None
    setup: datetime | None
    playable: datetime | None
    intro: datetime | None
    lose_focus: datetime | None

    @staticmethod
    def _gap(start: datetime | None, end: datetime | None) -> float | None:
        return None if start is None or end is None else (end - start).total_seconds()

    @property
    def queue_to_setup(self) -> float | None:
        return self._gap(self.queued, self.setup)

    @property
    def queue_to_playable(self) -> float | None:
        return self._gap(self.queued, self.playable)

    @property
    def intro_to_setup(self) -> float | None:
        return self._gap(self.intro, self.setup)

    @property
    def lose_focus_to_setup(self) -> float | None:
        return self._gap(self.lose_focus, self.setup)


@dataclass(frozen=True)
class Settings:
    bottle: Path
    game_dir: Path
    data_dir: Path
    launcher_app: Path
    save_rel: str
    launch_timeout: int
    load_timeout: int
    menu_load_game: tuple[int, int]
    menu_save_row: tuple[int, int]
    menu_load_save: tuple[int, int]
    mod_name: str
    leftover_archive_prefix: str
    state_loss_pattern: str
    playable_marker: str
    menu_ready_marker: str
    game_process_pattern: str
    steam_process_pattern: str
    quit_grace: int
    poll_interval: float

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "Logs"

    @property
    def mod_dir(self) -> Path:
        return self.data_dir / "Mods" / self.mod_name

    @property
    def auto_load_file(self) -> Path:
        return self.mod_dir / "auto_load.txt"

    @property
    def save_abs(self) -> str:
        return f"C:/users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2/{self.save_rel}"

    @property
    def guarded_config_files(self) -> list[Path]:
        return [
            self.game_dir / "optimizing.json",
            self.mod_dir / "unity_experiment.txt",
            self.game_dir / "Assets" / "Configuration" / "log4net.xml",
        ]

    @property
    def steam_console_log(self) -> Path:
        return (
            self.bottle / "Program Files (x86)" / "Steam" / "logs" / "console_log.txt"
        )


def parse_entries(text: str) -> list[Entry]:
    """Split the wrapped log format into records: a header line, then message lines until a blank line."""
    entries: list[Entry] = []
    header: tuple[datetime, str] | None = None
    lines: list[str] = []

    def flush() -> None:
        if header is not None:
            entries.append(Entry(header[0], "\n".join(lines), header[1]))

    for line in text.splitlines():
        match = HEADER_RE.match(line)
        if match:
            flush()
            header = (
                datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f"),
                match.group(2),
            )
            lines = []
        elif header is not None:
            if line.strip():
                lines.append(line)
            else:
                flush()
                header = None
                lines = []
    flush()
    return entries


def queued_save_path(entries: list[Entry]) -> str | None:
    for e in entries:
        if QUEUED_MARKER in e.message:
            match = QUEUED_PATH_RE.search(e.message)
            return match.group(1) if match else None
    return None


def is_expected_save(path: str | None, save_rel: str) -> bool:
    return path is not None and path.replace("\\", "/").endswith(
        save_rel.replace("\\", "/")
    )


def find_timings(
    entries: list[Entry], playable_marker: str = DEFAULT_PLAYABLE_MARKER
) -> Timings:
    queued = next((e.ts for e in entries if QUEUED_MARKER in e.message), None)
    if queued is None:
        return Timings(None, None, None, None, None)
    after = [e for e in entries if e.ts >= queued]
    setup = next((e.ts for e in after if SETUP_MARKER in e.message), None)
    playable = next((e.ts for e in after if playable_marker in e.message), None)
    before_setup = [e for e in after if setup is None or e.ts <= setup]
    intro = next(
        (e.ts for e in reversed(before_setup) if INTRO_MARKER in e.message), None
    )
    lose_focus = next(
        (e.ts for e in reversed(before_setup) if LOSE_FOCUS_MARKER in e.message), None
    )
    return Timings(queued, setup, playable, intro, lose_focus)


def count_errors(text: str) -> int:
    return sum(1 for e in parse_entries(text) if e.level == "ERROR")


def count_state_loss(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.IGNORECASE))


def leftover_archive_name(run_name: str, prefix: str) -> str:
    return f"{prefix}{run_name}"


def parse_point(text: str) -> tuple[int, int]:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 2:
        raise ValueError(f"expected 'x,y', got {text!r}")
    return int(parts[0]), int(parts[1])


def auto_load_text(save_path: str) -> str:
    return f"save={save_path}\n"


def validate_run_name(name: str) -> None:
    if not RUN_NAME_RE.fullmatch(name) or name in {".", ".."}:
        raise ValueError(
            f"invalid run name {name!r}: use letters, digits, '.', '_' and '-' only"
        )


def hash_files(paths: list[Path]) -> dict[Path, str | None]:
    return {
        p: sha256(p.read_bytes()).hexdigest() if p.is_file() else None for p in paths
    }


def changed_files(
    before: Mapping[Path, str | None], after: Mapping[Path, str | None]
) -> list[Path]:
    return sorted(
        p for p in before.keys() | after.keys() if before.get(p) != after.get(p)
    )


class _MappingRepository:
    """decouple repository backed by a plain mapping."""

    def __init__(self, data: Mapping[str, str]):
        self.data = data

    def __contains__(self, key: str) -> bool:
        return key in self.data

    def __getitem__(self, key: str) -> str:
        return self.data[key]


def load_settings(cwd: Path, env: Mapping[str, str] | None = None) -> Settings:
    from decouple import Config, RepositoryEnv

    env_file = cwd / ".env"
    file_values = RepositoryEnv(str(env_file)).data if env_file.exists() else {}
    process_env = os.environ if env is None else env
    config = Config(_MappingRepository({**file_values, **process_env}))

    def path(key: str, default: str) -> Path:
        return Path(config(key, default=default)).expanduser()

    bottle = path("BOTTLE", DEFAULT_BOTTLE)
    game_dir = path(
        "GAME_DIR",
        str(bottle / "Program Files (x86)/Steam/steamapps/common/Xenonauts2"),
    )
    data_dir = path(
        "DATA_DIR",
        str(
            bottle / "users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2"
        ),
    )
    return Settings(
        bottle=bottle,
        game_dir=game_dir,
        data_dir=data_dir,
        launcher_app=path("LAUNCHER_APP", DEFAULT_LAUNCHER_APP),
        save_rel=config("SAVE_REL", default=DEFAULT_SAVE_REL),
        launch_timeout=config("LAUNCH_TIMEOUT", default=60, cast=int),
        load_timeout=config("LOAD_TIMEOUT", default=120, cast=int),
        menu_load_game=parse_point(config("MENU_LOAD_GAME", default="1331,1302")),
        menu_save_row=parse_point(config("MENU_SAVE_ROW", default="947,426")),
        menu_load_save=parse_point(config("MENU_LOAD_SAVE", default="960,1112")),
        mod_name=config("MOD_NAME", default=DEFAULT_MOD_NAME),
        leftover_archive_prefix=config(
            "LEFTOVER_ARCHIVE_PREFIX", default=DEFAULT_LEFTOVER_ARCHIVE_PREFIX
        ),
        state_loss_pattern=config(
            "STATE_LOSS_PATTERN", default=DEFAULT_STATE_LOSS_PATTERN
        ),
        playable_marker=config("PLAYABLE_MARKER", default=DEFAULT_PLAYABLE_MARKER),
        menu_ready_marker=config(
            "MENU_READY_MARKER", default=DEFAULT_MENU_READY_MARKER
        ),
        game_process_pattern=config(
            "GAME_PROCESS_PATTERN", default=DEFAULT_GAME_PROCESS_PATTERN
        ),
        steam_process_pattern=config(
            "STEAM_PROCESS_PATTERN", default=DEFAULT_STEAM_PROCESS_PATTERN
        ),
        quit_grace=config("QUIT_GRACE", default=15, cast=int),
        poll_interval=config("POLL_INTERVAL", default=0.5, cast=float),
    )


def game_pids(s: Settings) -> list[int]:
    result = subprocess.run(
        ["pgrep", "-f", s.game_process_pattern], capture_output=True, text=True
    )
    return [int(p) for p in result.stdout.split()]


def wait_until(
    predicate: Callable[[], bool], timeout_s: float, poll_interval: float
) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(poll_interval)
    return predicate()


def stop_game(s: Settings) -> None:
    """SIGTERM the game, then SIGKILL if it is still alive after the grace period."""
    gone = lambda: not game_pids(s)  # noqa: E731
    if gone():
        return
    subprocess.run(["pkill", "-TERM", "-f", s.game_process_pattern])
    if not wait_until(gone, s.quit_grace, s.poll_interval):
        subprocess.run(["pkill", "-KILL", "-f", s.game_process_pattern])
        if not wait_until(gone, 5, s.poll_interval):
            raise RunError("the game process would not exit")


def preflight(s: Settings) -> None:
    if not s.launcher_app.exists():
        raise RunError(f"launcher app not found: {s.launcher_app}")
    if (
        subprocess.run(
            ["pgrep", "-f", s.steam_process_pattern], capture_output=True
        ).returncode
        != 0
    ):
        raise RunError("CrossOver Steam is not running; start it and log in first")
    if (
        s.steam_console_log.exists()
        and "syncfailed" in s.steam_console_log.read_text(errors="replace")[-20000:]
    ):
        raise RunError(
            "Steam console_log.txt reports a failed cloud sync; disable Steam Cloud sync for Xenonauts 2"
        )


def archive_leftover_logs(s: Settings, run_name: str) -> None:
    leftovers = sorted(s.logs_dir.glob("output.log*"))
    if not leftovers:
        return
    dest = s.logs_dir / leftover_archive_name(run_name, s.leftover_archive_prefix)
    dest.mkdir(parents=True)
    for f in leftovers:
        shutil.move(f, dest / f.name)


def read_log(s: Settings) -> str:
    log = s.logs_dir / "output.log"
    return log.read_text(errors="replace") if log.exists() else ""


def wait_for_log(
    s: Settings, predicate: Callable[[list[Entry]], bool], timeout_s: float
) -> bool:
    return wait_until(
        lambda: predicate(parse_entries(read_log(s))), timeout_s, s.poll_interval
    )


JXA_CLICK = """
ObjC.import('CoreGraphics');
function post(type, x, y) {
  const e = $.CGEventCreateMouseEvent($(), type, $.CGPointMake(x, y), $.kCGMouseButtonLeft);
  $.CGEventPost($.kCGHIDEventTap, e);
}
function click(x, y) {
  post($.kCGEventMouseMoved, x, y);
  delay(0.3);
  post($.kCGEventLeftMouseDown, x, y);
  delay(0.08);
  post($.kCGEventLeftMouseUp, x, y);
}
click(%d, %d);
"""


def click(point: tuple[int, int]) -> None:
    subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", JXA_CLICK % point], check=True
    )


def menu_load(s: Settings) -> None:
    if not wait_for_log(
        s,
        lambda es: any(s.menu_ready_marker in e.message for e in es),
        s.launch_timeout,
    ):
        raise RunError(f"main menu was not ready within {s.launch_timeout} s of launch")
    time.sleep(1)
    for point in (s.menu_load_game, s.menu_save_row, s.menu_load_save):
        click(point)
        time.sleep(1.5)


def perform_run(s: Settings, run_name: str, load: str) -> Timings:
    s.logs_dir.mkdir(parents=True, exist_ok=True)
    stop_game(s)
    archive_leftover_logs(s, run_name)
    if load == "auto":
        s.auto_load_file.write_text(auto_load_text(s.save_abs))
    print(f"launching {s.launcher_app.name} (load={load})")
    subprocess.run(["open", str(s.launcher_app)], check=True)
    if not wait_until(lambda: bool(game_pids(s)), s.launch_timeout, s.poll_interval):
        raise RunError(f"Xenonauts2.exe did not start within {s.launch_timeout} s")
    if load == "menu":
        menu_load(s)

    if not wait_for_log(
        s,
        lambda es: queued_save_path(es) is not None,
        s.launch_timeout + s.load_timeout,
    ):
        raise RunError(
            "no 'Queued LoadGameCommand' line appeared; the save was never loaded"
        )
    queued = queued_save_path(parse_entries(read_log(s)))
    if not is_expected_save(queued, s.save_rel):
        raise RunError(f"wrong save loaded: expected {s.save_rel}, log shows {queued}")
    if not wait_for_log(
        s, lambda es: any(s.playable_marker in e.message for e in es), s.load_timeout
    ):
        raise RunError(
            f"playable marker not reached within {s.load_timeout} s of the save being queued"
        )
    text = read_log(s)
    stop_game(s)

    dest = s.logs_dir / run_name
    dest.mkdir(parents=True)
    for f in sorted(s.logs_dir.glob("output.log*")):
        shutil.move(f, dest / f.name)
    print(f"logs archived to {dest}")
    print(
        f"errors: {count_errors(text)}, state-loss: {count_state_loss(text, s.state_loss_pattern)}"
    )
    return find_timings(parse_entries(text), s.playable_marker)


def format_seconds(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f} s"


def print_timings(t: Timings) -> None:
    print(f"queue to setup:      {format_seconds(t.queue_to_setup)}")
    print(f"queue to playable:   {format_seconds(t.queue_to_playable)}")
    print(f"intro to setup:      {format_seconds(t.intro_to_setup)}")
    print(f"lose focus to setup: {format_seconds(t.lose_focus_to_setup)}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Run one cold measurement run of Xenonauts 2."
    )
    parser.add_argument("run_name")
    parser.add_argument("--load", choices=["auto", "menu"], default="auto")
    args = parser.parse_args(argv)

    try:
        validate_run_name(args.run_name)
        s = load_settings(Path.cwd())
        for taken in (
            args.run_name,
            leftover_archive_name(args.run_name, s.leftover_archive_prefix),
        ):
            if (s.logs_dir / taken).exists():
                raise RunError(f"{s.logs_dir / taken} already exists")
        preflight(s)
    except (ValueError, RunError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    before = hash_files(s.guarded_config_files)
    failure: str | None = None
    timings: Timings | None = None
    try:
        timings = perform_run(s, args.run_name, args.load)
    except RunError as exc:
        failure = str(exc)
    except KeyboardInterrupt:
        failure = "interrupted"
    except subprocess.CalledProcessError as exc:
        failure = f"command failed: {exc}"
    finally:
        try:
            stop_game(s)
        except RunError as exc:
            failure = failure or str(exc)
        s.auto_load_file.unlink(missing_ok=True)
        modified = changed_files(before, hash_files(s.guarded_config_files))
        if modified:
            failure = (
                (failure + "; " if failure else "")
                + "config files modified: "
                + ", ".join(str(p) for p in modified)
            )

    if failure:
        print(f"error: {failure}", file=sys.stderr)
        return 1
    assert timings is not None
    print_timings(timings)
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    sys.exit(main(sys.argv[1:]))

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
    Performs one cold measurement run of Xenonauts 2: close the game, archive logs, launch, load the
    baseline save, wait until playable, quit, archive the run's logs. Runs on macOS under CrossOver
    and on Linux under Proton; the defaults that differ are in PLATFORM_DEFAULTS.
    Menu mode takes over mouse input on the desktop it runs against. See docs/automated-runs.md.
"""

import argparse
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

STEAM_APP_ID = "538030"

DEFAULT_MACOS_BOTTLE = "~/Library/Application Support/CrossOver/Bottles/Steam/drive_c"
DEFAULT_LINUX_BOTTLE = f"~/.steam/steam/steamapps/compatdata/{STEAM_APP_ID}/pfx/drive_c"
DEFAULT_MACOS_LAUNCHER_APP = "~/Applications/CrossOver/Steam/Xenonauts 2.app"
DEFAULT_MACOS_GAME_DIR = "{bottle}/Program Files (x86)/Steam/steamapps/common/Xenonauts2"
DEFAULT_LINUX_GAME_DIR = "~/.steam/steam/steamapps/common/Xenonauts2"
DEFAULT_MACOS_WINE_USER = "crossover"
DEFAULT_LINUX_WINE_USER = "steamuser"
DEFAULT_MACOS_STEAM_CONSOLE_LOG = "{bottle}/Program Files (x86)/Steam/logs/console_log.txt"
DEFAULT_LINUX_STEAM_CONSOLE_LOG = "~/.steam/steam/logs/console_log.txt"
DEFAULT_MACOS_STEAM_PROCESS_PATTERN = "[s]team.exe"
DEFAULT_LINUX_STEAM_PROCESS_PATTERN = "[s]teamwebhelper"
DEFAULT_MACOS_LAUNCH_CMD = ("open", "{app}")
DEFAULT_LINUX_LAUNCH_CMD = ("steam", f"steam://rungameid/{STEAM_APP_ID}")

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
click({x}, {y});
"""

DEFAULT_MACOS_CLICK_CMD = ("osascript", "-l", "JavaScript", "-e", JXA_CLICK)
DEFAULT_LINUX_CLICK_CMD = ("xdotool", "mousemove", "{x}", "{y}", "click", "1")
DEFAULT_SAVE_REL = "Saves/ellz_1bf479e6/auto/auto_groundcombat_turn_10_start-62.json"
DEFAULT_GAME_PROCESS_PATTERN = "[X]enonauts2.exe"
DEFAULT_PLAYABLE_MARKER = "GCUI: BlockOnLocalPlayerTurn"
DEFAULT_MENU_READY_MARKER = "XenonautsLoadScreen: Outro Complete"
DEFAULT_STATE_LOSS_PATTERN = "state-loss"
DEFAULT_MOD_NAME = "x2_load_profiler"
DEFAULT_TIMING_MOD_NAME = "x2_load_timing"
DEFAULT_LEFTOVER_ARCHIVE_PREFIX = "pre-"
QUEUED_MARKER = "Queued LoadGameCommand"
SETUP_MARKER = "Handling Setup for GroundCombat"
INTRO_MARKER = "XenonautsLoadScreen: Intro Complete"
LOSE_FOCUS_MARKER = "LoadingWorld - Handled LoseFocusScreenReport"

HEADER_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}) \[(\w+)\] ")
MARKER_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}) (.+)$")
QUEUED_PATH_RE = re.compile(r"SaveGameDescriptor: (?:FD\[[A-Z]+\]>)?FileSystem::(.+?)\)?\s*$")
RUN_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class RunError(Exception):
    """A failure the run reports to the user and turns into exit code 1."""


@dataclass(frozen=True)
class PlatformDefaults:
    """The built-in defaults that differ between the CrossOver host and the Proton host."""

    wine_user: str
    bottle: str
    launcher_app: str
    """Empty where the platform launches the game without an app bundle."""
    game_dir: str
    steam_console_log: str
    steam_process_pattern: str
    launch_cmd: tuple[str, ...]
    click_cmd: tuple[str, ...]


PLATFORM_DEFAULTS = {
    "darwin": PlatformDefaults(
        wine_user=DEFAULT_MACOS_WINE_USER,
        bottle=DEFAULT_MACOS_BOTTLE,
        launcher_app=DEFAULT_MACOS_LAUNCHER_APP,
        game_dir=DEFAULT_MACOS_GAME_DIR,
        steam_console_log=DEFAULT_MACOS_STEAM_CONSOLE_LOG,
        steam_process_pattern=DEFAULT_MACOS_STEAM_PROCESS_PATTERN,
        launch_cmd=DEFAULT_MACOS_LAUNCH_CMD,
        click_cmd=DEFAULT_MACOS_CLICK_CMD,
    ),
    "linux": PlatformDefaults(
        wine_user=DEFAULT_LINUX_WINE_USER,
        bottle=DEFAULT_LINUX_BOTTLE,
        launcher_app="",
        game_dir=DEFAULT_LINUX_GAME_DIR,
        steam_console_log=DEFAULT_LINUX_STEAM_CONSOLE_LOG,
        steam_process_pattern=DEFAULT_LINUX_STEAM_PROCESS_PATTERN,
        launch_cmd=DEFAULT_LINUX_LAUNCH_CMD,
        click_cmd=DEFAULT_LINUX_CLICK_CMD,
    ),
}


def platform_defaults(platform: str) -> PlatformDefaults:
    return PLATFORM_DEFAULTS.get(platform, PLATFORM_DEFAULTS["linux"])


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
    launcher_app: Path | None
    wine_user: str
    save_rel: str
    launch_timeout: int
    load_timeout: int
    menu_load_game: tuple[int, int]
    menu_save_row: tuple[int, int]
    menu_load_save: tuple[int, int]
    game_menu_button: tuple[int, int]
    game_menu_load_game: tuple[int, int]
    game_menu_save_row: tuple[int, int]
    mod_name: str
    timing_mod_name: str
    leftover_archive_prefix: str
    state_loss_pattern: str
    playable_marker: str
    menu_ready_marker: str
    game_process_pattern: str
    steam_process_pattern: str
    quit_grace: int
    poll_interval: float
    steam_console_log: Path
    launch_cmd: tuple[str, ...]
    click_cmd: tuple[str, ...]

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "Logs"

    @property
    def mod_dir(self) -> Path:
        return self.data_dir / "Mods" / self.mod_name

    @property
    def markers_file(self) -> Path:
        return self.data_dir / "Mods" / self.timing_mod_name / "markers.txt"

    @property
    def auto_load_file(self) -> Path:
        return self.mod_dir / "auto_load.txt"

    @property
    def save_abs(self) -> str:
        return f"C:/users/{self.wine_user}/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2/{self.save_rel}"

    @property
    def guarded_config_files(self) -> list[Path]:
        return [
            self.game_dir / "optimizing.json",
            self.mod_dir / "unity_experiment.txt",
            self.game_dir / "Assets" / "Configuration" / "log4net.xml",
        ]


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


def parse_markers(text: str) -> list[Entry]:
    """One entry per `<timestamp> <message>` line written by the x2_load_timing mod."""
    entries: list[Entry] = []
    for line in text.splitlines():
        match = MARKER_RE.match(line)
        if match:
            entries.append(Entry(datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f"), match.group(2)))
    return entries


def timing_entries(log_text: str, markers_text: str) -> list[Entry]:
    """Mod markers when the timing mod wrote any, otherwise the game's own log lines (DEBUG or INFO configuration)."""
    return parse_markers(markers_text) or parse_entries(log_text)


def queued_save_path(entries: list[Entry]) -> str | None:
    for e in entries:
        if QUEUED_MARKER in e.message:
            match = QUEUED_PATH_RE.search(e.message)
            return match.group(1) if match else None
    return None


def last_queued_save_path(entries: list[Entry]) -> str | None:
    for i in range(len(entries) - 1, -1, -1):
        if QUEUED_MARKER in entries[i].message:
            return queued_save_path(entries[i:])
    return None


def is_expected_save(path: str | None, save_rel: str) -> bool:
    return path is not None and path.replace("\\", "/").endswith(save_rel.replace("\\", "/"))


def find_timings(entries: list[Entry], playable_marker: str = DEFAULT_PLAYABLE_MARKER) -> Timings:
    queued = next((e.ts for e in entries if QUEUED_MARKER in e.message), None)
    if queued is None:
        return Timings(None, None, None, None, None)
    after = [e for e in entries if e.ts >= queued]
    setup = next((e.ts for e in after if SETUP_MARKER in e.message), None)
    playable = next((e.ts for e in after if playable_marker in e.message), None)
    before_setup = [e for e in after if setup is None or e.ts <= setup]
    intro = next((e.ts for e in reversed(before_setup) if INTRO_MARKER in e.message), None)
    lose_focus = next((e.ts for e in reversed(before_setup) if LOSE_FOCUS_MARKER in e.message), None)
    return Timings(queued, setup, playable, intro, lose_focus)


def find_load_timings(entries: list[Entry], playable_marker: str = DEFAULT_PLAYABLE_MARKER) -> list[Timings]:
    """One Timings per queued load, each bounded by the next queued load."""
    starts = [i for i, e in enumerate(entries) if QUEUED_MARKER in e.message]
    ends = starts[1:] + [len(entries)]
    return [find_timings(entries[start:end], playable_marker) for start, end in zip(starts, ends, strict=False)]


def count_errors(text: str) -> int:
    return sum(1 for e in parse_entries(text) if e.level == "ERROR")


def count_state_loss(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.IGNORECASE))


def leftover_archive_name(run_name: str, prefix: str) -> str:
    return f"{prefix}{run_name}"


def cloud_sync_blocked(console_log: str) -> bool:
    """True when the latest syncfailed line has no later completed launch after it."""
    failed = console_log.rfind("syncfailed")
    return failed != -1 and console_log.rfind("LaunchApp changed task to Completed") < failed


def substitute(argv: Sequence[str], replacements: Mapping[str, str]) -> list[str]:
    """Literal token replacement, not str.format: the JXA clicker's own braces must survive."""
    out = []
    for arg in argv:
        for token, value in replacements.items():
            arg = arg.replace(token, value)
        out.append(arg)
    return out


def launch_command(s: Settings) -> list[str]:
    return substitute(s.launch_cmd, {"{app}": str(s.launcher_app) if s.launcher_app else ""})


def click_command(s: Settings, point: tuple[int, int]) -> list[str]:
    return substitute(s.click_cmd, {"{x}": str(point[0]), "{y}": str(point[1])})


def parse_point(text: str) -> tuple[int, int]:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 2:
        raise ValueError(f"expected 'x,y', got {text!r}")
    return int(parts[0]), int(parts[1])


def auto_load_text(save_path: str) -> str:
    return f"save={save_path}\n"


def validate_run_name(name: str) -> None:
    if not RUN_NAME_RE.fullmatch(name) or name in {".", ".."}:
        raise ValueError(f"invalid run name {name!r}: use letters, digits, '.', '_' and '-' only")


def hash_files(paths: list[Path]) -> dict[Path, str | None]:
    return {p: sha256(p.read_bytes()).hexdigest() if p.is_file() else None for p in paths}


def changed_files(before: Mapping[Path, str | None], after: Mapping[Path, str | None]) -> list[Path]:
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))


class _MappingRepository:
    """decouple repository backed by a plain mapping."""

    def __init__(self, data: Mapping[str, str]):
        self.data = data

    def __contains__(self, key: str) -> bool:
        return key in self.data

    def __getitem__(self, key: str) -> str:
        return self.data[key]


def load_settings(cwd: Path, env: Mapping[str, str] | None = None, platform: str = sys.platform) -> Settings:
    from decouple import Config, RepositoryEnv

    d = platform_defaults(platform)

    env_file = cwd / ".env"
    file_values = RepositoryEnv(str(env_file)).data if env_file.exists() else {}
    process_env = os.environ if env is None else env
    config = Config(_MappingRepository({**file_values, **process_env}))

    def command(key: str, default: tuple[str, ...]) -> tuple[str, ...]:
        """Overrides are shell-quoted strings; the defaults stay tuples because the JXA clicker cannot survive a split."""
        value = config(key, default="")
        return tuple(shlex.split(value)) if value else default

    bottle = Path(config("BOTTLE", default=d.bottle)).expanduser()

    def path(key: str, default: str) -> Path:
        """'{bottle}' expands to the configured bottle, in the default and in a configured value alike."""
        return Path(config(key, default=default).replace("{bottle}", str(bottle))).expanduser()

    wine_user = config("WINE_USER", default=d.wine_user)
    game_dir = path("GAME_DIR", d.game_dir)
    data_dir = path(
        "DATA_DIR",
        str(bottle / f"users/{wine_user}/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2"),
    )
    launcher_app = config("LAUNCHER_APP", default=d.launcher_app)
    return Settings(
        bottle=bottle,
        game_dir=game_dir,
        data_dir=data_dir,
        launcher_app=Path(launcher_app).expanduser() if launcher_app else None,
        wine_user=wine_user,
        save_rel=config("SAVE_REL", default=DEFAULT_SAVE_REL),
        launch_timeout=config("LAUNCH_TIMEOUT", default=60, cast=int),
        load_timeout=config("LOAD_TIMEOUT", default=120, cast=int),
        menu_load_game=parse_point(config("MENU_LOAD_GAME", default="1331,1302")),
        menu_save_row=parse_point(config("MENU_SAVE_ROW", default="947,426")),
        menu_load_save=parse_point(config("MENU_LOAD_SAVE", default="960,1112")),
        game_menu_button=parse_point(config("GAME_MENU_BUTTON", default="54,54")),
        game_menu_load_game=parse_point(config("GAME_MENU_LOAD_GAME", default="1280,760")),
        game_menu_save_row=parse_point(config("GAME_MENU_SAVE_ROW", default="896,426")),
        mod_name=config("MOD_NAME", default=DEFAULT_MOD_NAME),
        timing_mod_name=config("TIMING_MOD_NAME", default=DEFAULT_TIMING_MOD_NAME),
        leftover_archive_prefix=config("LEFTOVER_ARCHIVE_PREFIX", default=DEFAULT_LEFTOVER_ARCHIVE_PREFIX),
        state_loss_pattern=config("STATE_LOSS_PATTERN", default=DEFAULT_STATE_LOSS_PATTERN),
        playable_marker=config("PLAYABLE_MARKER", default=DEFAULT_PLAYABLE_MARKER),
        menu_ready_marker=config("MENU_READY_MARKER", default=DEFAULT_MENU_READY_MARKER),
        game_process_pattern=config("GAME_PROCESS_PATTERN", default=DEFAULT_GAME_PROCESS_PATTERN),
        steam_process_pattern=config("STEAM_PROCESS_PATTERN", default=d.steam_process_pattern),
        quit_grace=config("QUIT_GRACE", default=15, cast=int),
        poll_interval=config("POLL_INTERVAL", default=0.5, cast=float),
        steam_console_log=path("STEAM_CONSOLE_LOG", d.steam_console_log),
        launch_cmd=command("LAUNCH_CMD", d.launch_cmd),
        click_cmd=command("CLICK_CMD", d.click_cmd),
    )


def game_pids(s: Settings) -> list[int]:
    result = subprocess.run(["pgrep", "-f", s.game_process_pattern], capture_output=True, text=True)
    return [int(p) for p in result.stdout.split()]


def wait_until(predicate: Callable[[], bool], timeout_s: float, poll_interval: float) -> bool:
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


def launcher_app_problem(s: Settings) -> str | None:
    """None where the platform launches without an app bundle, so LAUNCHER_APP is unset."""
    if s.launcher_app is not None and not s.launcher_app.exists():
        return f"launcher app not found: {s.launcher_app}"
    return None


def preflight(s: Settings) -> None:
    problem = launcher_app_problem(s)
    if problem:
        raise RunError(problem)
    if subprocess.run(["pgrep", "-f", s.steam_process_pattern], capture_output=True).returncode != 0:
        raise RunError("CrossOver Steam is not running; start it and log in first")
    if s.steam_console_log.exists() and cloud_sync_blocked(s.steam_console_log.read_text(errors="replace")):
        raise RunError("Steam console_log.txt reports a failed cloud sync; disable Steam Cloud sync for Xenonauts 2")


def archive_leftover_logs(s: Settings, run_name: str) -> None:
    leftovers = sorted(s.logs_dir.glob("output.log*")) + ([s.markers_file] if s.markers_file.exists() else [])
    if not leftovers:
        return
    dest = s.logs_dir / leftover_archive_name(run_name, s.leftover_archive_prefix)
    dest.mkdir(parents=True)
    for f in leftovers:
        shutil.move(f, dest / f.name)


def read_log(s: Settings) -> str:
    log = s.logs_dir / "output.log"
    return log.read_text(errors="replace") if log.exists() else ""


def read_markers(s: Settings) -> str:
    return s.markers_file.read_text(errors="replace") if s.markers_file.exists() else ""


def read_timing_entries(s: Settings) -> list[Entry]:
    return timing_entries(read_log(s), read_markers(s))


def wait_for_log(s: Settings, predicate: Callable[[list[Entry]], bool], timeout_s: float) -> bool:
    return wait_until(lambda: predicate(read_timing_entries(s)), timeout_s, s.poll_interval)


def click(s: Settings, point: tuple[int, int]) -> None:
    subprocess.run(click_command(s, point), check=True)


def bring_game_to_front() -> None:
    """Menu clicks land on whatever window is frontmost, so raise the game first."""
    script = 'tell application "System Events" to set frontmost of (first process whose name contains "Xenonauts") to true'
    subprocess.run(["osascript", "-e", script], check=True)


def menu_load(s: Settings) -> None:
    if not wait_for_log(
        s,
        lambda es: any(s.menu_ready_marker in e.message for e in es),
        s.launch_timeout,
    ):
        raise RunError(f"main menu was not ready within {s.launch_timeout} s of launch")
    time.sleep(1)
    bring_game_to_front()
    for point in (s.menu_load_game, s.menu_save_row, s.menu_load_save):
        click(s, point)
        time.sleep(1.5)


def count_playable(s: Settings) -> int:
    return sum(1 for e in read_timing_entries(s) if s.playable_marker in e.message)


def warm_load(s: Settings) -> None:
    """Reload the baseline save through the in-game menu; the row is positional like the main menu one."""
    before = count_playable(s)
    time.sleep(2)
    bring_game_to_front()
    for point in (
        s.game_menu_button,
        s.game_menu_load_game,
        s.game_menu_save_row,
        s.menu_load_save,
    ):
        click(s, point)
        time.sleep(1.5)
    if not wait_until(lambda: count_playable(s) > before, s.load_timeout, s.poll_interval):
        raise RunError(f"playable marker not reached within {s.load_timeout} s of the warm load")
    queued = last_queued_save_path(read_timing_entries(s))
    if not is_expected_save(queued, s.save_rel):
        raise RunError(f"wrong warm save loaded: expected {s.save_rel}, log shows {queued}")


def perform_run(s: Settings, run_name: str, load: str, warm_loads: int = 0) -> list[Timings]:
    s.logs_dir.mkdir(parents=True, exist_ok=True)
    stop_game(s)
    archive_leftover_logs(s, run_name)
    if load == "auto":
        s.auto_load_file.write_text(auto_load_text(s.save_abs))
    command = launch_command(s)
    print(f"launching with {shlex.join(command)} (load={load})")
    subprocess.run(command, check=True)
    if not wait_until(lambda: bool(game_pids(s)), s.launch_timeout, s.poll_interval):
        raise RunError(f"Xenonauts2.exe did not start within {s.launch_timeout} s")
    if load == "menu":
        menu_load(s)

    if not wait_for_log(
        s,
        lambda es: queued_save_path(es) is not None,
        s.launch_timeout + s.load_timeout,
    ):
        raise RunError("no 'Queued LoadGameCommand' line appeared; the save was never loaded")
    queued = queued_save_path(read_timing_entries(s))
    if not is_expected_save(queued, s.save_rel):
        raise RunError(f"wrong save loaded: expected {s.save_rel}, log shows {queued}")
    if not wait_for_log(s, lambda es: any(s.playable_marker in e.message for e in es), s.load_timeout):
        raise RunError(f"playable marker not reached within {s.load_timeout} s of the save being queued")
    for _ in range(warm_loads):
        warm_load(s)
    text = read_log(s)
    entries = read_timing_entries(s)
    stop_game(s)

    dest = s.logs_dir / run_name
    dest.mkdir(parents=True)
    for f in sorted(s.logs_dir.glob("output.log*")):
        shutil.move(f, dest / f.name)
    if s.markers_file.exists():
        shutil.move(s.markers_file, dest / s.markers_file.name)
    print(f"logs archived to {dest}")
    print(f"errors: {count_errors(text)}, state-loss: {count_state_loss(text, s.state_loss_pattern)}")
    loads = find_load_timings(entries, s.playable_marker)
    return loads


def format_seconds(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f} s"


def print_timings(t: Timings) -> None:
    print(f"queue to setup:      {format_seconds(t.queue_to_setup)}")
    print(f"queue to playable:   {format_seconds(t.queue_to_playable)}")
    print(f"intro to setup:      {format_seconds(t.intro_to_setup)}")
    print(f"lose focus to setup: {format_seconds(t.lose_focus_to_setup)}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run one cold measurement run of Xenonauts 2.")
    parser.add_argument("run_name")
    parser.add_argument("--load", choices=["auto", "menu"], default="auto")
    parser.add_argument(
        "--warm-loads",
        type=int,
        default=0,
        help="reload the warm save N times in the same session after the first load",
    )
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
    timings: list[Timings] | None = None
    try:
        timings = perform_run(s, args.run_name, args.load, args.warm_loads)
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
            failure = (failure + "; " if failure else "") + "config files modified: " + ", ".join(str(p) for p in modified)

    if failure:
        print(f"error: {failure}", file=sys.stderr)
        return 1
    assert timings is not None
    for i, t in enumerate(timings):
        print(f"load {i + 1} ({'cold' if i == 0 else 'warm'})")
        print_timings(t)
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    sys.exit(main(sys.argv[1:]))

# GOG install via Minigalaxy

Xenonauts 2 can also run from the GOG build, installed and launched through Minigalaxy. The GOG build is Windows-only, so Minigalaxy runs it under the Wine bundled in its Flatpak. The Steam install is unchanged and still works.

## Minigalaxy

| Item | Value |
| --- | --- |
| Flatpak ref | `io.github.sharkwouter.Minigalaxy` (stable, x86_64) |
| Version | 1.4.1 |
| Origin | `flathub` |
| Installation | user (`flatpak install --user`) |
| Runtime | `org.gnome.Platform//48` |
| Wine | `/app/bin/wine` inside the sandbox (`custom_wine` in the per-game config) |
| Launch | `flatpak run --branch=stable --arch=x86_64 --command=minigalaxy io.github.sharkwouter.Minigalaxy` (the start menu entry runs the same command) |

Install:

```bash
flatpak install --user -y flathub io.github.sharkwouter.Minigalaxy
```

Minigalaxy only lists Linux games unless "Show Windows games" is on (`show_windows_games` in its config). It is on here.

## Paths

| What | Path |
| --- | --- |
| Install dir | `/media/gog/Xenonauts 2` |
| Wine prefix | `/media/gog/Xenonauts 2/prefix` |
| User data (Mods, Saves, Logs, Settings) | `/media/gog/Xenonauts 2/prefix/drive_c/users/<wine-user>/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2` |
| Minigalaxy config | `~/.var/app/io.github.sharkwouter.Minigalaxy/config/minigalaxy/config.json` |
| Per-game config | `~/.var/app/io.github.sharkwouter.Minigalaxy/config/minigalaxy/games/Xenonauts 2.json` |
| GOG product id | `1412583633` (`goggame-1412583633.info` in the install dir) |

`<wine-user>` is the host login name, not `steamuser` as in the Steam prefix. The game sees the install dir as `c:\game`, so the game process is `c:\game\Xenonauts2.exe` under `C:\windows\system32\start.exe`.

The Flatpak only has access to `~/GOG Games`. The install dir is outside that, so `install_dir` in the config points at a document-portal path that maps to `/media/gog`. If Minigalaxy cannot write there, grant it with `flatpak override --user --filesystem=/media/gog io.github.sharkwouter.Minigalaxy`.

## Differences from the Steam install

- The Wine prefix lives inside the install dir, so the user data is under the install dir, not under a separate `compatdata` tree.
- Paths in `Settings/contentpacks.json` for mods use the Wine user: `C:/users/<wine-user>/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2/Mods/<mod>`. The Steam copy uses `C:/users/steamuser/...`, so entries cannot be copied between the two files unchanged.
- There is no Steam Workshop content and no `steam_autocloud.vdf`.
- The game logs to `Player.log` and `Logs/output.log` in the user data dir. There is no Steam console log, so the start detection in `scripts/run.py` that reads `STEAM_CONSOLE_LOG` does not apply.

## Migrating saves and mods from Steam

Copy `Saves` (without `steam_autocloud.vdf`) and `Mods` from the Steam user data dir into the GOG user data dir, then add the mod entries to the GOG `Settings/contentpacks.json` with the Wine-user path above and `"Enabled": true`. Keep the UTF-8 BOM at the start of the file.

```bash
rsync -a --exclude steam_autocloud.vdf "<steam-user-data>/Saves/" "<gog-user-data>/Saves/"
rsync -a "<steam-user-data>/Mods/" "<gog-user-data>/Mods/"
```

## Verified launch

Launched Minigalaxy from the start menu command above, opened the Installed view, and clicked Play on Xenonauts 2. The game loaded to the main menu (Full Release 7.27.11), and Load Game listed the migrated saves. The mods are enabled in `contentpacks.json`. Exit Game closed the game and left no `Xenonauts2.exe` process.

The display is only reachable through the KVM (see `CLAUDE.local.md`), so the launch was driven by mouse events on the remote screen. `xdotool` is not installed.

A cursor resting on a HUD item (for example Exit Game) keeps its tooltip open, and hovering many HUD items changes which element the game treats as focused. Move the pointer off the HUD before the next click or screenshot.

## Automated runs

`scripts/run.py` runs the GOG build unattended with `BUILD=gog`, launching through Minigalaxy's Wine command and clicking with `ydotool` on the KDE Wayland session. See [Automated cold runs](automated-runs.md#gog-build-and-kde-wayland).

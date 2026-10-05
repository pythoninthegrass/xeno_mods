# Copy Xenonauts 2 to another Mac

Copies Xenonauts 2 (Steam app `538030`) from one Mac's CrossOver bottle to another's over SSH, without moving the whole bottle. The target machine needs a CrossOver bottle with Steam already installed and logged in once.

## What gets copied

All paths are relative to the bottle's `drive_c`.

| Path | Contents | Size |
| --- | --- | --- |
| `Program Files (x86)/Steam/steamapps/common/Xenonauts2/` | Game files | about 7 GB |
| `Program Files (x86)/Steam/steamapps/appmanifest_538030.acf` | Steam's record that the game is installed | tiny |
| `users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2/` | `Saves/`, `Settings/`, `Mods/` and logs | small |

The third path holds the mods and saves. Skip it to start the target with a clean profile.

## Preconditions

- Steam is installed in the target bottle and has been logged into once, so `steamapps` exists.
- Steam and CrossOver are closed on both machines.
- Steam Cloud is disabled for Xenonauts 2, or the first launch shows an "Unable to Sync" dialog (see [automated-runs.md](automated-runs.md)).
- `rsync` 3.x is installed on the machine you copy from. The `rsync` bundled with macOS (`openrsync`) does not handle remote paths with spaces the same way.

## Commands

Run these on the machine that has the game. Set `REMOTE` to the SSH host of the target and `BOTTLE` to the bottle name on both machines.

```bash
REMOTE=<remote>
BOTTLE=Steam

SRC=~/Library/Application\ Support/CrossOver/Bottles/$BOTTLE/drive_c
DST="Library/Application Support/CrossOver/Bottles/$BOTTLE/drive_c"
APPS='Program Files (x86)/Steam/steamapps'
DATA='users/crossover/AppData/LocalLow/Goldhawk Interactive/Xenonauts 2'

ssh "$REMOTE" "mkdir -p \"$DST/$APPS/common\" \"$DST/$DATA\""

rsync -aP "$SRC/$APPS/common/Xenonauts2" "$REMOTE:$DST/$APPS/common/"
rsync -aP "$SRC/$APPS/appmanifest_538030.acf" "$REMOTE:$DST/$APPS/"
rsync -aP "$SRC/$DATA/" "$REMOTE:$DST/$DATA/"
```

Add `-n` to each `rsync` to preview what would be copied. Rerunning the commands sends only what changed, and an interrupted copy resumes.

## Notes

- The `mkdir -p` step exists because `openrsync` on the target has no `--mkpath`.
- On first launch Steam sees the manifest and either lists the game as installed or verifies the files, instead of downloading it again.
- `users/crossover` is the default Wine user in a CrossOver bottle. Check the bottle's `drive_c/users/` if the target uses a different name.

## Alternative: whole bottle

Use this to clone everything, including Steam itself. Expect a large transfer, because a bottle with Steam and a few games is tens of gigabytes.

```bash
CX=/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/cxbottle

# archive, copy and restore
$CX --bottle "$BOTTLE" --tar ~/$BOTTLE.cxarchive
rsync -avP ~/$BOTTLE.cxarchive "$REMOTE:~/"
ssh "$REMOTE" "$CX --restore ~/$BOTTLE.cxarchive"
```

Alternatively, rsync the bottle directory itself, then run `ssh "$REMOTE" "$CX --bottle $BOTTLE --restored"` so CrossOver registers it. The archive is gzipped, which saves little on game assets that are already compressed, so rsyncing the directory is usually faster.

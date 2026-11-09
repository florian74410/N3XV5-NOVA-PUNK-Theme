# NEXUS HUD 3.2.1 — Gaming Sleep / XFCE panel restoration

Development branch: `work/nexus-v3.2.1-gaming-panel-settings`.

This branch **includes the complete 3.1.8.3 source baseline** under
`Releases/NEXUS-3.1.8.3-STABLE/Source/` and builds the full 3.2.1 source by
applying the 3.2 and 3.2.1 stages in sequence. The stable 3.1.8.3 baseline
and the 3.2.0 installation are not modified.

## Changes since 3.2.0

- Settings → **GÉNÉRALE** → **MODE GAMING / VEILLE**:
  enable or disable Dolphin-triggered sleep, persisted as `game_sleep_enabled`
  in `~/.config/nexus-v3-hybrid/n3xvs-unified.json`.
- When Dolphin triggers sleep, the watcher snapshots the original XFCE
  panel window IDs before NEXUS exits. It then remaps those original
  windows, verifies visibility and uses `xfce4-panel --restart` as a
  last resort if an original panel was recorded but failed to restore.
- No changes to the animations, FPS, Holo, metrics, Blue Neon styling,
  or hardware polling; watcher polling remains 2 seconds.
- On disabling the setting while Dolphin is open, the watcher wakes
  NEXUS when it next checks the preference.

## Upgrade on XFCE X11

Run these two commands **from an XFCE X11 terminal, with Dolphin closed**:

```bash
git clone --depth 1 --branch work/nexus-v3.2.1-gaming-panel-settings \
  https://github.com/florian74410/N3XV5-NOVA-PUNK-Theme.git \
  ~/Téléchargements/NEXUS-3.2.1-DEV
bash ~/Téléchargements/NEXUS-3.2.1-DEV/App/Core/GamingSleep/install_v321.sh install
```

The installer requires the existing `~/.local/share/nexus-320-full` with
`3.2.0-GAMING-SLEEP-TEST` and an existing compatible virtualenv.
It creates `~/.local/share/nexus-321-full`, a separate launcher,
a session watcher service and a new XFCE autostart entry.

### Rollback

```bash
bash ~/Téléchargements/NEXUS-3.2.1-DEV/App/Core/GamingSleep/install_v321.sh rollback
```

The complete source archive is assembled in CI by
`.github/workflows/nexus-321-full-build.yml`, and uploaded as an Actions artifact
after a successful build. This is a test release, not yet a verified
hardware-integrated stable release.

### Manual acceptance tests

1. Enable gaming sleep in General; close Dolphin, confirm NEXUS Top and Bottom.
2. Open Dolphin; NEXUS exits and the native bottom XFCE panel must appear.
3. Exit Dolphin; NEXUS restarts exactly once.
4. Disable gaming sleep in General, launch Dolphin again; NEXUS must remain.
5. Close/open Dolphin rapidly and repeat; no duplicated panels, no loss of
   terminal access.
6. Reboot XFCE X11 and check service and panel recovery.

Logs: `~/.local/state/nexus-321/logs/nexus.log`;
`journalctl --user -u nexus-321-gaming.service -n 100 --no-pager`.

**Known limitation:** the watcher service requires a valid graphical session
environment (DISPLAY and X11 authentication); validate reboot behavior on
the user's actual XFCE machine before promoting to stable.

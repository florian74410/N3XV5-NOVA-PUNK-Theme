# NEXUS HUD 3.2.2 — Gaming Bottom Only (XFCE X11 TEST)

This full build is in `Releases/NEXUS-3.2.2-FULL/Source` and is based on 3.2.1.
The stable 3.1.8.3 and older 3.2 builds are kept separately.

## Gaming behavior
- Dolphin opens: hide only the **NEXUS TopBar**; leave its existing Qt **Navbar Bottom** visible.
- Dolphin closes: show the TopBar again (NEXUS remains in the same process).
- Settings → **GÉNÉRALE → MODE GAMING / VEILLE**: switch enables/disables this behavior.
- No `xfce4-panel --restart`, XFCE panel recovery, NEXUS exit, or new NEXUS process while gaming.
- Signals: SIGUSR1 (TopBar hidden), SIGUSR2 (TopBar shown), sent only to the exact staged Qt process.
- Uses the existing animation / visual pipeline unchanged.

## Installation on Linux Mint XFCE

Close Dolphin before upgrading, then run:

```bash
git clone --depth 1 -b work/nexus-v3.2.2-gaming-bottom-only \
  https://github.com/florian74410/N3XV5-NOVA-PUNK-Theme.git \
  "$HOME/Téléchargements/NEXUS-3.2.2-DEV"
bash "$HOME/Téléchargements/NEXUS-3.2.2-DEV/App/Core/GamingSleep/install_v322.sh" install
```

Creates `~/.local/share/nexus-322-full` and `~/.local/bin/nexus-322`.
Keeps original 3.2 and 3.2.1 files.

### Rollback

```bash
bash "$HOME/Téléchargements/NEXUS-3.2.2-DEV/App/Core/GamingSleep/install_v322.sh" rollback
```

## Tests to complete on real XFCE X11

1. Confirm TopBar + Navbar Bottom are visible.
2. Open Dolphin; TopBar disappears, Navbar Bottom stays, icons remain clickable.
3. Close Dolphin; TopBar reappears with no process restart.
4. Disable gaming in General; opening Dolphin no longer hides the TopBar.
5. Re-enable gaming; test a second Dolphin cycle.
6. Check no duplicate NEXUS or native XFCE panels.

Logs: `journalctl --user -u nexus-322-gaming.service -n 80 --no-pager`.

This is a **test** build until validated on the user's session.

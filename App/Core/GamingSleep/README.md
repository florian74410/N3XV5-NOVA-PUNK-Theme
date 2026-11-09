# NEXUS 3.2 — Gaming Sleep Mode (development preview)

**DO NOT deploy to Macro yet.** This is the development branch, not a stable build.

## Goal
Automatically detect Dolphin, stop NEXUS graphical effects/telemetry, restore the original XFCE panel during play, then restore NEXUS after Dolphin exits. The user does not want any permanent reduction in NEXUS rendering quality.

## Current implementation
- Minimal Python standard-library process watcher with exact command-name matching (2-second polling).
- Debounced sleep/wake state machine; handles orderly watcher termination.
- Dry-run preview and fail-safe configuration (all desktop mutations disabled by default).
- Does **not** yet implement/claim tested XFCE or healthbar state management.

## Blocking issue — exact 3.1.8 baseline
The repository's main branch contains earlier N3XV5 code, **not the verified full installed Macro NEXUS 3.1.8**.
Do not label this earlier source as 3.1.8 or publish a stable tag until a validated snapshot of:
`~/.local/share/nexus-318-full`, `~/.local/bin/nexus-318`, relevant systemd/autostart entries and installation metadata
has been captured from Macro, compared with the running installation, audited for secrets and then committed to a release source tree.

## Safe dry-run setup
```bash
mkdir -p ~/.config/nexus-318
cp App/Core/GamingSleep/config.example.json ~/.config/nexus-318/gaming-sleep.json
python3 App/Core/GamingSleep/gaming_sleep.py --dry-run
```
Before enabling real actions, implement an adapter that cooperates with the existing `healthbar` XFCE restore mechanism. Do not kill processes with generic `pkill -f`; avoid duplicate panels. Implement idempotent sleep/wake commands, preserve NEXUS preferences, provide manual recovery and verify X11/Qt workareas.

## Acceptance tests required
1. Cold start with Dolphin absent: NEXUS unchanged.
2. Dolphin launch: one transition to real XFCE panels, zero NEXUS animation/metrics workers.
3. Dolphin exit: one transition back to original NEXUS 3.1.8 state.
4. Rapid Dolphin relaunch, game crash, watcher crash/restart, logout/login, manual recovery.
5. Compare FPS, CPU/RAM and thermals on Intel HD 3000; check no duplicate bars.
6. Validate installer update and rollback to exact stable 3.1.8.

Nothing here is a release of 3.2. A draft PR is appropriate until validated on Macro.

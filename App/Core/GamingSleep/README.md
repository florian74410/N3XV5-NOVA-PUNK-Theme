# NEXUS 3.2 Gaming Sleep Mode — TEST (Macro / XFCE X11)

This branch contains the imported exact 3.1.8.3-FULL baseline under
`Releases/NEXUS-3.1.8.3-STABLE/Source/`. The **stable source remains unchanged**.
Production on Macro must not be overwritten during development.

## Architecture

- `stage_v32.py`: copy the 3.1.8.3-FULL source to a **new** staging tree, validate the entry point and inject a minimal Qt bridge. Never writes to the source tree.
- `qt_bridge.py`: on SIGUSR1, a 200ms Qt timer calls `QApplication.quit()`, which triggers `bar.close()`; this closes Bottom Dock and invokes its existing `NativePanelGuard.restore()`. No style, particle or settings changes.
- `watcher_v32.py`: independent low-cost process watcher checks for Dolphin every 2 seconds. Requests graceful exit of the verified **3.2 staged** Qt process, tracks that it stopped NEXUS, and relaunches the 3.2 staged launcher after Dolphin exits. Doesn't call xfce4-panel itself or touch the production 3.1.8.3 process.
- `config.v32.example.json`: disabled by default.

## Stage / syntax test — no desktop changes

```bash
python3 App/Core/GamingSleep/stage_v32.py \
  --source Releases/NEXUS-3.1.8.3-STABLE/Source \
  --dest /tmp/nexus-320-test
python3 -m py_compile /tmp/nexus-320-test/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py
```

The actual test launcher must set the **staged** tree root, existing compatible PySide6 venv, X11 display, and `HEALTHBAR_DATA_DIR` pointing to a separate 3.2 test profile. Set `launcher` in JSON accordingly. The stable 3.1.8.3 autostart must not be changed.

## Known limitations / release blockers

1. No integrated Qt Settings UI toggle yet.
2. No installation or rollback package yet; watcher is not enabled or installed.
3. Actual XFCE restoration and watcher recovery must be validated on Macro.
4. Dolphin identification needs validation with actual `/proc/*/cmdline` on Macro.
5. No automatic stable deployment; before production promotion, add a user-level service and recovery CLI with single-instance locking.
6. `watcher_v32.py` requires that NEXUS be started from staged source and its patched Qt bridge be active. Never enable watcher against unpatched 3.1.8.
7. A second running 3.1.8 instance can interfere with 3.2 testing. Only perform graphical integration tests from a safe XFCE session with backup and recovery procedures.

## Acceptance tests
- No Dolphin: no transition.
- Dolphin started: exactly one graceful NEXUS stop; XFCE original panel returns.
- Dolphin exits: staged NEXUS restarts with unchanged appearance.
- Crash and rapid relaunch, watcher shutdown/startup, logout, game closure; no duplicated panel.
- CPU/GPU usage measured against stable baseline.

Until these tests pass, PR remains draft and installation is opt-in only.

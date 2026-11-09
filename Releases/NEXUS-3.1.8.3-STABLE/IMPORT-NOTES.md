# Snapshot NEXUS 3.1.8.3-FULL — Macro (baseline pending import)

The installed source archive from Macro was inspected on 2026-11-09:

- 259 regular files and 33 directories (tar.gz roughly 7.8 MiB).
- Actual version in `VERSION.txt`: **3.1.8.3-FULL**.
- Launcher: `~/.local/bin/nexus-318`.
- Application: `~/.local/share/nexus-318-full/`.
- XFCE autostart: `~/.config/autostart/nexus-318.desktop`.
- Entry point: `App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py`.
- `healthbar.desktop_backend.NativePanelGuard` hides the original XFCE panel and starts a separate restoration watchdog. A safe gaming transition must use (or cooperate with) that mechanism.
- Excluded local .venv, runtime logs, session configs, Git data; those are not present in the tarball.

**Important: this document is not the source snapshot.** The exact extracted 3.1.8.3 tree must be imported before labelling a release stable or tagging it. Never promote the older `main` source as this version. Preserve file contents, binary artwork and executable bits during import.

## Safe acceptance gate
- Import sanitized source tree under `Releases/NEXUS-3.1.8.3-STABLE/`, including the actual launcher and autostart file in a `packaging/` subfolder.
- Review any personal paths or credentials before publishing.
- Compare source hashes with unpacked tar archive.
- Restore/run on Macro in a disposable install path without overwriting 3.1.8.3.
- Confirm that a process exit restores XFCE panels and no duplicate panels appear.
- Only then create a release tag and begin testing the Gaming Sleep Mode integration.

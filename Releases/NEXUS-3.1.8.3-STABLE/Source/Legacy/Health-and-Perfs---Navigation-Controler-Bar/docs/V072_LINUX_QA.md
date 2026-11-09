# NovaBar / Cyber-Neon Interactif 0.7.2 — Linux QA

This is an **isolated rebuilt Cyber-Neon branch** based on the visual identity of 0.6.11. The repository's historic GitHub tag `v0.7.2` belongs to an older release and **MUST NOT be overwritten**. Distribute this version as a CI artifact until a new unique, traceable release channel is established.

## Installation on Linux Mint XFCE (X11)

1. Keep a local copy of the current 0.7.0 installer and back up user settings.
2. Download the new `NovaBar_0.7.2_amd64.deb` from the **successful** run of GitHub Actions: `NovaBar 0.7.2 Cyber-Neon Linux Desktop QA`.
3. Verify the artifact hash against the same build's `sha256sum` CI output. Copy `.deb` to a world-readable temporary directory to avoid APT's `_apt` warning.
4. Close the running NovaBar via its tray icon or Ctrl+Q. Do not kill the native XFCE panel.
5. Run `sudo install -m 644 NovaBar_0.7.2_amd64.deb /tmp/NovaBar_0.7.2_amd64.deb && sudo apt install /tmp/NovaBar_0.7.2_amd64.deb`.
6. Start with `/usr/bin/novabar`; examine General, Themes, Extensions, 1-second top reveal, 3+N bottom tabs, and Polkit Turbo prompts.

No hardware control without an explicit user action. The privileged helper is at `/usr/libexec/novabar-turbo-helper`, root-owned by dpkg. It accepts only the fixed arguments `on` or `off` and manipulates only Linux kernel CPU boost switches.

## Acceptance checks

- Settings: proper glass/nav geometry and backdrop (no native gray). All new controls survive a restart.
- Top: no X button, continues showing collapsed content, only reveals after continuous hover in user-configured 10-px strip (default: 1000 ms).
- XFCE/X11: normal maximized windows respect the EWMH reserved region above/below; test both collapsed/expanded states, then 2 workspaces.
- Bottom: 62–130 px configurable; 1–3 visible window buttons and a `+N` menu showing *every* remaining window.
- Turbo: NORMAL in cyan; TURBO in red; Polkit password/cancellation must preserve actual CPU state.
- Application exit: original XFCE panel restored and workarea struts removed.
- Resource use: compare CPU/RAM at idle, collapsed, and while navigating.

## Compatibility notes

X11 `_NET_WM_STRUT_PARTIAL` only reserves space at the outer root-screen edges. It is a window-manager request (not a global display resize), so Wayland and some multi-monitor geometries need separate handling. Native XFCE panels are preserved; never overwrite `xfce4-panel.xml` as an update mechanism.

The in-app native updater only selects official releases carrying the explicit `cyber-neon-rebased-from-0.6.11` lineage marker; historic 0.7.1–0.7.5 releases cannot be offered for this rebuilt line.

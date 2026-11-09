# NovaBar / NOVA NEXUS HD 0.8.0 — Linux QA

Branch: `work/novabar-v0.8.0-holo-cyber-pcb`

This is a **full Linux desktop QA build**, not yet a certified stable release.

## Major visual changes

- Holo CPU now names the actual CPU model (if Linux /proc/cpuinfo exposes it). Architecture is shown beneath; cores and threads precede temperature, frequency, load and measured package watts.
- RAM Holo shows detected physical DIMM count, capacity per module, and its *configured* SMBIOS speed when readable without privileged access. CAS latency and live DDR clocks remain unavailable rather than guessed.
- Fan Holo reports the exact count of exposed fan sensors, RPM and percentage **only** if a corresponding `fan*_max` exists. The header distinguishes motherboard temperature from CPU temperature, and indicates read-only Turbo state.
- Network Holo lists only interfaces where the kernel reports `isup=True`, with Wi-Fi, LAN or Bluetooth-identifying title.
- The original segmented dials now use a blue/green/orange/red progression; the fan dial doesn't print a duplicate RPM in its center.
- RAM/SSD battery silhouettes were replaced with 12 connected PCB LED capacity cells.
- Bottom navigation is an X11 overlay and **no longer reserves screen height**. `Générale → Transparence de navigation basse` configures glass fill from 10 to 100 percent.
- Settings' backdrop uses individually routed asymmetrical PCB traces, vias, glass reflection and existing neon cut corners, without a perpetual animation timer.

## Hardware limitations

The system must not infer power from CPU TDP or calculate a per-core wattage by dividing package power. Intel RAPL may report true package consumption where the kernel permits access. DIMM clocks are not sampled live from SMBIOS; SMBIOS provides configured transfer speeds. Hardware devices whose interfaces do not expose read-only information show em dash (`—`) rather than fictional telemetry.

## Safe Linux test

1. Back up existing settings and keep a copy of the previous installer.
2. Obtain the `NovaBar-0.8.0-HOLO-PCB-LINUX-QA` artifact **from a successful run** of GitHub Actions workflow `NovaBar 0.8.0 Holo and PCB Linux QA`. Do **not** reuse an older CI run's Debian package after new commits.
3. Verify the package SHA-256 against the corresponding GitHub Actions log output.
4. Quit NovaBar using its tray menu or Ctrl+Q, allowing XFCE panel restoration.
5. Run `sudo install -m 644 NovaBar_0.8.0_amd64.deb /tmp/NovaBar_0.8.0_amd64.deb && sudo apt install /tmp/NovaBar_0.8.0_amd64.deb`.
6. Launch with `/usr/bin/novabar`; inspect the Holo modules by clicking their top HUD slots.
7. Confirm bottom navigation overlaps maximized windows, without changing their size, across at least two workspaces. Verify changing opacity from Settings survives restart.
8. Check CPU, RAM, SSD, fans and Wi-Fi names and unavailable values on the actual machine.
9. Measure CPU%/RSS at rest with the bars open, collapsed and during animations.
10. On failure, quit normally and reinstall your saved 0.7.2 package with `sudo apt install --allow-downgrades /path/to/NovaBar_0.7.2_amd64.deb`.

Do not mark this branch STABLE before XFCE/X11 and real hardware QA. In-app updates require a matching official manifest lineage; a CI artifact by itself is not an in-app update.

# NovaBar v0.3.4 — Neon + safe upgrade

## Visual direction
Use the existing *real neon preview* (`docs/novabar-neon-preview.png`) as the
reference, NOT the speculative wide mockup. Slim default remains **72 px**,
allowed range **50–150 px**, pinned to the screen edge at 100% length by default.
Only the upper glass reflection, subtle traveling energy trace and hover glow
are enhanced. No plugin dimensions, telemetry labels or core values are invented.
`docs/novabar-normal-holo-neon.svg` is an illustrated two-state preview.

## Safe upgrade sequence
1. Detect installed runtime from `installation.json`; refuse downgrades.
2. Keep the previous executable untouched while extracting/building the new one.
3. Execute the **new** runtime's isolated `--self-test --expect-version`.
4. Switch shortcuts, autostart and active-version metadata only after success.
5. Remove **only lower-version, non-symlink directories** immediately inside
   `install_root()/versions` after successful activation.
6. Leave any locked Windows executable in place, report that cleanup is deferred.
   No recursive scan of user-owned locations is permitted.

This order intentionally prioritizes recoverability over removing the old runtime
before a new version has been proven functional.

### User data preserved
`Documents/NovaBar`, `App/Profiles`, `Plugins`, `plugin_sources.json`,
theme assets, local preferences, and non-runtime custom folders are not deleted.
The same Windows Inno Setup AppId upgrades the *installer launcher* in place;
the installer closes old app processes when Windows permits it. On Linux, previously
downloaded `.run` files remain in the user's Downloads folder and are never
silently deleted.

### Limitations
Only the CPU module currently provides a native Holo panel, and it requires
the corresponding compatible CPU Manager plugin. Tests run with mock files plus
the native CI matrix; manual desktop validation is still required on XFCE,
multi-monitor DPI, Win10/11 and modern macOS.

"""OS session launchers, scoped to the current user; never needs root."""
import os
import plistlib
import subprocess
import sys
from pathlib import Path


def launch_command():
    # An activated user update takes precedence over an inherited DEB/Flatpak marker.
    if getattr(sys,"frozen",False):
        from .install_engine import read_installed_state
        state=read_installed_state()
        if state and Path(state.get("executable","")).resolve()==Path(sys.executable).resolve():
            return [sys.executable]
    # Desktop package paths remain stable across system package upgrades.
    if os.getenv("NOVABAR_PACKAGED") == "deb":
        return ["/usr/bin/novabar"]
    if os.getenv("NOVABAR_PACKAGED") == "flatpak":
        return ["flatpak", "run", "io.github.florian74410.NovaBar"]
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "healthbar"]


def desktop_quote(value):
    # Desktop Entry Exec is not shell syntax; escape reserved characters explicitly.
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def set_enabled(enabled, command=None):
    command = command or launch_command()
    if sys.platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                            winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, "HealthPerfsBar", 0, winreg.REG_SZ,
                                 subprocess.list2cmdline(command))
            else:
                try:
                    winreg.DeleteValue(key, "HealthPerfsBar")
                except FileNotFoundError:
                    pass
    elif sys.platform == "darwin":
        target = Path.home() / "Library/LaunchAgents/com.healthperfs.bar.plist"
        if enabled:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(plistlib.dumps({"Label": "com.healthperfs.bar",
                "ProgramArguments": command, "RunAtLoad": True,
                "ProcessType": "Interactive"}))
        else:
            target.unlink(missing_ok=True)
    else:
        target = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "autostart/health-perfs-bar.desktop"
        if enabled:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("[Desktop Entry]\nType=Application\nName=Health & Perfs Bar\nExec="
                + " ".join(map(desktop_quote, command))
                + "\nTerminal=false\nX-GNOME-Autostart-enabled=true\n", encoding="utf-8")
        else:
            target.unlink(missing_ok=True)

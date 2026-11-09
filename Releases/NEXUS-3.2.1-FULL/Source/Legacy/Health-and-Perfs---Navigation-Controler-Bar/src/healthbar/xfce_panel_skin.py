"""Optional, reversible Cyber Nexus skin for the existing Xfce 4 panel.

The panel is NEVER replaced: every original launcher, tray icon, plugin and
shortcut stays owned by xfce4-panel. We only add a clearly delimited GTK 3 CSS
block and change the selected panel's native auto-hide setting, with backup.
No panel thickness, position, plugin-ids or launcher list is modified.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config import data_dir
from .system_env import native_env

START = "/* NOVABAR CYBER NEXUS PANEL SKIN BEGIN (managed) */"
END = "/* NOVABAR CYBER NEXUS PANEL SKIN END (managed) */"
PALETTES = {
    "blue-neon": ("#18dfff", "#1765bc", "24, 220, 245"),
    "cyber-futuriste": ("#18dfff", "#1765bc", "24, 220, 245"),
    "green-matrix": ("#43fa9a", "#137d59", "67, 250, 154"),
    "red-blood": ("#ff607d", "#96254e", "255, 96, 125"),
    "redblack-0822": ("#FF2647", "#80122A", "255, 38, 71"),
}
BOTTOM_POSITIONS = {4, 8, 10, 12}


def gtk_css_path():
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home()/".config"))) / "gtk-3.0/gtk.css"


def backup_path():
    return data_dir() / "xfce-panel-original.json"


def available():
    """Only native X11/Xfce sessions. Unsupported desktop remains unchanged."""
    return (sys.platform.startswith("linux") and bool(os.environ.get("DISPLAY"))
            and os.environ.get("XDG_SESSION_TYPE", "x11").lower() != "wayland"
            and shutil.which("xfconf-query") is not None
            and shutil.which("xfce4-panel") is not None)


def _query(*arguments):
    try:
        response = subprocess.run(
            ["xfconf-query", "-c", "xfce4-panel", *arguments],
            check=False, capture_output=True, text=True, timeout=2, env=native_env())
        if response.returncode:
            return None
        return response.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None


def bottom_panel_id():
    """Find a bottom-anchored XFCE panel without presuming panel-0/panel-1."""
    output = _query("-lv")
    if not output:
        return None
    options = []
    for line in output.splitlines():
        match = re.match(r"^/panels/panel-(\d+)/position\s+[\"\']?p=(\d+);", line.strip())
        if match and int(match.group(2)) in BOTTOM_POSITIONS:
            options.append(int(match.group(1)))
    return min(options) if options else None


def _property(panel_id, name):
    return f"/panels/panel-{panel_id}/{name}"


def panel_setting(panel_id, name):
    return _query("-p", _property(panel_id, name))


def _set_panel_setting(panel_id, name, value):
    prop = _property(panel_id, name)
    try:
        command = ["xfconf-query", "-c", "xfce4-panel", "-p", prop, "-s", str(value)]
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=2, env=native_env())
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def render_css(theme="blue-neon", delay_seconds=10):
    primary, secondary, rgb = PALETTES.get(theme, PALETTES["blue-neon"])
    ms = max(1000, min(120000, int(delay_seconds)*1000))
    # Native XFCE panel remains intact: only the existing managed stylesheet is changed.
    redblack=theme=="redblack-0822"
    pane_bg="7, 5, 9" if redblack else "4, 13, 27"
    pane_lower="5, 4, 8" if redblack else "3, 13, 27"
    button_bg="22, 7, 13" if redblack else "3, 17, 33"
    return f"""{START}
/* XFCE retains all launchers, Wi-Fi, notifications, tasklist and system tray.
   Only the shell/background/buttons are retinted. Never touch plugin-ids.
   XFCE GTK CSS popdown delay is expressed in milliseconds. */
#XfcePanelWindow {{
  -XfcePanelWindow-popup-delay: 150;
  -XfcePanelWindow-popdown-delay: {ms};
  /* Almost entirely hidden; keep a 1px native edge for mouse reveal. */
  -XfcePanelWindow-autohide-size: 1;
}}
.xfce4-panel.background {{
  background-color: rgba({pane_bg}, 0.95);
  background-image: linear-gradient(to bottom,
    rgba({rgb}, 0.28), rgba({pane_bg}, .99) 13%,
    rgba({pane_lower}, .97) 38%, rgba(1, 4, 7, .98) 80%,
    rgba({rgb}, .25));
  border-style: solid;
  border-width: 1px 0 2px 0;
  border-color: {secondary};
  box-shadow: inset 0 2px rgba({rgb}, .45), inset 0 -2px rgba({rgb}, .32);
  color: #ebfaff;
}}
.xfce4-panel.background button {{
  color: #e3f6ff;
  border: 1px solid rgba({rgb}, .22);
  border-radius: 5px;
  background-color: rgba({button_bg}, .72);
  background-image: none;
  box-shadow: inset 0 1px rgba({rgb}, .19);
  padding: 1px;
}}
.xfce4-panel.background button:hover {{
  border-color: {primary};
  background-color: rgba({rgb}, 0.28);
  box-shadow: inset 0 0 7px rgba({rgb}, 0.48);
}}
.xfce4-panel.background button:checked {{
  background-color: rgba({rgb}, 0.22);
  border-color: {secondary};
  box-shadow: inset 0 0 8px rgba({rgb}, .25);
}}
/* Native tasklist buttons still own their original icons and click handlers. */
.xfce4-panel.background .tasklist button {{
  border-radius: 3px;
  border-color: rgba({rgb}, .35);
  background-image: linear-gradient(to bottom, rgba({rgb}, .15), rgba(2,11,25,.9));
}}
.xfce4-panel.background .tasklist button:checked {{
  border-color: {primary};
  background-image: linear-gradient(to bottom, rgba({rgb}, .31), rgba(3,29,43,.90));
  box-shadow: inset 0 0 9px rgba({rgb}, .24);
}}
{END}"""


def with_managed_block(original, block):
    """Replace only our owned segment; never wipe existing user's GTK theme."""
    start, end = original.find(START), original.find(END)
    if (start == -1) != (end == -1):
        raise ValueError("Marqueur NovaBar GTK incomplet : aucune modification")
    if start != -1:
        if end <= start or original.count(START) != 1 or original.count(END) != 1:
            raise ValueError("Marqueurs GTK NovaBar ambigus : aucune modification")
        original = original[:start] + original[end+len(END):]
    result = original.rstrip("\n")
    if block:
        result = (result + "\n\n" if result else "") + block + "\n"
    elif result:
        result += "\n"
    return result


def _atomic_text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".novabar-tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def _reload_panel():
    """Panel restart only when GTK CSS changes: preserve every plugin and size."""
    try:
        subprocess.Popen(["xfce4-panel", "--restart"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def apply_skin(theme, delay_seconds=10, scale_percent=175):
    """Apply a reversible native-panel skin, preserving launcher/plugin configuration."""
    if not available():
        return False, "Habillage XFCE disponible uniquement sur une session XFCE X11."
    target = bottom_panel_id()
    if target is None:
        return False, "Aucun panneau XFCE ancré en bas détecté : rien n'a été modifié."
    if type(scale_percent) is not int or not 100 <= scale_percent <= 200:
        return False, "Épaisseur demandée hors limites (100 à 200 %)."
    if type(delay_seconds) is not int or not 1 <= delay_seconds <= 120:
        return False, "Délai de repli hors limites (1 à 120 secondes)."
    backup = backup_path()
    css_file = gtk_css_path()
    try:
        previous = css_file.read_text(encoding="utf-8") if css_file.exists() else ""
        next_css = with_managed_block(previous, render_css(theme, delay_seconds))
        saved = json.loads(backup.read_text(encoding="utf-8")) if backup.is_file() else None
    except (OSError, ValueError, TypeError):
        return False, "CSS ou sauvegarde incompatible : aucune modification effectuée."
    if saved is not None and saved.get("panel_id") != target:
        return False, "Le panneau XFCE a changé : restaurez d'abord l'ancien habillage."
    original_autohide = panel_setting(target, "autohide-behavior")
    original_size = panel_setting(target, "size")
    if original_autohide is None or original_size is None:
        return False, "Impossible de lire la configuration native du panneau XFCE."
    try:
        measured_size = int(original_size)
    except (ValueError, TypeError):
        return False, "Dimension du panneau XFCE invalide."
    if measured_size < 16 or measured_size > 192:
        return False, "Épaisseur de panneau hors plage de sécurité."
    if saved is None:
        saved = {"panel_id": target, "original_autohide": original_autohide,
                 "original_size": measured_size}
        try:
            _atomic_text(backup, json.dumps(saved, ensure_ascii=False, indent=2)+"\n")
        except OSError:
            return False, "Sauvegarde du panneau impossible : aucune modification."
    elif "original_size" not in saved:
        # Legacy NovaBar backup only saved auto-hide; older skins did not alter size.
        saved["original_size"] = measured_size
        try:
            _atomic_text(backup, json.dumps(saved, ensure_ascii=False, indent=2)+"\n")
        except OSError:
            return False, "Impossible d'ajouter la dimension originale à la sauvegarde."
    initial_size = int(saved["original_size"])
    if not 16 <= initial_size <= 192:
        return False, "Dimension originale invalide dans la sauvegarde."
    # Always compute from original size, never from the current modified panel.
    desired_size = min(initial_size * 2, max(initial_size, round(initial_size * scale_percent / 100)))
    if not _set_panel_setting(target, "autohide-behavior", 2):
        return False, "Impossible d'activer la rétractation native XFCE."
    if not _set_panel_setting(target, "size", desired_size):
        _set_panel_setting(target, "autohide-behavior", original_autohide)
        return False, "Impossible de régler l'épaisseur ; configuration précédente restaurée."
    try:
        if next_css != previous:
            _atomic_text(css_file, next_css)
            _reload_panel()
    except OSError:
        _set_panel_setting(target, "size", measured_size)
        _set_panel_setting(target, "autohide-behavior", original_autohide)
        return False, "Impossible d'installer le style GTK ; dimensions restaurées."
    return True, (f"Habillage XFCE actif · {desired_size} px · repli {delay_seconds}s "
                  "· bord de rappel natif 1 px.")



def remove_skin():
    """Restore pre-NovaBar panel auto-hide and remove only NovaBar GTK CSS."""
    backup = backup_path()
    if not backup.is_file():
        return False, "Aucune sauvegarde d'habillage XFCE à restaurer."
    try:
        info = json.loads(backup.read_text(encoding="utf-8"))
        panel = info["panel_id"]
        old_autohide = info["original_autohide"]
        old_size = info.get("original_size")
        css_file = gtk_css_path()
        previous = css_file.read_text(encoding="utf-8") if css_file.is_file() else ""
        updated = with_managed_block(previous, "")
        if not _set_panel_setting(panel, "autohide-behavior", old_autohide):
            return False, "Impossible de restaurer le repli original du panneau."
        if old_size is not None and not _set_panel_setting(panel, "size", old_size):
            return False, "Impossible de restaurer l'épaisseur du panneau."
        if updated != previous:
            _atomic_text(css_file, updated)
            _reload_panel()
        backup.unlink()
        return True, "Panneau XFCE restauré sans toucher à ses icônes."
    except (KeyError, OSError, ValueError, TypeError) as exc:
        return False, f"Restauration du panneau impossible : {exc}"

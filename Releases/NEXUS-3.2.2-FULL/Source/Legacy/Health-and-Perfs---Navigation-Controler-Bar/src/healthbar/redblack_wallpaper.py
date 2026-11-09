"""Safe, explicit, reversible XFCE wallpaper operation for REDBLACK.

Never alters desktop settings when the theme itself is selected: the user
must click the wallpaper apply button. We back up every affected property
before modifying it, preserving workspace/monitor identity.
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

PROPERTY = re.compile(r"^/backdrop/screen[0-9]+/monitor[^/]+/workspace[0-9]+/last-image$")
BACKUP = "redblack-wallpaper-backup.json"

def supported():
    return (sys.platform.startswith("linux") and bool(os.environ.get("DISPLAY"))
            and shutil.which("xfconf-query") is not None
            and "XFCE" in os.environ.get("XDG_CURRENT_DESKTOP","").upper())

def _xfconf(*args):
    from .system_env import native_env
    result=subprocess.run(["xfconf-query","-c","xfce4-desktop",*args],
                          text=True,capture_output=True,timeout=6,env=native_env(),check=False)
    if result.returncode:
        raise OSError((result.stderr or result.stdout or "XFCE wallpaper unavailable").strip())
    return result.stdout.strip()

def _properties():
    rows={}
    for line in _xfconf("-lv").splitlines():
        entry=line.strip().split(None,1)
        if len(entry)==2 and PROPERTY.fullmatch(entry[0]):
            rows[entry[0]]=entry[1].strip()
    return rows

def _render_wallpaper(path):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor,QImage,QPainter
    from PySide6.QtSvg import QSvgRenderer
    from .redblack_shell import ASSET_ROOT
    # Prefer the user's previously installed BlackRed Studio imagery.
    studio=data_dir()/"Themes"/"blackred-studio"/"wallpaper-blackred.webp"
    picture=None
    try:
        if studio.is_file() and studio.stat().st_size<20*1024*1024:
            test=QImage(str(studio))
            if not test.isNull():
                picture=test.scaled(1920,1080,Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                    Qt.TransformationMode.SmoothTransformation)
    except OSError:
        pass
    if picture is not None:
        left=max(0,(picture.width()-1920)//2)
        top=max(0,(picture.height()-1080)//2)
        picture=picture.copy(left,top,1920,1080)
        if not picture.save(str(path),"PNG"):raise OSError("Export REDBLACK impossible")
        return
    source=ASSET_ROOT/"wallpaper-redblack.svg"
    renderer=QSvgRenderer(str(source))
    if not renderer.isValid():raise OSError("Fond REDBLACK invalide")
    image=QImage(1920,1080,QImage.Format.Format_RGB32)
    image.fill(QColor("#030405"))
    painter=QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    if not image.save(str(path),"PNG"):raise OSError("Export REDBLACK impossible")

def apply_wallpaper():
    if not supported():
        raise OSError("Fond d'écran automatisé disponible uniquement sur XFCE/X11")
    values=_properties()
    if not values:raise OSError("Aucune propriété de fond XFCE disponible : aucun changement")
    root=data_dir();root.mkdir(parents=True,exist_ok=True)
    backup=root/BACKUP
    if not backup.exists():
        staging=backup.with_suffix(".tmp")
        staging.write_text(json.dumps({"version":1,"properties":values},ensure_ascii=False,indent=2),encoding="utf-8")
        staging.replace(backup)
    target=root/"Wallpapers"/"REDBLACK-0.8.2.2.png"
    target.parent.mkdir(parents=True,exist_ok=True)
    _render_wallpaper(target)
    updated=[]
    try:
        for key in values:
            _xfconf("-p",key,"-s",str(target))
            updated.append(key)
    except (OSError,subprocess.TimeoutExpired):
        for key in updated:
            try:_xfconf("-p",key,"-s",values[key])
            except (OSError,subprocess.TimeoutExpired):pass
        raise
    return str(target)

def restore_wallpaper():
    if not supported():raise OSError("Restauration automatique disponible uniquement sur XFCE")
    backup=data_dir()/BACKUP
    if not backup.is_file():raise OSError("Aucune sauvegarde REDBLACK du fond d'écran")
    record=json.loads(backup.read_text(encoding="utf-8"))
    props=record.get("properties",{})
    if record.get("version")!=1 or not isinstance(props,dict):
        raise ValueError("Sauvegarde de fond d'écran invalide")
    for prop,value in props.items():
        if not PROPERTY.fullmatch(prop) or not isinstance(value,str):
            raise ValueError("Propriété de sauvegarde invalide")
    for prop,value in props.items():
        _xfconf("-p",prop,"-s",value)
    backup.unlink()
    return len(props)

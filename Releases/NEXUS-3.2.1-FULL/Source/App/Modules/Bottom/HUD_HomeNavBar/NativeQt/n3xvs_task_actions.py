# NEXUS_V31_MENU_DIVIDERS
"""N3XV5 2.4.6 - XFCE/X11 native contextual task actions.

Only touches the BottomDock task context menu; the original left-click
activation/minimize and animated TaskButton paint routine remain intact.
No privileged operations and no arbitrary command execution.
"""
from __future__ import annotations

import configparser
import os
from pathlib import Path
import re
import shutil
import subprocess

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QMessageBox


def _open_x():
    from Xlib import display
    return display.Display()


def _prop(d, w, name):
    p = w.get_full_property(d.intern_atom(name), 0)
    return list(p.value) if p is not None else []


def _xinfo(xid):
    """Read only X11 fields required by menu actions."""
    d = _open_x()
    try:
        w = d.create_resource_object('window', int(xid))
        wmclass = tuple((w.get_wm_class() or ()))
        return {
            'id': int(xid), 'class': wmclass,
            'pid': int((_prop(d, w, '_NET_WM_PID') or [0])[0]),
            'desktop': int((_prop(d, w, '_NET_WM_DESKTOP') or [0])[0]),
            'states': set(_prop(d, w, '_NET_WM_STATE')),
            'above_atom': d.intern_atom('_NET_WM_STATE_ABOVE'),
            'sticky_atom': d.intern_atom('_NET_WM_STATE_STICKY'),
            'max_atoms': (d.intern_atom('_NET_WM_STATE_MAXIMIZED_VERT'), d.intern_atom('_NET_WM_STATE_MAXIMIZED_HORZ')),
            'desktops': int((_prop(d, d.screen().root, '_NET_NUMBER_OF_DESKTOPS') or [1])[0]),
            'desktop_names': _desktop_names(d),
        }
    finally:
        d.close()


def _desktop_names(d):
    raw = _prop(d, d.screen().root, '_NET_DESKTOP_NAMES')
    try:
        if raw:
            return bytes(raw).decode('utf-8','replace').strip('\0').split('\0')
    except (TypeError, ValueError):
        pass
    return []


def _send(xid, atom_name, args):
    """Ask the X11 window manager, rather than directly manipulating windows."""
    from Xlib import X, protocol
    d = _open_x()
    try:
        w = d.create_resource_object('window', int(xid))
        root = d.screen().root
        data = ([int(i) for i in args] + [0] * 5)[:5]
        event = protocol.event.ClientMessage(window=w, client_type=d.intern_atom(atom_name), data=(32, data))
        root.send_event(event, event_mask=X.SubstructureNotifyMask | X.SubstructureRedirectMask)
        d.flush()
        return True
    finally:
        d.close()


def _state(xid, enabled, state1, state2=None):
    d = _open_x()
    try:
        first = d.intern_atom(state1)
        second = d.intern_atom(state2) if state2 else 0
    finally:
        d.close()
    return _send(xid, '_NET_WM_STATE', [1 if enabled else 0, first, second, 2, 0])


def _matching_windows(xid, wmclass):
    """Match WM_CLASS, not PID alone (PID may be a shared browser process)."""
    d = _open_x()
    try:
        root = d.screen().root
        ids = _prop(d, root, '_NET_CLIENT_LIST')
        matches = []
        for value in ids:
            try:
                w = d.create_resource_object('window', int(value))
                if tuple(w.get_wm_class() or ()) == wmclass and wmclass:
                    matches.append(int(value))
            except Exception:
                continue
        return matches
    finally:
        d.close()


def _desktop_file(wmclass, icon):
    """Only pin when a unique installed desktop entry can be verified."""
    tokens = {str(t).lower() for t in (*wmclass, icon) if t}
    roots = [Path.home()/'.local/share/applications', Path('/usr/local/share/applications'), Path('/usr/share/applications')]
    matches = []
    for base in roots:
        if not base.is_dir():
            continue
        for path in base.glob('*.desktop'):
            try:
                cfg = configparser.ConfigParser(interpolation=None, strict=False)
                cfg.read(path, encoding='utf-8')
                if 'Desktop Entry' not in cfg or cfg['Desktop Entry'].get('Type') != 'Application':
                    continue
                entry = cfg['Desktop Entry']
                keys = {path.stem.lower(), entry.get('StartupWMClass', '').lower()}
                if any(v in tokens for v in keys if v):
                    matches.append(path)
            except (OSError, ValueError, configparser.Error):
                continue
    unique = {p.resolve() for p in matches}
    return next(iter(unique)) if len(unique) == 1 else None


def install(bottom_dock):
    """Monkeypatch only task_menu, preserving other dock methods."""
    if getattr(bottom_dock.BottomDock, '_n3xvs_full_task_menu', False):
        return

    def full_task_menu(self, button, row):
        xid = int(row['id'])
        try:
            data = _xinfo(xid)
        except Exception as exc:
            QMessageBox.information(self, 'N3XV5 · Fenêtre', f'Fenêtre X11 indisponible : {exc}')
            return
        menu = self.themed_menu()
        menu.setTitle(row.get('name') or 'Fenêtre')
        menu.addAction('Activer / Restaurer', lambda: self.backend.action(xid))
        menu.addAction('Réduire', lambda: self.backend.action(xid, minimize=True))
        maximized = all(x in data['states'] for x in data['max_atoms'])
        menu.addAction('Restaurer la taille' if maximized else 'Maximiser',
                       lambda: _state(xid, not maximized, '_NET_WM_STATE_MAXIMIZED_VERT', '_NET_WM_STATE_MAXIMIZED_HORZ'))
        menu.addAction('Déplacer', lambda: _interactive(xid, 8))
        menu.addAction('Redimensionner', lambda: _interactive(xid, 4))
        # V3.1 : séparation des 5 premières actions.
        menu.addSeparator()
        above = data['above_atom'] in data['states']
        a = menu.addAction('Toujours au premier plan')
        a.setCheckable(True); a.setChecked(above)
        a.triggered.connect(lambda state: _state(xid, state, '_NET_WM_STATE_ABOVE'))
        sticky = data['desktop'] == 0xffffffff or data['sticky_atom'] in data['states']
        a = menu.addAction('Afficher sur tous les bureaux')
        a.setCheckable(True); a.setChecked(sticky)
        a.triggered.connect(lambda state: _send(xid, '_NET_WM_DESKTOP', [0xffffffff if state else 0, 2]))
        desktops = menu.addMenu('Déplacer vers un bureau virtuel')
        for i in range(max(1, min(32, data['desktops']))):
            title = data['desktop_names'][i] if i < len(data['desktop_names']) and data['desktop_names'][i] else f'Bureau {i+1}'
            action = desktops.addAction(title)
            action.setCheckable(True); action.setChecked(i == data['desktop'])
            action.triggered.connect(lambda checked=False, index=i: _send(xid, '_NET_WM_DESKTOP', [index, 2]))
        menu.addSeparator()
        path = _desktop_file(data['class'], row.get('icon', ''))
        folder = menu.addAction("Ouvrir le dossier de l'application")
        folder.setEnabled(path is not None and shutil.which('xdg-open') is not None)
        if folder.isEnabled():
            folder.triggered.connect(lambda: subprocess.Popen(['xdg-open', str(path.parent)],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True))
        pin = menu.addAction('Épingler à la BottomBar')
        pin.setEnabled(path is not None)
        if path is not None:
            pin.triggered.connect(lambda: self.shortcut_requested.emit('bottom', str(path)))
        menu.addAction("Informations sur l'application", lambda: _show_info(self, row, data, path))
        menu.addSeparator()
        menu.addAction('Fermer la fenêtre', lambda: self.backend.action(xid, close=True))
        group = _matching_windows(xid, data['class'])
        close_all = menu.addAction("Fermer toutes les fenêtres de l'application")
        close_all.setEnabled(len(group) > 1)
        close_all.triggered.connect(lambda: _close_all(self, group, row.get('name','application')))
        force = menu.addAction('Forcer la fermeture…')
        force.triggered.connect(lambda: _force_close(self, xid, row.get('name','fenêtre')))
        menu.exec(button.mapToGlobal(button.rect().topLeft()))

    bottom_dock.BottomDock.task_menu = full_task_menu
    bottom_dock.BottomDock._n3xvs_full_task_menu = True


def _interactive(xid, direction):
    from PySide6.QtGui import QCursor
    p = QCursor.pos()
    # XFWM _NET_WM_MOVERESIZE directions: 8 move, 4 bottom-right resize.
    return _send(xid, '_NET_WM_MOVERESIZE', [p.x(), p.y(), direction, 1, 2])


def _show_info(parent, row, data, path):
    name = row.get('name','Fenêtre')
    QMessageBox.information(parent, 'N3XV5 · Informations',
        f"Nom : {name}\nFenêtre X11 : 0x{data['id']:x}\nPID : {data['pid'] or 'inconnu'}\n"
        f"WM_CLASS : {', '.join(data['class']) or 'indisponible'}\n"
        f"Bureau virtuel : {data['desktop']+1 if data['desktop'] != 0xffffffff else 'Tous'}\n"
        f"Lanceur : {path if path else 'non identifié'}")


def _close_all(parent, xids, name):
    if QMessageBox.question(parent, 'N3XV5 · Fermer les fenêtres',
                            f"Fermer normalement {len(xids)} fenêtres appartenant à {name} ?") != QMessageBox.StandardButton.Yes:
        return
    for xid in xids:
        parent.backend.action(xid, close=True)


def _force_close(parent, xid, name):
    if QMessageBox.warning(parent, 'N3XV5 · Fermeture forcée',
                           f"Forcer la fermeture de {name} ?\nLes données non enregistrées peuvent être perdues.",
                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                           QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
        return
    # XKillClient closes the offending X11 client connection; it may close
    # several windows belonging to that client, which is why we confirm.
    d = _open_x()
    try:
        d.kill_client(int(xid))
        d.sync()
    finally:
        d.close()

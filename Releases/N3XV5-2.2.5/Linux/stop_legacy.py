#!/usr/bin/env python3
"""Stop ONLY user-owned known historical N3XV5/NovaBar bars and X11 windows.

No generic Python processes, no xfce4-panel, no modification to XFCE settings.
"""
import os
import signal
import time
import subprocess
from pathlib import Path

HOME=str(Path.home())
KNOWN_MARKERS=(
    HOME+'/N3XV5-XFCE-TEST/start_n3xvs.sh',
    HOME+'/N3XV5-NATIVE-V2/start_navbar_bottom.sh',
    HOME+'/N3XV5-NATIVE-V2/App/Modules/Bottom/HUD_HomeNavBar/start_slim_navbar.sh',
    HOME+'/N3XV5-NATIVE-V2/App/Modules/Bottom/HUD_HomeNavBar/NativeQt/n3xvs_bottom_slim.py',
    HOME+'/N3XV5-NATIVE-V2/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py',
    HOME+'/.local/share/n3xvs-hud/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py',
    '/usr/lib/novabar/HealthPerfsBar/HealthPerfsBar',
    '/usr/bin/novabar',
)
# Distinct historical dock title only; do not close a generic terminal or XFCE panel.
OLD_WINDOW_NAMES=(
    'NovaBar · CYBER NEXUS · Cockpit inférieur',
    'N3XV5 • Navbar Bottom — Slim Neon',
    'N3XV5 — Native Qt TOP HUD',
)

def user_processes():
    for item in Path('/proc').iterdir():
        if not item.name.isdigit(): continue
        pid=int(item.name)
        if pid in (os.getpid(),os.getppid()):continue
        try:
            if item.stat().st_uid != os.getuid():continue
            words=[x.decode('utf-8','replace') for x in (item/'cmdline').read_bytes().split(b'\0') if x]
        except (OSError,ProcessLookupError):continue
        yield pid,words

def known_pids():
    return {pid for pid,words in user_processes()
            if any(word in KNOWN_MARKERS for word in words)}

def x11_window_pids():
    """Find exact historical windows even when launched as 'python -'."""
    try:
        from Xlib import display, X, protocol
        d=display.Display()
        root=d.screen().root
        client_atom=d.intern_atom('_NET_CLIENT_LIST')
        title_atom=d.intern_atom('_NET_WM_NAME')
        pid_atom=d.intern_atom('_NET_WM_PID')
        close_atom=d.intern_atom('_NET_CLOSE_WINDOW')
        prop=root.get_full_property(client_atom,X.AnyPropertyType)
        if prop is None: return set(), False
        found=set()
        for xid in prop.value:
            try:
                win=d.create_resource_object('window',int(xid))
                title=win.get_full_property(title_atom,X.AnyPropertyType)
                name=(bytes(title.value).decode('utf-8','replace') if title is not None else win.get_wm_name()) or ''
                if name not in OLD_WINDOW_NAMES:continue
                p=win.get_full_property(pid_atom,X.AnyPropertyType)
                if p is None or len(p.value)<1:continue
                pid=int(p.value[0])
                proc=Path('/proc')/str(pid)
                if not proc.exists() or proc.stat().st_uid != os.getuid():continue
                found.add(pid)
                ev=protocol.event.ClientMessage(window=win,client_type=close_atom,data=(32,[0,0,0,0,0]))
                root.send_event(ev,event_mask=X.SubstructureRedirectMask|X.SubstructureNotifyMask)
                print(f'Fermeture X11 historique {name!r} PID={pid}',flush=True)
            except Exception as exc:
                print(f'INFO: fenêtre X11 ignorée ({exc})',flush=True)
        d.flush();d.close()
        return found, True
    except Exception as exc:
        print(f'INFO: enumeration X11 indisponible ({exc})',flush=True)
        return set(),False

def main():
    window_pids,detected=x11_window_pids()
    pids=known_pids()|window_pids
    # Allow graceful window-close requests a moment before sending TERM to known pids.
    time.sleep(.3)
    for pid in sorted(pids):
        try:
            print(f'Arrêt ciblé N3XV5 / NovaBar PID={pid}',flush=True)
            os.kill(pid,signal.SIGTERM)
        except (ProcessLookupError,PermissionError):pass
    for _ in range(25):
        remains={pid for pid in pids if Path('/proc',str(pid)).exists()}
        remains |= known_pids()
        if not remains:break
        time.sleep(.12)
    remains={pid for pid in pids if Path('/proc',str(pid)).exists()}|known_pids()
    if remains:
        print(f'ERREUR: anciennes instances non arrêtées: {sorted(remains)}',flush=True)
        return 1
    if not detected:
        print('ATTENTION: aucun contrôle des fenêtres X11 orphelines. Assure-toi qu’aucune ancienne Navbar ne reste affichée.',flush=True)
    print('✅ Arrêt ciblé terminé (panneau XFCE non modifié).',flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())

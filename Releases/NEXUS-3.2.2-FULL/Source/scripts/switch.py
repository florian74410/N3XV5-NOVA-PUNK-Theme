#!/usr/bin/env python3
"""Reversible user-level autostart switch. Never edits XFCE or Thunar config."""
import json,os,signal,sys,time
from pathlib import Path

HOME=Path.home()
AUTOSTART=HOME/'.config/autostart'
STATE=HOME/'.local/state/nexus-v3/switch.json'
NAMES=('health-perfs-bar.desktop','novabar.desktop','n3xvs-hud.desktop','nexus-v3.desktop')

def prepare(backup):
    if STATE.exists():
        raise RuntimeError('Une bascule V3 est déjà enregistrée : utiliser nexus-v3-rollback avant de recommencer')
    AUTOSTART.mkdir(parents=True,exist_ok=True)
    state={'backup':str(backup),'items':{},'old_launcher':None}
    backup.mkdir(parents=True,exist_ok=True)
    for name in NAMES:
        path=AUTOSTART/name
        if path.is_symlink():
            state['items'][name]={'existed':True,'symlink':True,'target':os.readlink(path)}
        elif path.exists():
            dst=backup/name;dst.write_bytes(path.read_bytes())
            state['items'][name]={'existed':True,'symlink':False,'backup':str(dst),'mode':path.stat().st_mode & 0o777}
        else:state['items'][name]={'existed':False}
    for launcher in (HOME/'.local/bin/n3xvs-hud',HOME/'.local/bin/novabar'):
        if launcher.exists():state['old_launcher']=str(launcher);break
    STATE.parent.mkdir(parents=True,exist_ok=True)
    temp=STATE.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2));temp.replace(STATE)
    for name in NAMES[:-1]:
        item=AUTOSTART/name
        if item.is_symlink():item.unlink()  # NEVER follow or overwrite the symlink target
        item.write_text('[Desktop Entry]\nType=Application\nName=NEXUS V2 disabled by V3 switch\nHidden=true\n',encoding='utf8')
    if (AUTOSTART/'nexus-v3.desktop').is_symlink():(AUTOSTART/'nexus-v3.desktop').unlink()
    (AUTOSTART/'nexus-v3.desktop').write_text('[Desktop Entry]\nType=Application\nName=NEXUS V3 (Parallel)\nExec='+str(HOME/'.local/bin/nexus-v3')+'\nTerminal=false\nX-GNOME-Autostart-enabled=true\nOnlyShowIn=XFCE;\n',encoding='utf8')


def restore():
    if not STATE.exists():
        print('Aucun état de bascule NEXUS V3 à restaurer');return None
    state=json.loads(STATE.read_text())
    for name,entry in state['items'].items():
        dst=AUTOSTART/name
        if dst.exists() or dst.is_symlink():dst.unlink()
        if entry['existed']:
            if entry.get('symlink'):
                dst.symlink_to(entry['target'])
            else:
                original=Path(entry['backup'])
                if original.exists():
                    dst.write_bytes(original.read_bytes())
                    dst.chmod(entry.get('mode',0o644))
    STATE.unlink()
    print('Autostart V2 restauré')
    return state.get('old_launcher')

def old_processes():
    own=os.getuid();found=[]
    for item in Path('/proc').iterdir():
        if not item.name.isdecimal():continue
        try:
            if item.stat().st_uid!=own:continue
            argv=(item/'cmdline').read_bytes().split(b'\0')
            args=[x.decode('utf8','replace') for x in argv if x]
        except (OSError,PermissionError):continue
        if not args:continue
        exe=Path(args[0]).name
        if (any('n3xvs_top_native.py' in arg for arg in args[1:]) or
            exe in ('HealthPerfsBar','novabar') or
            (exe.startswith('python') and args[1:3]==['-m','healthbar'])):
            found.append(int(item.name))
    return found

def stop_old():
    pids=old_processes()
    for pid in pids:
        try:os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:pass
    stop_at=time.monotonic()+5
    while time.monotonic()<stop_at and any(Path('/proc',str(pid)).exists() for pid in pids):
        time.sleep(.15)
    remaining=[pid for pid in pids if Path('/proc',str(pid)).exists()]
    if remaining:
        print('ATTENTION : processus V2 encore actifs :',remaining)
    else:print('Session V2 arrêtée :',pids)
    return not remaining

if __name__=='__main__':
    action=sys.argv[1]
    if action=='prepare':prepare(Path(sys.argv[2]))
    elif action=='restore':restore()
    elif action=='stop-old':sys.exit(0 if stop_old() else 1)

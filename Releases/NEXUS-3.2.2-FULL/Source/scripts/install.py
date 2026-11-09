#!/usr/bin/env python3
"""NEXUS V3 hybrid preview2 installer; user-level reversible migration only.

The installed V2 tree is the source of truth for visuals. This tool copies it,
never patches it. V3 core is staged for 3.1; no claim that it replaces V2
collectors or rendering in the hybrid process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
V2 = HOME/'.local/share/n3xvs-hud'
V3 = HOME/'.local/share/nexus-v3'
RELEASE = V3/'releases/3.0.0-hybrid-preview2'
STATE = HOME/'.local/state/nexus-v3-hybrid'
CONFIG = HOME/'.config/nexus-v3-hybrid'
AUTOSTART = HOME/'.config/autostart'
VERSION = '3.0.0-hybrid-preview2'
CURRENT = Path(__file__).resolve().parents[1]
TOP_REL = Path('App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py')
SHELL_REL = Path('App/Modules/Top/HUD_Plugins_ViewBar/Assets/reference_shell.png')
BOTTOM_REL = Path('App/Modules/Bottom/HUD_HomeNavBar/NativeQt/slim_style.py')
LEGACY_REL = Path('Legacy/Health-and-Perfs---Navigation-Controler-Bar')
LAUNCH = HOME/'.local/bin/nexus-v3-hybrid'
ROLLBACK = HOME/'.local/bin/nexus-v3-rollback'
AUTOV3 = AUTOSTART/'nexus-v3.desktop'
SWITCH_STATE = HOME/'.local/state/nexus-v3/switch.json'
V3_READY = HOME/'.config/nexus-v3/ready'


def ignored(_directory, entries):
    return {name for name in entries if name in {'.git','.venv','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'} or name.endswith('.pyc')}


def validate_source():
    expected = [TOP_REL, SHELL_REL, BOTTOM_REL, LEGACY_REL/'src/healthbar/app.py',LEGACY_REL/'src/healthbar/holo.py']
    missing = [str(V2/p) for p in expected if not (V2/p).is_file()]
    python = V2/'.venv/bin/python'
    if not python.is_file(): missing.append(str(python))
    if missing:
        raise RuntimeError('Installation V2 non complète ; aucune bascule autorisée :\n'+ '\n'.join(missing))
    for rel in (TOP_REL, BOTTOM_REL):
        text = (V2/rel).read_text(encoding='utf-8')
        compile(text,str(V2/rel),'exec')
    if (V2/SHELL_REL).stat().st_size < 2048:
        raise RuntimeError('Asset TopBar V2 absent ou anormalement petit')
    # Check the exact interpreter that the currently installed V2 uses.
    probe = 'import PySide6, Xlib, psutil, healthbar, dbus_next; from PySide6.QtWidgets import QApplication; print("V2_QT_OK")'
    env = os.environ.copy()
    env['PYTHONPATH'] = str(V2/LEGACY_REL/'src')
    proc = subprocess.run([str(python),'-c',probe],env=env,text=True,capture_output=True,timeout=15)
    if proc.returncode:
        raise RuntimeError('Python V2 non fonctionnel ; aucune bascule : '+(proc.stderr[-600:] or proc.stdout[-600:]))
    return python


def make_stage(python):
    V3.joinpath('releases').mkdir(parents=True, exist_ok=True)
    stage = V3/'releases'/('.staging-'+VERSION+'-'+str(os.getpid()))
    if stage.exists(): shutil.rmtree(stage)
    stage.mkdir()
    try:
        shutil.copytree(V2/'App',stage/'App',ignore=ignored)
        shutil.copytree(V2/LEGACY_REL,stage/LEGACY_REL,ignore=ignored)
        shutil.copytree(CURRENT/'nexus_core',stage/'nexus_core',ignore=ignored)
        shutil.copytree(CURRENT/'nexus_v3',stage/'nexus_v3',ignore=ignored)
        shutil.copytree(CURRENT/'tests',stage/'tests',ignore=ignored)
        shutil.copytree(CURRENT/'scripts',stage/'scripts',ignore=ignored)
        (stage/'VERSION.txt').write_text(VERSION+'\n')
        (stage/'HYBRID_MODE.txt').write_text('UI: V2 native Qt copied from installed N3XV5\nV3 controller/core: staged only, not yet authoritative for V2 widgets\n')
        checksums = {}
        for rel in (TOP_REL,SHELL_REL,BOTTOM_REL):
            checksums[str(rel)] = hashlib.sha256((stage/rel).read_bytes()).hexdigest()
            if (V2/rel).read_bytes() != (stage/rel).read_bytes():
                raise RuntimeError('Copie différente de la source V2 : '+str(rel))
        (stage/'v2-visual-manifest.json').write_text(json.dumps(checksums,indent=2)+'\n')
        for rel in (TOP_REL,BOTTOM_REL):
            compile((stage/rel).read_text(encoding='utf-8'),str(stage/rel),'exec')
        env = os.environ.copy(); env['PYTHONPATH']=str(stage)
        tests = subprocess.run([sys.executable,'-m','unittest','discover','-s',str(stage/'tests'),'-q'],cwd=stage,env=env,text=True,capture_output=True,timeout=30)
        if tests.returncode:
            raise RuntimeError('Tests V3 échoués : '+tests.stderr[-1500:])
        print(tests.stderr.strip() or 'Tests V3 réussis')
        print('✅ Code, assets V2 et moteur V3 vérifiés')
        return stage
    except Exception:
        shutil.rmtree(stage,ignore_errors=True)
        raise


def make_launcher(path,python):
    return '''#!/usr/bin/env bash
set -Eeuo pipefail
if [[ -z "${DISPLAY:-}" || "${XDG_SESSION_TYPE:-x11}" == "wayland" ]]; then
  echo "NEXUS Hybrid nécessite XFCE/X11" >&2; exit 2
fi
ROOT="'''+str(path)+'''"
V2PY="'''+str(python)+'''"
STATE="$HOME/.local/state/nexus-v3-hybrid"
mkdir -p "$STATE"
exec 9>"$STATE/session.lock"
if ! flock -n 9; then
  echo "NEXUS Hybrid déjà actif" >&2; exit 3
fi
export QT_QPA_PLATFORM=xcb
export HEALTHBAR_DATA_DIR="$HOME/.config/nexus-v3-hybrid"
export PYTHONPATH="$ROOT:$ROOT/Legacy/Health-and-Perfs---Navigation-Controler-Bar/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$V2PY" "$ROOT/App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py" \\
  --legacy "$ROOT/Legacy/Health-and-Perfs---Navigation-Controler-Bar" "$@"
'''


def backup_file(path, directory):
    if path.is_symlink():
        return {'kind':'symlink','target':os.readlink(path)}
    if path.exists():
        dst = directory / (path.name+'.orig')
        shutil.copy2(path,dst)
        return {'kind':'file','backup':str(dst)}
    return {'kind':'absent'}


def restore_file(path, entry):
    if path.exists() or path.is_symlink(): path.unlink()
    if entry['kind']=='file': shutil.copy2(entry['backup'],path)
    if entry['kind']=='symlink': path.symlink_to(entry['target'])


def proc_cmd(pid):
    try:
        if (Path('/proc')/str(pid)).stat().st_uid != os.getuid(): return ''
        return (Path('/proc')/str(pid)/'cmdline').read_bytes().replace(b'\0',b' ').decode('utf-8','replace')
    except (OSError,PermissionError): return ''


def managed_pid(pid,kind):
    cmd=proc_cmd(pid)
    if kind=='old-v3': return (' -m nexus_v3' in cmd or '/nexus_v3/__main__.py' in cmd) and 'n3xvs_top_native.py' not in cmd
    if kind=='hybrid': return str(RELEASE/TOP_REL) in cmd
    if kind=='old-v2':return 'n3xvs_top_native.py' in cmd and str(RELEASE) not in cmd and 'n3xvs-hud' in cmd
    return False


def stop_pid(pid,kind):
    if not managed_pid(pid,kind): return False
    os.kill(pid,signal.SIGTERM)
    for _ in range(30):
        if not managed_pid(pid,kind):return True
        time.sleep(.1)
    raise RuntimeError('Le processus ne s’est pas arrêté : '+str(pid))


def old_v2_pids():
    found=[]
    for p in Path('/proc').iterdir():
        if p.name.isdigit() and managed_pid(int(p.name),'old-v2'):
            found.append(int(p.name))
    return found


def stop_old():
    old_v3_pid = None
    if V3_READY.exists():
        raw=V3_READY.read_text().strip()
        if raw.isdigit() and managed_pid(int(raw),'old-v3'):
            old_v3_pid=int(raw)
            stop_pid(old_v3_pid,'old-v3')
            print('✅ Préversion V3 précédente arrêtée')
    for pid in old_v2_pids():
        stop_pid(pid,'old-v2')
    return old_v3_pid


def create_autostart():
    AUTOSTART.mkdir(parents=True,exist_ok=True)
    # Preserve preview1 switch-state if already prepared; otherwise use the
    # existing reversible switcher to archive and disable only known entries.
    if not SWITCH_STATE.exists():
        sys.path.insert(0,str(CURRENT/'scripts'))
        from switch import prepare
        prepare(STATE/'v2-autostart-backup')
    AUTOV3.write_text('[Desktop Entry]\nType=Application\nName=NEXUS V3 Hybrid (Blue Neon V2)\nExec='+str(LAUNCH)+'\nTerminal=false\nOnlyShowIn=XFCE;\nX-GNOME-Autostart-enabled=true\n',encoding='utf-8')


def save_preferences():
    if CONFIG.exists():return
    CONFIG.mkdir(parents=True,exist_ok=True)
    from_dir = HOME/'.config/n3xvs-hud'
    if from_dir.is_dir():
        for src in from_dir.rglob('*.json'):
            if any(seg in ('backups','logs') for seg in src.parts):continue
            dst = CONFIG/src.relative_to(from_dir)
            if dst.exists():continue
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true',help='Valide les sources V2 sans modifier les installations')
    args=parser.parse_args()
    python=validate_source()
    if args.check:
        print('✅ V2 disponible : châssis, Holo, BottomBar et Python Qt');return
    if not os.environ.get('DISPLAY') or os.environ.get('XDG_SESSION_TYPE','x11').lower()=='wayland':
        raise RuntimeError('Installation et bascule seulement depuis une session XFCE/X11')
    stage=make_stage(python)
    backup=STATE/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    backup.mkdir(parents=True,exist_ok=True)
    original_files = {str(p):backup_file(p,backup) for p in (LAUNCH,ROLLBACK,AUTOV3)}
    previous_switch_existed=SWITCH_STATE.exists()
    old_v3_pid=None
    process=None
    log=None
    try:
        if RELEASE.exists():
            raise RuntimeError('Preview2 déjà installée. Utilise le lanceur ou la restauration, pas un écrasement.')
        stage.rename(RELEASE)
        STATE.mkdir(parents=True,exist_ok=True)
        save_preferences()
        LAUNCH.parent.mkdir(parents=True,exist_ok=True)
        LAUNCH.write_text(make_launcher(RELEASE,python)); LAUNCH.chmod(0o755)
        print('===== BASCULE RÉVERSIBLE =====')
        old_v3_pid=stop_old()
        create_autostart()
        log=open(STATE/'session.log','ab',buffering=0)
        process=subprocess.Popen([str(LAUNCH)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=os.environ.copy())
        for _ in range(38):
            if process.poll() is not None:
                raise RuntimeError('Le rendu V2 hybride ne démarre pas ; voir session.log (code '+str(process.returncode)+')')
            time.sleep(.1)
        (STATE/'hybrid.pid').write_text(str(process.pid)+'\n')
        # Original preview1 launcher is deliberately left intact as a fallback.
        ROLLBACK.write_text('''#!/usr/bin/env bash
set -Eeuo pipefail
exec python3 "'''+str(RELEASE)+'''/scripts/rollback.py"
''')
        ROLLBACK.chmod(0o755)
        (STATE/'install.json').write_text(json.dumps({
            'release':str(RELEASE),'backup':str(backup),'files':original_files,
            'switch_preexisted':previous_switch_existed,'old_v3_pid':old_v3_pid,
        },indent=2)+'\n')
        print('✅ Hybrid Preview2 active (PID '+str(process.pid)+')')
        print('✅ Source visuelle : copie exacte de la V2 installée')
        print('↩ Retour V2 : ~/.local/bin/nexus-v3-rollback')
        print('🧾 Logs : '+str(STATE/'session.log'))
        print('⚠️ Validation visuelle réelle sur XFCE encore nécessaire')
    except Exception:
        if process is not None and process.poll() is None and managed_pid(process.pid,'hybrid'):
            stop_pid(process.pid,'hybrid')
        for path,value in original_files.items():restore_file(Path(path),value)
        if not previous_switch_existed and SWITCH_STATE.exists():
            sys.path.insert(0,str(CURRENT/'scripts'))
            from switch import restore
            restore()
        if old_v3_pid is not None:
            previous=HOME/'.local/bin/nexus-v3'
            if previous.is_file():subprocess.Popen([str(previous)],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            previous=HOME/'.local/bin/n3xvs-hud'
            if previous.is_file():subprocess.Popen([str(previous)],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        # This release was staged by this run, so discard it on failure; V2 untouched.
        if RELEASE.exists(): shutil.rmtree(RELEASE,ignore_errors=True)
        print('↩ Échec : fichiers de démarrage restaurés',file=sys.stderr)
        raise
    finally:
        if log: log.close()
        if stage.exists():shutil.rmtree(stage,ignore_errors=True)


if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,subprocess.TimeoutExpired) as exc:
        print('❌ '+str(exc),file=sys.stderr)
        sys.exit(1)

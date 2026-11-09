#!/usr/bin/env python3
"""Stop hybrid, restore original autostart entries, then start preserved V2."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import time

HOME=Path.home()
STATE=HOME/'.local/state/nexus-v3-hybrid'
PIDFILE=STATE/'hybrid.pid'
READY=HOME/'.config/nexus-v3/ready'

if PIDFILE.exists():
    raw=PIDFILE.read_text().strip()
    if raw.isdigit():
        pid=int(raw)
        try:
            proc=Path('/proc')/str(pid)
            cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode('utf-8','replace')
            if proc.stat().st_uid==os.getuid() and '3.0.0-hybrid-preview2' in cmd and 'n3xvs_top_native.py' in cmd:
                os.kill(pid,signal.SIGTERM)
                for _ in range(40):
                    if not proc.exists():break
                    time.sleep(.1)
        except (ProcessLookupError,OSError):pass
    PIDFILE.unlink(missing_ok=True)

# Restore all original user autostarts via the versioned switch state.
switch=HOME/'.local/share/nexus-v3/releases/3.0.0-hybrid-preview2/scripts/switch.py'
if not switch.is_file():
    raise SystemExit('Impossible de trouver le gestionnaire de restauration')
subprocess.run([sys.executable,str(switch),'restore'],check=True)

launcher=HOME/'.local/bin/n3xvs-hud'
if launcher.is_file():
    log=STATE/'rollback-v2.log'
    with log.open('ab') as output:
        subprocess.Popen([str(launcher)],stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
    print('✅ N3XV5 V2 relancée')
else:
    print('⚠️ Lanceur V2 introuvable : '+str(launcher))

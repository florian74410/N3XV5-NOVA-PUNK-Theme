"""N3XV5 lightweight supplemental metrics, no privileges and no fabricated values.

All expensive probes are startup-only or execute on a background thread.
The optional Internet bandwidth test can transfer substantial data. It is
manual by default, and hourly only after the user explicitly enables it.
"""
from __future__ import annotations
import json
import math
import shutil
import subprocess
import threading
import time
from pathlib import Path

SATA_CEILINGS = {'SATA II': 300, 'SATA III': 600}  # MB/s, nominal link limits


def storage_caps(info):
    """Return labelled nominal interface ceilings, never claim device benchmarks."""
    if not isinstance(info, dict):
        return None
    # Manufacturer speeds take precedence, handled by the caller.
    tech = str(info.get('storage_technology') or '').lower()
    if 'nvme' in tech or 'pcie' in tech:
        return 'NVMe/PCIe : débit dépend du lien et du SSD'
    if 'sata' not in tech and 'ata' not in tech:
        return None
    link = str(info.get('n3xvs_sata_speed') or info.get('storage_sata_link') or '').lower()
    if '6.0' in link or '6 gb' in link or 'sata3' in link or 'sata iii' in link:
        return 'SATA III : lien 600 MB/s · SSD ~500–560'
    if '3.0' in link or '3 gb' in link or 'sata2' in link or 'sata ii' in link:
        return 'SATA II : lien 300 MB/s · SSD ~250–280'
    if '1.5' in link or '1.5 gb' in link:
        return 'SATA I : max théorique 150 MB/s'
    return 'SATA : II ≤300 / III ≤600 MB/s (lien inconnu)'


def power_labels(data):
    """Indicate only actually provided electrical sensors; no invented wall watts."""
    data = data or {}
    def v(k):
        x=data.get(k)
        return float(x) if type(x) in (int,float) and math.isfinite(x) and x>=0 else None
    total=v('power_total_w')
    battery=v('battery_discharge_w')
    cpu=v('cpu_power_w')
    gpu=v('gpu_power_w')
    if battery is not None:
        return f'{battery:.1f} W', 'Batterie : décharge mesurée (portable)'
    if total is not None:
        return f'{total:.1f} W', 'Mesure capteur alimentation'
    if cpu is not None and gpu is not None:
        return f'{cpu:.0f}+{gpu:.0f} W', 'CPU + GPU mesurés · hors reste du PC'
    if cpu is not None:
        return f'{cpu:.1f} W', 'CPU mesuré · PC total inconnu'
    if gpu is not None:
        return f'{gpu:.1f} W', 'GPU mesuré · PC total inconnu'
    return 'SONDE —', 'Prise wattmètre pour les watts du PC'


def _parse_speedtest_json(payload, variant):
    """Ookla uses bytes/s; speedtest-cli uses bit/s."""
    item=json.loads(payload)
    if not isinstance(item,dict):
        raise ValueError('Réponse non JSON-object')
    if variant=='ookla':
        # Ookla result also includes status error objects. Verify both fields.
        down=item.get('download',{}).get('bandwidth')
        up=item.get('upload',{}).get('bandwidth')
        divisor=125000  # bytes/s -> Mbit/s
    else:
        down=item.get('download');up=item.get('upload');divisor=1000000
    if not all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in (down,up)):
        raise ValueError('Débits absents ou incorrects dans le résultat')
    return {'download_mbps':round(down/divisor,1),
            'upload_mbps':round(up/divisor,1),
            'measured_at':time.time(),'source':variant}


class InternetSpeedTest:
    """Threaded, nonblocking optional test; never touches Qt from worker threads."""
    def __init__(self):
        self.lock=threading.Lock()
        self.running=False
        self.result=None
        self.error='Test non effectué'
        self.last_attempt=0.0

    def start(self, *, automatic=False, interval_seconds=3600):
        with self.lock:
            now=time.time()
            if self.running:return False
            if automatic and now-self.last_attempt < max(3600,interval_seconds):return False
            self.running=True
            self.last_attempt=now
            self.error='Test en cours'
        threading.Thread(target=self._work,daemon=True,name='n3xvs-speedtest').start()
        return True

    def _work(self):
        cmd=None;variant=None
        # No subprocess/shell for utilities which are not already installed.
        if shutil.which('speedtest'):
            cmd=['speedtest','--accept-license','--accept-gdpr','--format=json'];variant='ookla'
        elif shutil.which('speedtest-cli'):
            cmd=['speedtest-cli','--json','--secure'];variant='legacy'
        try:
            if cmd is None:
                raise RuntimeError('Installer speedtest ou speedtest-cli pour mesurer le débit Internet')
            proc=subprocess.run(cmd,text=True,capture_output=True,timeout=90,check=False)
            if proc.returncode:
                raise RuntimeError((proc.stderr or proc.stdout or 'Échec test')[-200:])
            result=_parse_speedtest_json(proc.stdout,variant)
            with self.lock:
                self.result=result;self.error=None
        except (OSError,RuntimeError,ValueError,subprocess.TimeoutExpired,json.JSONDecodeError) as exc:
            with self.lock:self.error=str(exc)[:250]
        finally:
            with self.lock:self.running=False

    def summary(self):
        with self.lock:
            if self.running:return 'TEST EN COURS'
            if not self.result:return 'TEST NON EFFECTUÉ'
            d=self.result
            return f"TEST {d['download_mbps']:.0f}↓ / {d['upload_mbps']:.0f}↑ Mb/s"


SPEED_TEST=InternetSpeedTest()

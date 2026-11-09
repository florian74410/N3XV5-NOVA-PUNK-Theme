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
    cap=v('battery_capacity_percent')
    volts=v('battery_voltage_v')
    if cap is not None:
        status='SECTEUR' if data.get('power_ac_online') is True else 'BATTERIE'
        return f'BAT {cap:.0f} %', f'{volts:.2f} V · {status}' if volts is not None else status
    if volts is not None:
        return f'{volts:.2f} V', 'Batterie · puissance non mesurée'
    return 'SONDE —', 'Prise wattmètre pour les watts du PC'


def _parse_speedtest_json(payload, variant):
    """Validate only actual tool JSON, never treat tool output/errors as measured speed."""
    if not payload or not payload.strip():
        raise ValueError('Le test n’a renvoyé aucun résultat. Vérifier la connexion et l’outil Speedtest.')
    try:
        item=json.loads(payload.strip())
    except json.JSONDecodeError as exc:
        # CLI tools can print progress, license/error HTML or warnings instead of JSON.
        preview=' '.join(payload.strip().split())[:110]
        raise ValueError('Réponse Speedtest non JSON : '+(preview or 'sortie vide')) from exc
    if not isinstance(item,dict):
        raise ValueError('Format de résultat Speedtest non reconnu')
    if item.get('type')=='error' or item.get('error'):
        err=item.get('message') or item.get('error') or 'Échec du test'
        raise ValueError('Speedtest : '+str(err)[:145])
    if variant=='ookla':
        down=(item.get('download') or {}).get('bandwidth') if isinstance(item.get('download'),dict) else None
        up=(item.get('upload') or {}).get('bandwidth') if isinstance(item.get('upload'),dict) else None
        divisor=125000  # bytes/s -> Mbit/s
    else:
        down=item.get('download');up=item.get('upload');divisor=1000000  # bit/s -> Mbit/s
    if not all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in (down,up)):
        raise ValueError('Test inachevé : débits absents ou non valides')
    if down == 0 and up == 0:
        raise ValueError('Test sans transfert mesurable (0/0). Vérifier serveur et connexion.')
    return {'download_mbps':round(down/divisor,3),
            'upload_mbps':round(up/divisor,3),
            'measured_at':time.time(),'source':variant,
            'latency_ms':(item.get('ping',{}).get('latency') if isinstance(item.get('ping'),dict) else item.get('ping')),
            'server':((item.get('server') or {}).get('name') if isinstance(item.get('server'),dict) else None)}


def _identify_speedtest(executable):
    """Debian's python speedtest-cli can also be called 'speedtest'. Check --version."""
    try:
        proc=subprocess.run([executable,'--version'],text=True,capture_output=True,
                            timeout=6,check=False)
    except (OSError,subprocess.TimeoutExpired):
        return None
    version=((proc.stdout or '')+' '+(proc.stderr or '')).lower()
    if 'speedtest-cli' in version or 'sivel' in version:
        return 'legacy'
    if 'ookla' in version or 'speedtest by ookla' in version or 'speedtest version' in version:
        return 'ookla'
    return None


class InternetSpeedTest:
    """One nonblocking worker; result is kept on failures and never fabricated."""
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
        try:
            found=[]
            for name in ('speedtest','speedtest-cli'):
                exe=shutil.which(name)
                if exe and exe not in found:found.append(exe)
            if not found:
                raise RuntimeError('Speedtest absent : installer speedtest-cli ou Ookla Speedtest.')
            messages=[]
            # Prefer Ookla binary when available: old speedtest-cli backends may
            # select outdated endpoints and yield misleadingly low throughput.
            found.sort(key=lambda exe: 0 if _identify_speedtest(exe)=='ookla' else 1)
            for exe in found:
                kind=_identify_speedtest(exe)
                # Avoid choosing Ookla-only options for Debian's speedtest-cli.
                if kind=='ookla':
                    cmd=[exe,'--accept-license','--accept-gdpr','--format=json']
                elif kind=='legacy' or Path(exe).name=='speedtest-cli':
                    kind='legacy'
                    cmd=[exe,'--json','--secure']
                else:
                    messages.append(Path(exe).name+': outil Speedtest inconnu (--version).')
                    continue
                try:
                    proc=subprocess.run(cmd,text=True,capture_output=True,timeout=120,check=False)
                except subprocess.TimeoutExpired:
                    messages.append(Path(exe).name+': délai dépassé (120 s).')
                    continue
                if proc.returncode:
                    detail=' '.join((proc.stderr or proc.stdout or '').split())[:145]
                    messages.append(Path(exe).name+': '+(detail or f'code de sortie {proc.returncode}'))
                    continue
                try:
                    result=_parse_speedtest_json(proc.stdout,kind)
                except ValueError as exc:
                    messages.append(Path(exe).name+': '+str(exc))
                    continue
                if result['download_mbps'] < .01 and result['upload_mbps'] < .01:
                    messages.append(Path(exe).name+': résultat quasi nul, mesure non fiable; essayer le client Ookla officiel.')
                    continue
                with self.lock:
                    self.result=result
                    self.error=None
                return
            raise RuntimeError(' | '.join(messages)[:240] or 'Aucun test disponible')
        except (OSError,RuntimeError) as exc:
            with self.lock:self.error=str(exc)[:250]
        finally:
            with self.lock:self.running=False

    def summary(self):
        with self.lock:
            if self.running:return 'SPEEDTEST EN COURS'
            if not self.result:return 'TEST NON EFFECTUÉ' if self.error=='Test non effectué' else 'TEST ÉCHOUÉ — détails dans NET'
            d=self.result
            return f"TEST {d['download_mbps']:.2f}↓/{d['upload_mbps']:.2f}↑ Mbit/s · {('Ookla' if d['source']=='ookla' else 'speedtest-cli')}"


SPEED_TEST=InternetSpeedTest()
    # N3XV5 v2.3.10: persistent source/server-aware archives
from n3xvs_network_archive import install_worker as _n3xvs_install_worker
_n3xvs_install_worker(InternetSpeedTest, _parse_speedtest_json, _identify_speedtest)


class LinuxPowerProbe:
    """Read *measured* energy / electrical telemetry, never estimate PSU watts.

    RAPL exposes microjoules counters; successive samples yield average package
    watts over the sampling interval. hwmon 'power*_average/input' is microwatts.
    Discharge from power_supply is battery only and is not wall draw.
    """
    def __init__(self, cpu_root=Path('/sys/class/powercap'), hwmon_root=Path('/sys/class/hwmon'), battery_root=Path('/sys/class/power_supply')):
        self.cpu_root=Path(cpu_root)
        self.hwmon_root=Path(hwmon_root)
        self.battery_root=Path(battery_root)
        self._last={}
        self._values={}
        self._lock=threading.Lock()
        self._nvidia_last=0.0
        self._nvidia_running=False
        self._nvidia_power=None

    def _nvidia_poll_worker(self):
        try:
            proc=subprocess.run(['nvidia-smi','--query-gpu=power.draw',
                '--format=csv,noheader,nounits'],capture_output=True,text=True,
                timeout=5,check=False)
            if proc.returncode == 0:
                readings=[]
                for line in proc.stdout.splitlines():
                    try:
                        v=float(line.strip())
                        if math.isfinite(v) and v>=0:readings.append(v)
                    except ValueError:pass
                with self._lock:self._nvidia_power=sum(readings) if readings else None
        except (OSError,subprocess.TimeoutExpired):pass
        finally:
            with self._lock:self._nvidia_running=False

    @staticmethod
    def _positive(path):
        try:
            value=float(path.read_text().strip())
            return value if math.isfinite(value) and value>=0 else None
        except (OSError,ValueError,OverflowError):
            return None

    def poll(self):
        now=time.monotonic()
        result={}
        # RAPL zone package-0: package energy, not whole-machine draw.
        try:
            zones=list(self.cpu_root.glob('intel-rapl*'))
        except OSError:
            zones=[]
        for zone in zones:
            try:name=(zone/'name').read_text().strip().lower()
            except OSError:continue
            if 'package' not in name and 'pkg' not in name:
                continue
            energy=self._positive(zone/'energy_uj')
            if energy is None:continue
            prior=self._last.get(str(zone))
            self._last[str(zone)]=(energy,now)
            if prior is None:continue
            delta=energy-prior[0]
            if delta<0:
                maxval=self._positive(zone/'max_energy_range_uj')
                if maxval is not None:delta+=maxval
            dt=now-prior[1]
            if 0<dt<60 and 0<=delta:
                result['cpu_power_w']=round(delta/1_000_000/dt,2)
                result['power_source']='RAPL CPU package'
                break
        # Report explicit GPU power only when hwmon names identify GPU.
        try: hwmon=list(self.hwmon_root.glob('hwmon*'))
        except OSError: hwmon=[]
        for folder in hwmon:
            try: name=(folder/'name').read_text().strip().lower()
            except OSError:continue
            if not any(name.startswith(k) for k in ('amdgpu','nouveau','zenpower','amd_energy')):continue
            for path in (folder/'power1_average',folder/'power1_input'):
                watts=self._positive(path)
                if watts is not None:
                    key='cpu_power_w' if name.startswith(('zenpower','amd_energy')) else 'gpu_power_w'
                    result[key]=round(watts/1_000_000,2)
                    result['power_source' if key=='cpu_power_w' else 'gpu_power_source']='hwmon '+name
                    break
        # Laptop power_supply: charge, volts and AC state are independent of
        # watts. In particular a full battery may report 0 A with a valid voltage.
        try:
            for supply in self.battery_root.iterdir():
                if not supply.is_dir():
                    continue
                try:
                    supply_type=(supply/'type').read_text().strip().lower()
                except OSError:
                    continue
                if supply_type=='mains':
                    online=self._positive(supply/'online')
                    if online is not None:
                        result['power_ac_online']=bool(online)
                elif supply_type=='battery':
                    voltage=self._positive(supply/'voltage_now')
                    capacity=self._positive(supply/'capacity')
                    if voltage is not None:
                        result['battery_voltage_v']=round(voltage/1e6,3)
                    if capacity is not None:
                        result['battery_capacity_percent']=max(0.0,min(100.0,capacity))
                    try:
                        result['battery_status']=(supply/'status').read_text().strip()
                    except OSError:
                        pass
        except OSError:
            pass
        # Laptop batteries: power_now is microwatts; status disambiguates.
        try: battery_dirs=list(self.battery_root.glob('BAT*'))
        except OSError:battery_dirs=[]
        for folder in battery_dirs:
            power=self._positive(folder/'power_now')
            if power is None:
                current=self._positive(folder/'current_now')
                voltage=self._positive(folder/'voltage_now')
                if current is not None and voltage is not None:
                    power=current*voltage/1e12 # microamp * microvolt -> watt
            else: power/=1e6
            if power is not None:
                try: state=(folder/'status').read_text().strip().lower()
                except OSError: state='unknown'
                if state=='discharging':
                    result['battery_discharge_w']=round(power,2)
                    result['power_source']='battery discharge'
                result['battery_power_w']=round(power,2)
                break
        with self._lock:
            if self._nvidia_power is not None and 'gpu_power_w' not in result:
                result['gpu_power_w']=round(self._nvidia_power,2)
                result['gpu_power_source']='nvidia-smi (power.draw)'
            if now-self._nvidia_last>=15 and not self._nvidia_running and shutil.which('nvidia-smi'):
                self._nvidia_last=now
                self._nvidia_running=True
                threading.Thread(target=self._nvidia_poll_worker,daemon=True,
                                 name='n3xvs-power-nvidia').start()
            self._values=result
        return result

    def snapshot(self):
        with self._lock:return dict(self._values)

def power_sensor_diagnostics():
    """Quick, read-only operator diagnostics. Never requires root or estimates W."""
    root=Path('/sys/class/powercap')
    powercap=list(root.glob('intel-rapl*/energy_uj')) if root.exists() else []
    hwmon_root=Path('/sys/class/hwmon')
    hwmon=list(hwmon_root.glob('hwmon*/power*_input'))+list(hwmon_root.glob('hwmon*/power*_average')) if hwmon_root.exists() else []
    return {
        'rapl_energy_paths': [str(p) for p in powercap],
        'hwmon_power_paths': [str(p) for p in hwmon],
        'nvidia_smi_installed': bool(shutil.which('nvidia-smi')),
        'note': 'Ces fichiers peuvent exister mais être illisibles. Aucun TDP n’est assimilé à une mesure.'
    }

POWER_PROBE=LinuxPowerProbe()

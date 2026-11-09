"""Only read sensors belonging to enabled plugins. All probes are read-only."""
from __future__ import annotations
import re
import subprocess
import time
from pathlib import Path

try: import psutil
except ImportError: psutil = None


def cpu_fast():
    if psutil is None: return {'available': False}
    f = psutil.cpu_freq(percpu=True)
    return {'load_percent': psutil.cpu_percent(interval=None),
            'per_core_ghz': [round(v.current / 1000, 3) for v in f] if f else [],
            'package_ghz': round(sum(v.current for v in f)/len(f)/1000, 3) if f else None}


def thermal_fans_ram(*, cpu: bool, ram: bool, fans: bool):
    if psutil is None: return {}
    result = {}
    if fans:
        try:
            fans_data = psutil.sensors_fans()
            result['fans'] = [{'sensor': group, 'name': v.label or f'Fan {i+1}',
                               'rpm': v.current, 'max_rpm': None}
                              for group, items in fans_data.items() for i,v in enumerate(items)]
        except (OSError, AttributeError, RuntimeError): result['fans'] = []
    if cpu:
        try:
            sensors = psutil.sensors_temperatures(fahrenheit=False)
            values = [v.current for items in sensors.values() for v in items
                      if isinstance(v.current, (float, int))]
            result['cpu_temperature_c'] = max(values) if values else None
        except (OSError, AttributeError, RuntimeError): result['cpu_temperature_c'] = None
    if ram:
        v = psutil.virtual_memory()
        result['ram'] = {'used_bytes': v.used, 'total_bytes': v.total, 'percent': v.percent}
    return result


def power():
    supply = Path('/sys/class/power_supply')
    rows = []
    try: paths = list(supply.iterdir())
    except OSError: paths = []
    for p in paths:
        def item(key):
            try: return (p / key).read_text().strip()
            except OSError: return None
        kind = item('type')
        if kind not in ('Battery', 'Mains'): continue
        x = {'name': p.name, 'kind': kind, 'status': item('status')}
        for src, dest, factor in [('capacity','percent',1),('voltage_now','volts',1e-6),
                                  ('current_now','amps',1e-6),('power_now','watts',1e-6),('online','online',1)]:
            raw = item(src)
            if raw is not None:
                try: x[dest] = float(raw) * factor
                except ValueError: pass
        rows.append(x)
    return {'supplies': rows, 'pc_watts': None}  # battery watts != whole-PC watts


def network_ping(host='1.1.1.1', timeout=2):
    # Blocked ICMP is 'ping unavailable' rather than an assertion of disconnection.
    try:
        result = subprocess.run(['ping','-n','-c','1','-W',str(int(timeout)),host],
                                capture_output=True,text=True,timeout=timeout+2,check=False)
    except (OSError,subprocess.TimeoutExpired): return {'ping_ms': None, 'icmp_ok': False, 'links': {}}
    match = re.search(r'time[=<]([0-9.]+)\s*ms', result.stdout)
    links = {}
    if psutil is not None:
        try:
            links = {name: bool(info.isup) for name, info in psutil.net_if_stats().items()
                     if name != 'lo'}
        except (OSError, RuntimeError): pass
    return {'ping_ms': float(match.group(1)) if match else None,
            'icmp_ok': result.returncode == 0, 'links': links}


def network_burst(*, duration=1.0, sleep=time.sleep):
    """Sample actual interface traffic only when requested (or at startup/event)."""
    if not psutil: return {'available': False}
    before = psutil.net_io_counters(pernic=True)
    start = time.monotonic(); sleep(max(0.25, duration))
    after = psutil.net_io_counters(pernic=True)
    dt = max(.001, time.monotonic() - start)
    result = {}
    for nic, a in after.items():
        b = before.get(nic)
        if not b or nic == 'lo': continue
        result[nic] = {'down_Bps': max(0,(a.bytes_recv-b.bytes_recv)/dt),
                       'up_Bps': max(0,(a.bytes_sent-b.bytes_sent)/dt)}
    return {'interfaces': result, 'sample_seconds': round(dt,2)}


def gpu():
    # GPU drivers differ; unexposed measurements are represented as unavailable.
    return {'available': False, 'note': 'Adaptateur pilote GPU à intégrer dans la phase suivante'}

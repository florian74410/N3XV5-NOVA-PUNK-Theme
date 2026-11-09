"""Network counters and bounded ICMP latency; unavailable never means disconnected."""
import math
import os
import re
import subprocess
import sys
from pathlib import Path

PING_TARGET = '1.1.1.1'


def format_rate(mbs):
    if not isinstance(mbs, (int, float)) or not math.isfinite(mbs) or mbs < 0:
        return '—'
    bps = mbs * 1_000_000
    if bps < 1000:
        return f'{bps:.0f} B/s'
    if bps < 1_000_000:
        return f'{bps/1000:.1f} kB/s'
    return f'{mbs:.2f} MB/s'



def format_compact_rate(mbs):
    """Ultra-compact HUD rate: decimal MB (Mo) per second, one decimal only."""
    if not isinstance(mbs,(int,float)) or not math.isfinite(mbs) or mbs<0:
        return "— Mo/s"
    return f"{mbs:.1f} Mo/s"


def format_compact_ping(data):
    latency=data.get("net_ping_ms") if isinstance(data,dict) else None
    if not isinstance(latency,(int,float)) or not math.isfinite(latency) or latency<0:
        return "—"
    return str(round(latency))+"ms"

def format_ping(data):
    value = data.get('net_ping_ms')
    if value is None:
        return '—'
    return ('< ' if data.get('net_ping_less_than') else '') + f'{value:.1f} ms'


def default_interface():
    if not sys.platform.startswith('linux'):
        return None
    try:
        rows = [line.split() for line in Path('/proc/net/route').read_text().splitlines()[1:]]
        routes = [(int(r[6]), r[0]) for r in rows if len(r) >= 8 and r[1] == '00000000' and int(r[3], 16) & 1]
        return min(routes)[1] if routes else None
    except (OSError, ValueError):
        return None


def virtual_interface(name):
    return name.lower().startswith(('lo', 'docker', 'veth', 'br-', 'bridge', 'virbr', 'vboxnet', 'vmnet', 'utun', 'tun', 'tap', 'wg', 'tailscale'))


class NetworkSampler:
    def __init__(self):
        self.previous = {}
        self.previous_at = None

    def sample(self, psutil, now):
        result = {'net_down_mbs': None, 'net_up_mbs': None, 'net_interfaces': [], 'net_interface': None, 'net_sample_at': now}
        try:
            counters = psutil.net_io_counters(pernic=True)
        except (OSError, RuntimeError, ValueError, AttributeError):
            self.previous = {}; self.previous_at = None
            return result
        if counters is None:
            counters = {}
        try:
            stats = psutil.net_if_stats()
        except (OSError, RuntimeError, ValueError, AttributeError):
            stats = {}
        default = default_interface()
        delta = now-self.previous_at if self.previous_at is not None else 0
        for name, current in counters.items():
            before = self.previous.get(name)
            info = stats.get(name)
            def rate(field):
                difference = getattr(current, field)-getattr(before, field) if before else -1
                return difference/delta/1e6 if delta > 0 and difference >= 0 else None
            result['net_interfaces'].append({
                'name': name, 'isup': info.isup if info else None,
                'speed_mbps': info.speed if info and info.speed > 0 else None,
                'down_mbs': rate('bytes_recv'), 'up_mbs': rate('bytes_sent'),
                'virtual': virtual_interface(name)})
        rows = result['net_interfaces']
        rows.sort(key=lambda r: (r['name'] != default, r['isup'] is not True, r['virtual'], r['name']))
        selected = [r for r in rows if r['name'] == default and r['isup'] is not False]
        if not selected:
            selected = [r for r in rows if r['isup'] is True and not r['virtual']]
        if not selected:
            selected = [r for r in rows if r['isup'] is True and not r['name'].lower().startswith('lo')]
        if selected:
            result['net_interface'] = ', '.join(r['name'] for r in selected)
            for key, field in [('net_down_mbs','down_mbs'), ('net_up_mbs','up_mbs')]:
                rates = [r[field] for r in selected]
                if all(r is not None for r in rates):
                    result[key] = sum(rates)
        self.previous = counters
        self.previous_at = now
        return result


class PingProbe:
    """One ICMP request per 10 s, on the existing telemetry worker, timeout 1.5 s."""
    def __init__(self):
        self.next_at = 0
        self.result = {'net_ping_ms': None, 'net_ping_target': PING_TARGET,
                       'net_ping_status': 'En attente', 'net_ping_less_than': False}

    def sample(self, now):
        if now < self.next_at:
            return self.result.copy()
        self.next_at = now + 10
        self.result.update(net_ping_ms=None, net_ping_less_than=False, net_ping_sample_at=now)
        args = (['ping', '-n', '1', '-w', '1000', PING_TARGET] if sys.platform == 'win32' else
                ['ping', '-n', '-c', '1', '-W', '1000' if sys.platform == 'darwin' else '1', PING_TARGET])
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
        try:
            response = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=1.5,
                                      env=dict(os.environ, LC_ALL='C'), **options)
            match = re.search(r'[=<]\s*(\d+(?:[.,]\d+)?)\s*ms', response.stdout)
            if response.returncode == 0 and match:
                self.result.update(net_ping_ms=float(match[1].replace(',','.')),
                                   net_ping_less_than='<' in match[0], net_ping_status='ICMP mesuré')
            else:
                self.result['net_ping_status'] = 'Sans réponse ICMP'
        except FileNotFoundError:
            self.result['net_ping_status'] = 'Commande ping absente'
        except (OSError, subprocess.SubprocessError):
            self.result['net_ping_status'] = 'ICMP indisponible'
        return self.result.copy()

"""NEXUS 3 preview configuration: never writes to installed N3XV5 preferences."""
from __future__ import annotations
import copy
import json
from pathlib import Path

DEFAULTS = {
    'version': '3.0.0-dev1',
    'enabled': {k: True for k in ('cpu', 'ram', 'fans', 'gpu', 'storage', 'network', 'power')},
    'periods': {
        'cpu_fast': 1.0, 'thermal_fans_ram': 3.0, 'network_ping': 5.0,
        'power': 30.0, 'gpu': 5.0,
    },
    'animations': {'fps': 25, 'neon_fps': 25, 'background_policy': 'pause'},
    'network': {'ping_host': '1.1.1.1', 'ping_timeout': 2},
    'benchmarks': {'automatic': False, 'storage_size_gib': 1},
    'ui': {'bottom_height':46, 'always_expanded':False},
}
# The user requested independent per-plugin settings, but a single scheduled
# thermal/RAM group. RAM refresh uses FANS rate while either is active.
PERIOD_LIMITS = {'cpu_fast': (0.5, 15), 'thermal_fans_ram': (1, 60),
                 'network_ping': (2, 300), 'power': (5, 3600), 'gpu': (1, 60)}


def normalize(raw):
    result = copy.deepcopy(DEFAULTS)
    if not isinstance(raw, dict):
        return result
    for section in ('enabled', 'periods', 'animations', 'network','ui'):
        source = raw.get(section)
        if isinstance(source, dict):
            for k, v in source.items():
                if k in result[section]: result[section][k] = v
    for k in result['enabled']:
        result['enabled'][k] = bool(result['enabled'][k])
    for k, (lo, hi) in PERIOD_LIMITS.items():
        try: v = float(result['periods'][k])
        except (TypeError, ValueError): v = DEFAULTS['periods'][k]
        result['periods'][k] = max(lo, min(hi, v))
    for k in ('fps', 'neon_fps'):
        result['animations'][k] = max(1, min(60, int(result['animations'][k])))
    result['ui']['bottom_height'] = max(40,min(82,int(result['ui'].get('bottom_height',46))))
    result['ui']['always_expanded'] = bool(result['ui'].get('always_expanded',False))
    result['benchmarks'] = copy.deepcopy(DEFAULTS['benchmarks'])
    return result


class ConfigStore:
    def __init__(self, path): self.path = Path(path)
    def load(self):
        try: return normalize(json.loads(self.path.read_text(encoding='utf-8')))
        except (OSError, ValueError, TypeError): return normalize(None)
    def save(self, config):
        new = normalize(config)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(new, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        tmp.replace(self.path)
        return new

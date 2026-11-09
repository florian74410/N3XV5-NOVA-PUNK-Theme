"""Read-only hardware inventory, cached across restarts of the same OS boot."""
from __future__ import annotations
import json
import platform
from pathlib import Path


def _read(path):
    try: return Path(path).read_text(encoding='utf-8').strip()
    except OSError: return None


def boot_id():
    return _read('/proc/sys/kernel/random/boot_id') or 'unknown-boot'


def collect():
    # No dmidecode/root, no block writes, no probing hardware by injecting loads.
    try: import psutil
    except ImportError: psutil = None
    result = {
        'kernel': platform.release(), 'machine': platform.machine(),
        'cpu_model': platform.processor() or 'unknown',
        'boot_id': boot_id(), 'memory_total_bytes': None,
        'memory_type': None, 'memory_sticks': None,
        'disks': [], 'sources': ['platform', '/proc/sys/kernel/random/boot_id'],
    }
    if psutil:
        result['memory_total_bytes'] = psutil.virtual_memory().total
        result['sources'].append('psutil.virtual_memory')
        for mount in psutil.disk_partitions(all=False):
            if mount.device and mount.device.startswith('/dev/'):
                result['disks'].append({'device': mount.device, 'mount': mount.mountpoint, 'fstype': mount.fstype})
    # Unknown DDR generation and DIMM count stay None, never guessed.
    return result


class InventoryCache:
    def __init__(self, path): self.path = Path(path)
    def get(self):
        current_boot = boot_id()
        try:
            state = json.loads(self.path.read_text(encoding='utf-8'))
            if state['boot_id'] == current_boot: return state
        except (OSError, KeyError, ValueError, TypeError): pass
        state = collect()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        tmp.replace(self.path)
        return state

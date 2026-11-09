"""CPU detail sampling: physical cores where the OS exposes topology; no fake watts."""
import os
import platform
import re
import sys
import time
from pathlib import Path

def cpu_identity():
    # On Linux platform.processor() often returns just 'x86_64'; prefer
    # the actual branded model name offered by /proc/cpuinfo.
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/cpuinfo").read_text(errors="replace").splitlines():
                if line.lower().startswith(("model name", "hardware")) and ":" in line:
                    model=line.split(":", 1)[1].strip()
                    if model:
                        return model[:128]
        except OSError:
            pass
    model = platform.processor().strip() or platform.uname().processor.strip()
    return model[:128] or None


def topology(cpu_index):
    """Physical package/core ID, Linux only. Never infer mapping on other platforms."""
    base = Path(f"/sys/devices/system/cpu/cpu{cpu_index}/topology")
    try:
        return (int((base/"physical_package_id").read_text()),
                int((base/"core_id").read_text()))
    except (OSError, ValueError):
        return None

def core_temperatures(psutil):
    readings = {}
    if psutil is None or not hasattr(psutil, "sensors_temperatures"):
        return readings
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False)
        for chip, entries in sensors.items():
            if "coretemp" not in chip.lower():
                continue
            for item in entries:
                match = re.fullmatch(r"Core\s+(\d+)", item.label or "", flags=re.IGNORECASE)
                if match and item.current is not None:
                    readings[int(match.group(1))] = float(item.current)
    except (OSError, ValueError, RuntimeError):
        pass
    return readings

def sample_cpu_cores(psutil):
    if psutil is None:
        return []
    physical = (psutil.cpu_count(logical=False) or 0)
    logical = min(psutil.cpu_count(logical=True) or physical, 128)
    freq = []
    try:
        if hasattr(psutil, "cpu_freq"):
            freq = psutil.cpu_freq(percpu=True) or []
    except (OSError, RuntimeError, ValueError, TypeError, NotImplementedError):
        pass
    temperatures = core_temperatures(psutil)
    grouped = {}
    has_topology = logical > 0 and sys.platform.startswith("linux")
    for cpu in range(logical):
        key = topology(cpu) if has_topology else None
        if key is None:
            has_topology = False
            break
        grouped.setdefault(key, []).append(cpu)
    if has_topology and grouped:
        result = []
        for (socket, core_id), threads in sorted(grouped.items()):
            readings = [freq[idx].current / 1000 for idx in threads
                        if idx < len(freq) and getattr(freq[idx], "current", None) is not None]
            result.append({
                "label": f"Core {core_id}" if socket == 0 else f"CPU{socket} Core {core_id}",
                "frequency_ghz": (sum(readings)/len(readings) if readings else None),
                "temperature_c": temperatures.get(core_id) if socket == 0 else None,
                "power_w": None,
            })
        return result
    # Per-CPU frequencies are logical thread frequencies when topology cannot be verified.
    if freq:
        return [{
            "label": f"Thread {idx}",
            "frequency_ghz": (getattr(item, "current", None) / 1000
                              if getattr(item, "current", None) is not None else None),
            "temperature_c": None, "power_w": None
        } for idx, item in enumerate(freq[:128])]
    # Physical-core temperature data can still be displayed even without frequency data.
    if temperatures:
        return [{"label": f"Core {idx}", "frequency_ghz": None,
                 "temperature_c": t, "power_w": None}
                for idx, t in sorted(temperatures.items())][:128]
    return [{"label":f"Core {i}", "frequency_ghz":None,
             "temperature_c":None,"power_w":None}
            for i in range(min(physical,128))]

class PackagePower:
    """Intel RAPL package energy (uJ delta/s), if readable. No estimated per-core watts."""
    def __init__(self, root=Path("/sys/class/powercap/intel-rapl:0")):
        self.root = Path(root)
        self.previous = None

    def _hwmon_package_watts(self):
        """Read only CPU-specific power sensors: Linux hwmon values are µW."""
        try:
            for folder in Path("/sys/class/hwmon").glob("hwmon*"):
                chip=(folder/"name").read_text().strip().lower()
                if chip not in ("zenpower","k10temp","amd_energy","coretemp"):
                    continue
                sensors=list(folder.glob("power*_average")) or list(folder.glob("power*_input"))
                for sensor in sensors:
                    label_path=sensor.with_name(sensor.name.split("_",1)[0]+"_label")
                    label=label_path.read_text().lower() if label_path.exists() else ""
                    if label and not any(word in label for word in ("package","socket","cpu","ppt")):
                        continue
                    watts=float(sensor.read_text().strip())/1e6
                    if 0<=watts<=1000:
                        return round(watts,1)
        except (OSError,ValueError):
            return None
        return None

    def sample(self):
        if not sys.platform.startswith("linux"):
            return None
        hwmon=self._hwmon_package_watts()
        if hwmon is not None:
            return hwmon
        try:
            value = int((self.root/"energy_uj").read_text())
            maximum = int((self.root/"max_energy_range_uj").read_text())
            when = time.monotonic()
        except (OSError, ValueError):
            self.previous = None
            return None
        if self.previous is None:
            self.previous = (value, when)
            return None
        earlier, before = self.previous
        self.previous = (value, when)
        delta = value - earlier
        if delta < 0 and maximum > earlier:
            delta += maximum
        elapsed = when - before
        if delta < 0 or not 0.05 <= elapsed <= 120:
            return None
        watts = delta / 1_000_000 / elapsed
        return round(watts,1) if 0 <= watts <= 1000 else None

"""Read-only telemetry. Values are None when hardware or permissions do not expose them."""
import math
import subprocess
import time
import platform
from pathlib import Path
from .network_detail import NetworkSampler, PingProbe
from .cpu_detail import cpu_identity, sample_cpu_cores, PackagePower
from .hardware_identity import read_ram_identity, fan_maxima
from .storage_identity import read_storage_identity
from .config import data_dir
from .power_sensors import power_sensor_snapshot
try:
    import psutil
except ImportError:
    psutil = None

def _number(v):
    try:
        n = float(v)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None

def cpu_temperature():
    if psutil is None or not hasattr(psutil, "sensors_temperatures"):
        return None
    try:
        groups = psutil.sensors_temperatures(fahrenheit=False)
        for key in ("coretemp", "k10temp", "zenpower", "cpu_thermal"):
            values=[_number(item.current) for item in groups.get(key, [])]
            values=[value for value in values if value is not None and -20 <= value <= 150]
            if values:return max(values)
    except (OSError, RuntimeError, ValueError):
        pass
    return None

def motherboard_temperature():
    """Read motherboard/system temperature only, never label CPU temp as PC."""
    if psutil is None or not hasattr(psutil,"sensors_temperatures"):
        return None
    try:
        for chip,entries in psutil.sensors_temperatures().items():
            if not any(word in chip.lower() for word in ("acpitz","nct","it87","asus","gigabyte")):
                continue
            for sensor in entries:
                label=(sensor.label or "").lower()
                if any(word in label for word in ("system","motherboard","board","systin","temp1")):
                    value=_number(sensor.current)
                    if value is not None and -20 <= value <= 130:
                        return value
    except (OSError,RuntimeError,ValueError):
        pass
    return None

def list_fans():
    if psutil is None or not hasattr(psutil, "sensors_fans"):
        return []
    results = []
    try:
        for chip, fans in psutil.sensors_fans().items():
            for n, fan in enumerate(fans):
                rpm = _number(fan.current)
                if rpm is not None and rpm >= 0:
                    results.append({"name": (fan.label or f"{chip} {n+1}")[:30],
                                    "rpm": round(rpm)})
    except (OSError, RuntimeError, ValueError):
        pass
    return results[:32]

def nvidia_gpu():
    fields = "temperature.gpu,utilization.gpu,clocks.gr,memory.used,memory.total,power.draw"
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=" + fields,
                                 "--format=csv,noheader,nounits"],
                                capture_output=True, text=True, check=True, timeout=1.5)
        rows = result.stdout.splitlines()
        values = [_number(x.strip()) for x in rows[0].split(",")] if rows else []
        if len(values) == 6:
            keys = ("gpu_temperature_c", "gpu_percent", "gpu_clock_mhz",
                    "vram_used_mb", "vram_total_mb", "gpu_power_w")
            data = dict(zip(keys, values))
            for src, dst in (("vram_used_mb", "vram_used_gb"),
                             ("vram_total_mb", "vram_total_gb")):
                val = data.pop(src)
                data[dst] = val / 1024 if val is not None else None
            return data
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        pass
    return {}

class Telemetry:
    def __init__(self):
        self.last_at = time.monotonic()
        self.last_disk = None
        self.network = NetworkSampler()
        self.ping = PingProbe()
        self.package_power = PackagePower()
        self.cpu_model = cpu_identity()
        self.ram_inventory = read_ram_identity()
        self.storage_identity = read_storage_identity(data_dir()/"ssd_specs.json")
        self.fan_rpm_limits = fan_maxima()
        # Cache expensive hardware/backend probes between shared sampling passes.
        self.module_intervals = {'gpu': 3, 'fans': 5, 'power': 5}
        self._last_probes = {}
        self._probe_cache = {}
        if psutil:
            psutil.cpu_percent(interval=None)

    def _cached_probe(self, name, get_value, now):
        interval = max(1, min(60, int(self.module_intervals.get(name, 5))))
        if name not in self._probe_cache or now-self._last_probes.get(name, 0) >= interval:
            result = get_value()
            self._probe_cache[name] = result
            self._last_probes[name] = now
        return self._probe_cache[name]

    def sample(self):
        keys = ("cpu_percent", "cpu_frequency_ghz", "cpu_frequency_max_ghz",
            "cpu_temperature_c", "cpu_power_w", "cpu_model", "cpu_physical_cores", "cpu_logical_cores", "gpu_temperature_c", "gpu_percent", "gpu_clock_mhz",
            "gpu_power_w", "vram_used_gb", "vram_total_gb",
            "ram_percent", "ram_used_gb", "ram_available_gb", "ram_total_gb",
            "disk_percent", "disk_used_gb", "disk_free_gb", "disk_total_gb",
            "disk_read_mbs", "disk_write_mbs", "disk_health_percent",
            "net_down_mbs", "net_up_mbs","cpu_turbo_enabled","ram_modules","ram_module_count","pc_temperature_c","cpu_architecture")
        data = dict.fromkeys(keys)
        data["net_interfaces"] = []
        data["fans"] = []
        data["cpu_cores"] = []
        data["cpu_architecture"] = platform.machine()
        data.update(self.storage_identity)
        data["ram_modules"] = self.ram_inventory["modules"]
        data["ram_module_count"] = self.ram_inventory["count"]
        # Unsupported readings stay None; wall power is never estimated from TDP.
        now = time.monotonic()
        data.update(self._cached_probe("power", power_sensor_snapshot, now))
        if psutil is None:
            return data
        # Network acquisition is independent of CPU/sensor failures.
        data.update(self.network.sample(psutil, now))
        from .cpu_backends import system_backend
        try:
            data["cpu_turbo_enabled"] = self._cached_probe("turbo",lambda:system_backend().read(),now)
        except (OSError,ValueError):
            data["cpu_turbo_enabled"] = None
        data.update(self.ping.sample(now))
        data["pc_temperature_c"] = self._cached_probe("boardtemp",motherboard_temperature,now)
        try:
            data["cpu_percent"] = _number(psutil.cpu_percent(interval=None))
            data["cpu_model"] = self.cpu_model
            data["cpu_physical_cores"] = psutil.cpu_count(logical=False)
            data["cpu_logical_cores"] = psutil.cpu_count(logical=True)
            data["cpu_cores"] = sample_cpu_cores(psutil)
            data["cpu_power_w"] = self.package_power.sample()
            freq = psutil.cpu_freq() if hasattr(psutil, 'cpu_freq') else None
            if freq:
                data["cpu_frequency_ghz"] = round(freq.current/1000, 2)
                data["cpu_frequency_max_ghz"] = round(freq.max/1000, 2) if freq.max else None
            data["cpu_temperature_c"] = cpu_temperature()
            data["fans"] = self._cached_probe("fans", list_fans, now)
            for fan in data["fans"]:
                maximum=self.fan_rpm_limits.get(str(fan["name"]).lower())
                fan["max_rpm"]=maximum
                fan["percent_max"]=min(100,round(100*fan["rpm"]/maximum)) if maximum else None
            mem = psutil.virtual_memory()
            data.update(ram_percent=mem.percent, ram_used_gb=mem.used/2**30,
                        ram_available_gb=mem.available/2**30, ram_total_gb=mem.total/2**30)
            try:
                disk = psutil.disk_usage(Path.home().anchor or "/")
                data.update(disk_percent=disk.percent, disk_used_gb=disk.used/2**30,
                            disk_free_gb=disk.free/2**30, disk_total_gb=disk.total/2**30)
            except OSError:
                pass
            delta = max(0.001, now - self.last_at)
            io = psutil.disk_io_counters()
            if self.last_disk and io:
                data["disk_read_mbs"] = max(0, (io.read_bytes-self.last_disk.read_bytes)/delta/1e6)
                data["disk_write_mbs"] = max(0, (io.write_bytes-self.last_disk.write_bytes)/delta/1e6)
            self.last_disk = io
            self.last_at = now
        except (OSError, RuntimeError, ValueError):
            pass
        data.update(self._cached_probe("gpu", nvidia_gpu, now))
        return data

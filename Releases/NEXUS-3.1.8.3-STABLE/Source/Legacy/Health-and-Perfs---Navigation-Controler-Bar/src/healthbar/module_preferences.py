"""Validated per-module telemetry preferences, independent from the legacy profile.

All settings are opt-in. A single telemetry service remains responsible for
sampling; per-module intervals describe cache freshness, not extra pollers.
"""
import json
import os
import tempfile
from pathlib import Path
from .config import data_dir

MODULES = ("cpu","gpu","ram","storage","fans","network","power")
FIELDS = {
 "cpu": ("cpu_percent","cpu_temperature_c","cpu_frequency_ghz","cpu_cores","cpu_power_w"),
 "gpu": ("gpu_percent","gpu_temperature_c","gpu_clock_mhz","vram_used_gb","gpu_power_w"),
 "ram": ("ram_percent","ram_used_gb","ram_available_gb","ram_total_gb"),
 "storage": ("disk_percent","disk_used_gb","disk_free_gb","disk_read_mbs","disk_write_mbs"),
 "fans": ("fans",),
 "network": ("net_down_mbs","net_up_mbs","net_interfaces"),
 "power": ("cpu_power_w","gpu_power_w","power_total_w"),
}
DEFAULT_INTERVALS = {"cpu":2,"gpu":3,"ram":3,"storage":5,"fans":5,"network":2,"power":5}

def defaults():
    return {name:{"refresh_seconds":DEFAULT_INTERVALS[name], "holo_enabled":True,
                  "details":list(FIELDS[name])} for name in MODULES}

def normalize(raw):
    result=defaults()
    if not isinstance(raw,dict):
        return result
    for module in MODULES:
        value=raw.get(module,{})
        if not isinstance(value,dict):
            continue
        interval=value.get("refresh_seconds")
        if type(interval) is int and 1 <= interval <= 60:
            result[module]["refresh_seconds"]=interval
        if type(value.get("holo_enabled")) is bool:
            result[module]["holo_enabled"]=value["holo_enabled"]
        fields=value.get("details")
        if isinstance(fields,list):
            result[module]["details"]=[x for x in FIELDS[module] if x in fields]
    return result

def location():
    return data_dir()/"module-preferences.json"

def load():
    try:
        return normalize(json.loads(location().read_text(encoding="utf-8")))
    except (OSError,ValueError,TypeError):
        return defaults()

def save(value):
    target=location()
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=".module-",dir=target.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(normalize(value),out,indent=2,ensure_ascii=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name,target)
    finally:
        if os.path.exists(name):
            os.unlink(name)

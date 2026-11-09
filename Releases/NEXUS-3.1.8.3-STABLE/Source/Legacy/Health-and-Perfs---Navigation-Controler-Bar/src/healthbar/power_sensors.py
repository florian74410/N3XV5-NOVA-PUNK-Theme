"""Read-only electrical telemetry. Never infer wall draw from package or GPU watts.

System mains voltage / AC power requires external measurement hardware;
per-core CPU/GPU and VRAM voltage or watts are only populated if genuinely
available from hardware interfaces. Unknown != zero.
"""
from __future__ import annotations
import math
from pathlib import Path


def _read_number(path):
    try:
        value = float(path.read_text(encoding="utf-8").strip())
        return value if math.isfinite(value) else None
    except (OSError, ValueError, OverflowError):
        return None


def _read_label(path):
    try:
        return path.read_text(encoding="utf-8").strip()[:90]
    except (OSError, ValueError):
        return ""


def power_sensor_snapshot(hwmon_root=Path("/sys/class/hwmon"),
                          supply_root=Path("/sys/class/power_supply")):
    """Return explicit sources only; no total-PC wattage from adding components."""
    result = {
        "power_total_w": None, "power_mains_voltage_v": None,
        "cpu_package_voltage_v": None, "gpu_core_voltage_v": None,
        "gpu_core_power_w": None, "gpu_vram_power_w": None,
        "gpu_vram_voltage_v": None,
        "battery_discharge_w": None, "ram_voltage_rails": [],
    }
    try:
        chips = sorted(hwmon_root.iterdir())
    except OSError:
        chips = []
    for chip in chips[:80]:
        if not chip.is_dir():
            continue
        for path in sorted(chip.glob("in*_input"))[:48]:
            label = _read_label(path.with_name(path.name.replace("_input", "_label")))
            if not label:
                continue
            v = _read_number(path)
            if v is None or not 0 <= v <= 30000:
                continue
            volts = round(v / 1000, 4)  # Linux hwmon in*_input uses millivolts.
            normalized = label.lower().replace(" ", "")
            if any(token in normalized for token in ("dimm", "dram", "vddq", "vddmem", "vdimm")):
                if len(result["ram_voltage_rails"]) < 16:
                    result["ram_voltage_rails"].append({"name": label, "voltage_v": volts})
            elif any(token in normalized for token in ("vcore", "cpu_vcore", "vddcr_cpu")):
                # A shared rail is NOT an individual core measurement.
                if result["cpu_package_voltage_v"] is None:
                    result["cpu_package_voltage_v"] = volts
    try:
        supplies = sorted(supply_root.iterdir())
    except OSError:
        supplies = []
    for supply in supplies[:32]:
        if not supply.name.upper().startswith("BAT"):
            continue
        status = _read_label(supply / "status").lower()
        if status != "discharging":
            continue
        p = _read_number(supply / "power_now")  # microwatts
        if p is None:
            i = _read_number(supply / "current_now")  # microamps
            v = _read_number(supply / "voltage_now")  # microvolts
            p = i * v / 1_000_000 if i is not None and v is not None else None
        if p is not None and p >= 0:
            result["battery_discharge_w"] = round(p / 1_000_000, 2)
            break
    return result

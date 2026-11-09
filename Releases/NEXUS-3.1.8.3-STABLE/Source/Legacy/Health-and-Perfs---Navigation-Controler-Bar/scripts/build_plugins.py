"""Build eight separately distributable NovaBar API v2 sensor ZIPs."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json

PACKS = [
    ("cpu-manager-viewer", "CPU Manager/Viewer", "cpu",
     "GHz: green 0-2, amber 2-3, red >3; 0-3.5 GHz dial",
     ["cpu_frequency_ghz", "cpu_percent", "cpu_temperature_c", "cpu_cores", "cpu_model", "cpu_power_w", "cpu_physical_cores", "cpu_logical_cores"]),
    ("gpu-manager-viewer", "GPU Manager/Viewer", "gpu",
     "GPU clock, load, temperature, VRAM and watts; alerts at 60%/85%",
     ["gpu_clock_mhz", "gpu_percent", "gpu_temperature_c", "gpu_power_w", "vram_used_gb", "vram_total_gb"]),
    ("cpu-temperature-viewer", "CPU Temperature Viewer", "cpu",
     "CPU temperature and load; red >=85%, critical >=95%",
     ["cpu_temperature_c", "cpu_percent"]),
    ("ram-viewer", "RAM Viewer", "ram",
     "RAM percent, memory used and available", ["ram_percent", "ram_used_gb", "ram_available_gb"]),
    ("storage-viewer", "HDD/SSD/NVMe Viewer", "storage",
     "Storage gauge, used/free space, disk I/O rates; health when available",
     ["disk_percent", "disk_used_gb", "disk_free_gb", "disk_read_mbs", "disk_write_mbs", "disk_health_percent"]),
    ("fans-viewer", "Fans Manager/Viewer", "fans",
     "Discover available fan RPM sensors; no fan speed writes",
     ["fans"]),
    ("network-viewer", "Network Viewer", "network",
     "Network traffic up/down in MB/s", ["net_down_mbs", "net_up_mbs"]),
    ("power-viewer", "Power Plugin", "power",
     "Power and voltage readings only when supported by the hardware sensor, never estimated",
     ["power_total_w", "power_mains_voltage_v", "cpu_power_w", "cpu_cores",
      "cpu_package_voltage_v", "gpu_power_w", "gpu_core_voltage_v",
      "gpu_core_power_w", "gpu_vram_power_w", "gpu_vram_voltage_v",
      "ram_voltage_rails", "battery_discharge_w"]),
]

def build(dest=Path("dist/plugins")):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for ident, name, slot, description, sensors in PACKS:
        is_cpu_holo = ident == "cpu-manager-viewer"
        version = "2.1.0" if is_cpu_holo else "1.0.0" if ident == "power-viewer" else "1.1.0"
        manifest = {
            "api_version": 2, "id": ident, "name": name,
            "version": version, "slot": slot, "kind": "builtin-sensor",
            "description": description, "sensor_keys": sensors,
            "min_ram_mb": 32, "requires": ["healthbar>=0.5.0", "Python>=3.10",
                                          "PySide6-Essentials>=6.8", "psutil>=5.9"],
            "permissions": ["read_sensors"], "optional_permissions": []
        }
        if is_cpu_holo:
            manifest["holo_view"] = "cpu-core-matrix"
        dependencies = (
            "# DEPENDENCY.md\n\n- Python >= 3.10\n- NovaBar >= 0.5.0\n"
            "- PySide6-Essentials >= 6.8\n- psutil >= 5.9\n"
            "- Optional: nvidia-smi (NVIDIA GPU), lm-sensors/sysfs (Linux).\n"
            "- No administrative access or automatic dependency installation.\n"
        )
        icon_svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
                    '<g fill="none" stroke="#20DFFF" stroke-width="2">'
                    '<rect x="8" y="8" width="48" height="48" rx="8"/>'
                    '<circle cx="32" cy="32" r="16"/>'
                    '<path d="M32 16V32L44 40"/></g></svg>')
        files = {
            "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2),
            "README.md": f"# {name}\n\n{description}\n\n"
                         "Import via Extensions > Plugin Manager. Built-in read-only telemetry.\n",
            "DEPENDENCY.md": dependencies,
            "VERSION.md": "# Version\n\n" + version + "\n",
            "dependencies.json": json.dumps({"requires": manifest["requires"]}, indent=2),
            "module.json": json.dumps({"slot": slot, "sensors": sensors,
                                       "icon": "Assets/icon.svg", "ui_kit": "novabar-holo-v1", "holo_trigger": "top-right-icon-click"}, indent=2),
            "Assets/icon.svg": icon_svg,
            "Source Code/adapter.py": (
                '"""Data-only built-in telemetry declaration (not executed)."""\n'
                f'PLUGIN_ID = {ident!r}\nSLOT = {slot!r}\n'
                f'SENSORS = {sensors!r}\n'
            ),
            "Scripts/JS/README.md": "Reserved for optional web panels.\n",
            "Scripts/PHP/README.md": "Not required by native Qt runtime.\n",
            "Scripts/HTML/README.md": "Reserved for optional web panels.\n",
            "Scripts/CSS/README.md": "Reserved for optional web themes.\n",
            "Profils/Template/Settings.md": "# Plugin profile\n\nPer-user settings maintained by the host.\n",
            "Profils/Template/Overclocking.md": "# Overclock\n\nNo hardware control in this package.\n",
            "Hologram/CPU_CORE_MATRIX.md": (
                "# CPU CORE MATRIX\n\nNative, no executable code in ZIP.\n"
                "Click on the CPU slot after activating the CPU plugin.\n"
                "Columns: Core/thread, frequency GHz, temperature °C, power W.\n"
                "Final row: PACKAGE TOTAL (average clock, package temperature, measured package watts).\n"
                "No synthetic TDP or core power values. Missing sensors shown as em dash.\n"
            ) if is_cpu_holo else "# Sensor Holo\n\nNative host panel. Click the top-right plugin logo; no hover activation.\n",
            "Hologram/holo.json": json.dumps({
                "view": "cpu-core-matrix" if is_cpu_holo else "sensor-details",
                "open": "click", "pin": True, "close": ["escape", "button", "outside"],
                "placement": "auto", "accent": "inherit-theme",
                "columns": ["core", "frequency_ghz", "temperature_c", "power_w"]
            }, indent=2),
            "install.sh": (
                "#!/bin/sh\nset -eu\n"
                "test -f manifest.json && test -f DEPENDENCY.md && test -d Assets\n"
                "echo 'VALIDÉ: prêt à importer via NovaBar > Extensions'\n"
            ),
        }
        with ZipFile(dest / f"{ident}-v{version}.zip", "w", ZIP_DEFLATED) as archive:
            for filename, contents in files.items():
                archive.writestr(filename, contents)
    return len(PACKS)

if __name__ == "__main__":
    print("Plugins packaged:", build())

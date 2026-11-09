"""Best-effort, read-only hardware identity for the v0.8 Holos.

No privileged commands are attempted. RAM timing/clock are never guessed from
CPU speed, SMBIOS transfer rate, or marketing DDR labels.
"""
from __future__ import annotations
import re
import shutil
import subprocess
from pathlib import Path


def compact_cpu_name(raw):
    """Remove verbose marketing suffixes, preserving actual model and vendor."""
    if not raw:
        return "CPU · modèle indisponible"
    name=re.sub(r"\((?:R|TM|r|tm)\)|®|™","",str(raw))
    name=re.sub(r"\s+"," ",name).strip()
    name=re.sub(r"\s+CPU\s+@.*$","",name,flags=re.IGNORECASE)
    name=re.sub(r"\s+Processor\s*$","",name,flags=re.IGNORECASE)
    name=re.sub(r"\s+(?:Eight|Six|Quad|Dual|Twelve|Sixteen|\d+)-Core$", "", name, flags=re.IGNORECASE)
    # Keep model identifiers such as AMD Ryzen 7 1700X and Intel Core i7-12700K.
    return name[:85] or "CPU · modèle indisponible"


def _run_utility(program,args,timeout=2.5):
    if not shutil.which(program):
        return ""
    try:
        result=subprocess.run([program,*args],capture_output=True,text=True,
                              timeout=timeout,check=False,env={"LC_ALL":"C","PATH":"/usr/sbin:/usr/bin:/sbin:/bin"})
        return result.stdout if result.returncode==0 else ""
    except (OSError,subprocess.TimeoutExpired):
        return ""


def _memory_blocks(dmi_output):
    """Parse SMBIOS Type 17 readable output; no need to elevate the GUI."""
    blocks=re.split(r"(?=^Memory Device\s*$)",dmi_output,flags=re.MULTILINE)
    modules=[]
    for block in blocks:
        def field(key):
            match=re.search(r"^\s*"+re.escape(key)+r":\s*(.*?)\s*$",block,re.MULTILINE)
            return match.group(1).strip() if match else None
        size=field("Size")
        if not size or size.lower() in ("no module installed","not installed","unknown"):
            continue
        speed=field("Configured Memory Speed") or field("Configured Clock Speed") or field("Speed")
        location=field("Locator") or field("Bank Locator") or "DIMM"
        modules.append({"slot":location[:45],"size":size[:25],
                        "speed":speed[:32] if speed else None,
                        "cl":None,"live_clock_mhz":None})
    return modules[:32]


def read_ram_identity():
    raw=_run_utility("dmidecode",["--type","memory"])
    modules=_memory_blocks(raw)
    return {"modules":modules,"count":len(modules) if modules else None,
            "source":"SMBIOS" if modules else None,
            "cl":None,"live_frequency_available":False}


def fan_maxima():
    """Use kernel-reported fan*_max, never estimate a maximum RPM."""
    values={}
    try:
        for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
            for node in hwmon.glob("fan*_max"):
                prefix=node.name[:-4]
                try:
                    maximum=int(node.read_text().strip())
                    if maximum<=0:continue
                    label_file=hwmon/(prefix+"_label")
                    label=label_file.read_text().strip() if label_file.exists() else prefix
                    values[label.lower()]=maximum
                except (OSError,ValueError):
                    continue
    except OSError:
        pass
    return values


def connected_interface_name(data):
    interfaces=[x for x in data.get("net_interfaces",[]) if x.get("isup") is True]
    active=data.get("net_interface")
    selected=next((row for row in interfaces if row.get("name")==active),None)
    if selected is None and interfaces:
        selected=interfaces[0]
    if selected is None:
        return "RÉSEAU · déconnecté"
    name=str(selected.get("name") or "Interface")
    lower=name.lower()
    kind=("Wi-Fi" if lower.startswith(("wl","wlan","wifi")) else
          "Bluetooth" if lower.startswith(("bnep","bt")) else
          "LAN" if lower.startswith(("en","eth","eno")) else "WLAN" if "wlan" in lower
          else "RÉSEAU")
    return f"{kind} · {name}"[:74]

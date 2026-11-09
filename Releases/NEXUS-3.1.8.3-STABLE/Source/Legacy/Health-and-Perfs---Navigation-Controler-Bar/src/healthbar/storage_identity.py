"""Read-only storage identity from util-linux lsblk (once per Telemetry instance).

Never conflate measured OS-wide I/O with the manufacturer's specification.
A verified spec may be supplied by an explicit exact-model user catalogue.
No web/API calls, no permissions and no additional pip dependency.
"""
import json
import re
import sys
import subprocess
from pathlib import Path

def parse_lsblk(output):
    try:
        disk_list=json.loads(output).get("blockdevices") or []
    except (ValueError,TypeError,AttributeError):
        return {}
    def mounted(node):
        points=node.get("mountpoints") or []
        return "/" in points or any(mounted(child) for child in node.get("children") or [])
    disks=[x for x in disk_list if x.get("type")=="disk" and x.get("model")]
    roots=[x for x in disks if mounted(x)]
    # Never guess a drive when multiple disks exist and root is ambiguous.
    if not roots and len(disks)==1:
        roots=disks
    if len(roots)!=1:
        return {}
    entry=roots[0]
    model=str(entry.get("model") or "").strip()
    vendor=str(entry.get("vendor") or "").strip()
    if vendor and vendor.lower() not in model.lower():
        model=(vendor+" "+model).strip()
    bus=str(entry.get("tran") or "").strip().lower()
    name=str(entry.get("name") or "")
    tech=("NVMe / PCIe" if bus=="nvme" or name.startswith("nvme") else
          "SATA" if bus in ("sata","ata") else
          "USB" if bus=="usb" else
          "Interface "+bus.upper() if bus else "Interface non identifiée")
    return {"storage_model":model[:110],
            "storage_technology":tech[:45],
            "storage_datasheet_read_mbs":None,
            "storage_datasheet_write_mbs":None,
            "storage_datasheet_url":None}

def read_storage_identity(catalog_path=None):
    if not sys.platform.startswith("linux"):
        return {}
    try:
        proc=subprocess.run(
            ["lsblk","--json","--output","NAME,TYPE,TRAN,MODEL,VENDOR,MOUNTPOINTS"],
            capture_output=True,text=True,timeout=2,check=False)
        if proc.returncode:
            return {}
        details=parse_lsblk(proc.stdout)
    except (OSError,subprocess.TimeoutExpired):
        return {}
    if not details:
        return {}
    # Only exact, user-verified model IDs; never infer advertised MB/s from bus.
    if catalog_path:
        try:
            entries=json.loads(Path(catalog_path).read_text(encoding="utf-8"))
            matched=entries.get(details["storage_model"]) if isinstance(entries,dict) else None
            if isinstance(matched,dict):
                read=matched.get("sequential_read_mbs")
                write=matched.get("sequential_write_mbs")
                url=matched.get("manufacturer_datasheet_url")
                if all(type(value) in (int,float) and 0<value<=30000
                       for value in (read,write)) and isinstance(url,str) and (
                           url.startswith("https://") and len(url)<1000):
                    details.update(storage_datasheet_read_mbs=read,
                                   storage_datasheet_write_mbs=write,
                                   storage_datasheet_url=url)
        except (OSError,ValueError,TypeError):
            pass
    return details

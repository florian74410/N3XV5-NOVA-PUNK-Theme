#!/usr/bin/env python3
"""Restore only original XFCE panel windows previously hidden by NEXUS 3.2."""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import subprocess
import time

def restore(snapshot):
    if not snapshot or snapshot.get("display") != os.environ.get("DISPLAY"):
        return True
    rows=snapshot.get("panels", [])
    if not rows:
        return True
    try:
        from Xlib import X, display
        connection=display.Display()
        try:
            for row in rows:
                window=connection.create_resource_object("window",int(row["id"]))
                classes=window.get_wm_class() or ()
                if not any("xfce4-panel" in str(c).lower() for c in classes):
                    continue
                pid=window.get_full_property(connection.intern_atom("_NET_WM_PID"),X.AnyPropertyType)
                if row.get("pid") and (not pid or int(pid.value[0]) != int(row["pid"])):
                    continue
                window.map()
            connection.sync()
            time.sleep(.4)
            # Only report success when all known matching windows are visible.
            for row in rows:
                window=connection.create_resource_object("window",int(row["id"]))
                if window.get_attributes().map_state != X.IsViewable:
                    raise RuntimeError("XFCE panel window not viewable")
            return True
        finally:
            connection.close()
    except Exception:
        # Only use the XFCE-native restart when there WAS a known hidden panel.
        # This is not a session reset and does not modify XFCE configuration.
        try:
            result=subprocess.run(["xfce4-panel","--restart"],timeout=12,
                                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                  check=False)
            return result.returncode == 0
        except (OSError,subprocess.TimeoutExpired):
            return False

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshot",required=True,type=pathlib.Path)
    args=parser.parse_args()
    data=json.loads(args.snapshot.read_text(encoding="utf-8"))
    raise SystemExit(0 if restore(data) else 1)

#!/usr/bin/env python3
"""NEXUS 3.2.2 — Dolphin watcher: SIGUSR1 hide TopBar; SIGUSR2 show TopBar.

Never quits NEXUS, restores/restarts XFCE or touches the stable install.
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import pathlib
import signal
import time

LOG = logging.getLogger("nexus.gaming")
DEFAULT = pathlib.Path.home() / ".config/nexus-320/gaming-sleep.json"
PREFS = pathlib.Path.home() / ".config/nexus-v3-hybrid/n3xvs-unified.json"
EXIT = False

def stopping(_signum, _frame):
    global EXIT
    EXIT = True

def tasks():
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            args = [x.decode("utf-8", "replace") for x in (entry / "cmdline").read_bytes().split(b"\0") if x]
            if args:
                yield int(entry.name), args
        except (OSError, ValueError):
            continue

def gaming_allowed():
    try:
        return json.loads(PREFS.read_text(encoding="utf-8")).get("game_sleep_enabled", True) is True
    except (OSError, TypeError, ValueError):
        return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    enabled = config.get("enabled") is True and not args.dry_run
    names = {str(x).lower() for x in config.get("applications", ["dolphin-emu", "dolphin", "dolphin-emu-qt2"])}
    target = str(pathlib.Path(config["target_script"]).expanduser().resolve())
    interval = max(1.0, min(15.0, float(config.get("interval", 2))))
    if not pathlib.Path(target).is_file() or "nexus-318-full" in target:
        parser.error("Invalid 3.2.2 staged target")
    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    last = None
    last_pid = None
    stable_count = 0
    prior_active = None
    while not EXIT:
        processes = list(tasks())
        detected = any(pathlib.Path(argv[0]).name.lower() in names for _, argv in processes)
        active = bool(detected and gaming_allowed())
        if active == prior_active:
            stable_count += 1
        else:
            stable_count = 1
            prior_active = active
        pids = [pid for pid, argv in processes
                if target in argv and any(x.endswith("n3xvs_top_native.py") for x in argv)]
        pid = pids[0] if len(pids) == 1 else None
        if stable_count >= 2 and pid is not None and (last != active or last_pid != pid):
            action = "BOTTOM ONLY" if active else "RESTORE TOP"
            LOG.info("Gaming %s: PID %s", action, pid)
            if enabled:
                try:
                    os.kill(pid, signal.SIGUSR1 if active else signal.SIGUSR2)
                    last = active
                    last_pid = pid
                except ProcessLookupError:
                    last_pid = None
            else:
                LOG.info("Dry-run: signal suppressed")
        if pid is None:
            last_pid = None
        if args.once:
            break
        time.sleep(interval)
    LOG.info("Watcher stopped without changing XFCE")

if __name__ == "__main__":
    main()

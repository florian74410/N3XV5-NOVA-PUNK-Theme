#!/usr/bin/env python3
"""NEXUS 3.2 — Dolphin watcher for an OPT-IN staging installation.

No root, no process-name-wide pkill, no direct xfce4-panel calls.
Uses SIGUSR1 delivered only to a verified NEXUS 3.2 Qt process.
Does NOT interact with the unchanged production 3.1.8.3 source tree.
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import pathlib
import signal
import subprocess
import time

LOG = logging.getLogger("nexus.gaming")
STATE = pathlib.Path.home() / ".local/state/nexus-320-gaming/sleep.json"
DEFAULT = pathlib.Path.home() / ".config/nexus-320/gaming-sleep.json"
EXIT = False

def _sig(_signum, _frame):
    global EXIT
    EXIT = True

def cmdline(pid):
    try:
        return [x.decode("utf-8","replace") for x in
                pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0") if x]
    except (OSError, ValueError):
        return []

def tasks():
    for entry in pathlib.Path("/proc").iterdir():
        if entry.name.isdecimal():
            yield int(entry.name), cmdline(entry.name)

def matches_game(argv, names):
    if not argv:
        return False
    executable = pathlib.Path(argv[0]).name.lower()
    # The actual executable can be an AppImage with its own name.
    return executable in names

def nexus_pid(target):
    matches = []
    for pid, argv in tasks():
        if pid == os.getpid() or len(argv) < 2:
            continue
        if str(target) in argv and any(x.endswith("n3xvs_top_native.py") for x in argv):
            matches.append(pid)
    return matches

def save_state(payload):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(STATE)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    enabled = cfg.get("enabled") is True and not args.dry_run
    names = {x.lower() for x in cfg.get("applications", ["dolphin-emu", "dolphin"])}
    target = pathlib.Path(cfg["target_script"]).expanduser().resolve()
    launcher = pathlib.Path(cfg["launcher"]).expanduser().resolve()
    interval = max(1.0, min(15.0, float(cfg.get("interval", 2))))
    if not target.is_file():
        parser.error(f"NEXUS 3.2 Qt source not found: {target}")
    if enabled and not launcher.is_file():
        parser.error(f"NEXUS 3.2 launcher not found: {launcher}")
    if enabled and "nexus-318-full" in str(target):
        parser.error("Refusing to control the production 3.1.8.3 tree")
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)
    was_game = False
    consecutive = 0
    stopped_by_us = False
    # Remember recoverable wake intent if watcher restarts during a game.
    if STATE.exists():
        try:
            old = json.loads(STATE.read_text(encoding="utf-8"))
            if old.get("target") == str(target):
                stopped_by_us = old.get("stopped_by_us") is True
        except (OSError, ValueError):
            pass
    while not EXIT:
        active = any(matches_game(argv, names) for _pid, argv in tasks())
        consecutive = consecutive + 1 if active == was_game else 1
        was_game = active
        if consecutive >= 2:
            pids = nexus_pid(target)
            if active and pids and not stopped_by_us:
                if enabled and len(pids) == 1:
                    LOG.info("Dolphin detected: request graceful NEXUS 3.2 sleep PID %d", pids[0])
                    os.kill(pids[0], signal.SIGUSR1)
                    # Qt closes itself and NativePanelGuard restores XFCE; never SIGKILL.
                    for _ in range(40):
                        if not pathlib.Path(f"/proc/{pids[0]}").exists(): break
                        time.sleep(.25)
                    if not pathlib.Path(f"/proc/{pids[0]}").exists():
                        stopped_by_us = True
                        save_state({"target": str(target), "stopped_by_us": True})
                    else: LOG.warning("NEXUS did not exit; refusing force-stop")
                else:
                    LOG.info("[DRY-RUN] would request graceful NEXUS shutdown: %s", pids)
            elif not active and stopped_by_us:
                if enabled and not pids:
                    LOG.info("Dolphin exited: relaunch NEXUS 3.2")
                    try:
                        subprocess.Popen([str(launcher)], stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
                        stopped_by_us = False
                        save_state({"target": str(target), "stopped_by_us": False})
                    except OSError as exc: LOG.error("Wake failed: %s", exc)
                elif not enabled:
                    LOG.info("[DRY-RUN] would wake NEXUS 3.2")
        if args.once: break
        time.sleep(interval)
    LOG.info("Watcher exit; no forced process or panel changes")

if __name__ == "__main__":
    main()

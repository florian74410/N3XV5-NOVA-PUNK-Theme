#!/usr/bin/env python3
"""NEXUS Gaming Sleep watcher 3.2 (preview).

Independent stdlib-only watcher. No graphics, no root privileges.
By default, actions are DISABLED. Never kill unknown processes.
The actual NEXUS and XFCE transition needs a verified local adapter.
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import pathlib
import signal
import subprocess
import sys
import time

DEFAULT_CONFIG = pathlib.Path.home() / ".config/nexus-318/gaming-sleep.json"
LOG = logging.getLogger("nexus.gaming")
EXIT = False

def stop_signal(_signum, _frame):
    global EXIT
    EXIT = True

def game_running(names):
    """Match executable name exactly, rather than matching our own cmdline."""
    try:
        proc = subprocess.run(
            ["ps", "-eo", "comm="], check=True, capture_output=True, text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        LOG.error("Unable to query processes: %s", exc)
        return None  # unknown: avoid a destructive transition
    observed = {name.strip().lower() for name in proc.stdout.splitlines()}
    return any(n.lower() in observed for n in names)

def invoke(argv, label, *, dry_run, timeout):
    if not isinstance(argv, list) or not argv or not all(isinstance(s, str) and s for s in argv):
        raise ValueError(f"Invalid {label} argv; use a nonempty string array")
    LOG.info("%s: %s", label, argv)
    if dry_run:
        return True
    try:
        subprocess.run(argv, check=True, timeout=timeout)
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        LOG.error("%s failed: %s", label, exc)
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true", help="Log transitions; no changes")
    parser.add_argument("--once", action="store_true", help="Check processes once")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        cfg = json.loads(args.config.read_text(encoding="utf-8"))
        apps = cfg.get("applications", ["dolphin-emu", "dolphin-emu-qt2", "dolphin"])
        if not isinstance(apps, list) or not apps or not all(isinstance(a, str) and a for a in apps):
            raise ValueError("applications must be a nonempty list of strings")
        interval = max(1.0, min(30.0, float(cfg.get("interval_seconds", 2))))
        debounce = max(1, min(10, int(cfg.get("debounce_samples", 2))))
        commands = cfg.get("commands", {})
        if not isinstance(commands, dict):
            raise ValueError("commands must be an object")
        enabled = cfg.get("enabled", False) is True
        adapter_ready = cfg.get("local_adapter_verified", False) is True
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    dry_run = args.dry_run or not(enabled and adapter_ready)
    if not dry_run:
        if not all(commands.get(action) for action in ("sleep", "wake")):
            parser.error("Both sleep and wake commands required for enabled adapter")
    LOG.info("Watchdog started: enabled=%s adapter_verified=%s dry_run=%s",
             enabled, adapter_ready, dry_run)
    # Transition only if two consecutive samples agree; no startup action if no game.
    asleep = False
    last = None
    consecutive = 0
    while not EXIT:
        present = game_running(apps)
        if present is not None:
            consecutive = consecutive + 1 if present == last else 1
            last = present
            if consecutive >= debounce and present != asleep:
                # In a failed transition, stay in the old state, retry next poll.
                label = "sleep" if present else "wake"
                if dry_run:
                    LOG.info("WOULD %s: game=%s", label, present)
                    asleep = present
                elif invoke(commands[label], label, dry_run=False, timeout=30):
                    asleep = present
        if args.once:
            break
        time.sleep(interval)
    # Fail-safe: a controlled watcher shutdown while sleeping restores desktop.
    if asleep and not dry_run:
        invoke(commands["wake"], "wake-on-shutdown", dry_run=False, timeout=30)
    LOG.info("Watcher stopped")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop_signal)
    signal.signal(signal.SIGTERM, stop_signal)
    main()

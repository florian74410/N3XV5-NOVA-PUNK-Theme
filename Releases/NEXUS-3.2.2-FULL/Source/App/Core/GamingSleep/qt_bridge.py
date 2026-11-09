"""NEXUS 3.2.2 — gaming mode: hide TOP only, retain NEXUS BottomDock.

Signals are delivered only to the exact staged NEXUS Qt process by watcher_v322.
No XFCE restoration/restart. No quit/close calls on the main HUD.
"""
from __future__ import annotations
import signal

def install_game_sleep_bridge(app, bar):
    from PySide6.QtCore import QTimer
    requested = {"mode": None}
    previous_sleep = signal.getsignal(signal.SIGUSR1)
    previous_wake = signal.getsignal(signal.SIGUSR2)
    state = {"gaming": False}
    def sleep(_signum, _frame):
        requested["mode"] = True
    def wake(_signum, _frame):
        requested["mode"] = False
    signal.signal(signal.SIGUSR1, sleep)
    signal.signal(signal.SIGUSR2, wake)
    timer = QTimer(bar)
    timer.setInterval(200)
    def poll():
        mode = requested["mode"]
        if mode is None:
            return
        requested["mode"] = None
        if mode and not state["gaming"]:
            # A Qt top-level BottomDock survives the TopBar being hidden.
            if bar.bottom_dock is None:
                bar.settings.bottom_dock_enabled = True
                bar.sync_xfce_skin()
            dock = bar.bottom_dock
            if dock is None:
                return  # Never leave the user without a navigation bar.
            dock.show()
            dock.raise_()
            bar.hide_timer.stop()
            bar.hide()
            state["gaming"] = True
        elif not mode and state["gaming"]:
            bar.show()
            # arm_hide is the existing NEXUS automatic retract policy.
            bar.arm_hide()
            state["gaming"] = False
    timer.timeout.connect(poll)
    timer.start()
    def cleanup():
        timer.stop()
        signal.signal(signal.SIGUSR1, previous_sleep)
        signal.signal(signal.SIGUSR2, previous_wake)
    app.aboutToQuit.connect(cleanup)
    return timer

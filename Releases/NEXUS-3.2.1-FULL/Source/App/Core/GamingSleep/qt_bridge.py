"""Optional NEXUS 3.2 QT bridge: request graceful exit for gaming mode.

This module does not change any styling or timers. It is installed ONLY into
a separately staged 3.2 source tree. No modification of installed 3.1.8.3.
"""
import signal

def install_game_sleep_bridge(app, qt_parent):
    from PySide6.QtCore import QTimer
    requested = {"value": False}
    previous = signal.getsignal(signal.SIGUSR1)

    def request_sleep(_signum, _frame):
        requested["value"] = True

    signal.signal(signal.SIGUSR1, request_sleep)
    timer = QTimer(qt_parent)
    timer.setInterval(200)
    def poll():
        if requested["value"]:
            requested["value"] = False
            timer.stop()
            app.quit()  # aboutToQuit triggers bar.close(); bottom dock restores XFCE
    timer.timeout.connect(poll)
    timer.start()
    def restore_signal():
        signal.signal(signal.SIGUSR1, previous)
    app.aboutToQuit.connect(restore_signal)
    return timer

"""Qt animation clock: 25 FPS while visible, no rendering while hidden.

No input polling, no telemetry calls. The UI retains full active animation speed.
"""
class AnimationClock:
    def __init__(self, repaint, fps=25):
        from PySide6.QtCore import QTimer,Qt
        self.timer=QTimer()
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(max(16,round(1000/fps)))
        self.timer.timeout.connect(repaint)
        self.enabled=True
        self.visible=False
        self.interacting=False

    def update_visibility(self, visible, effect_active=True):
        self.visible=bool(visible)
        self.interacting=bool(effect_active)
        if self.enabled and self.visible and self.interacting:
            if not self.timer.isActive(): self.timer.start()
        else:self.timer.stop()

    def stop(self): self.timer.stop()

"""Qt components ready for future integration in the EXISTING settings/Holos.

No top-level imports from Qt, no X11 window reservation, no desktop modifications.
"""
from __future__ import annotations


def make_cache_controls(cache, parent=None):
    """Return a narrow native widget for Paramètres > Performances."""
    from PySide6.QtWidgets import QWidget,QHBoxLayout,QLabel,QPushButton
    panel = QWidget(parent)
    row = QHBoxLayout(panel)
    row.setContentsMargins(0,0,0,0)
    label = QLabel('Cache graphique · châssis / instruments',panel)
    button = QPushButton('Vider le cache',panel)
    status = QLabel('',panel)
    row.addWidget(label,1);row.addWidget(button);row.addWidget(status)
    def clear():
        cache.clear()
        status.setText('Cache vidé ✓')
    button.clicked.connect(clear)
    return panel


def make_benchmark_controls(benchmark, parent=None):
    """Return a native progress bar + Play/Stop, no benchmark on construction.

    Benchmark callbacks run in a worker; Qt signal marshals them to the GUI.
    """
    from PySide6.QtCore import QObject, Signal,Qt
    from PySide6.QtWidgets import QWidget,QHBoxLayout,QProgressBar,QToolButton,QLabel

    class Bridge(QObject):
        changed = Signal(dict)
    panel = QWidget(parent)
    row = QHBoxLayout(panel)
    row.setContentsMargins(0,0,0,0)
    progress = QProgressBar(panel)
    progress.setRange(0,100);progress.setValue(0)
    progress.setTextVisible(True)
    button = QToolButton(panel)
    button.setText('▶');button.setToolTip('Démarrer le benchmark disque (manuel)')
    status = QLabel('Prêt',panel)
    row.addWidget(progress,1);row.addWidget(button);row.addWidget(status)
    bridge = Bridge(panel)
    def on_event(event):
        state = event['state']
        progress.setValue(round(event.get('percent',0)))
        if state in ('writing','reading'):
            status.setText('Écriture…' if state=='writing' else 'Lecture…')
            button.setText('■')
        elif state=='success':
            button.setText('▶');status.setText('✓ Terminé')
        elif state=='cancelled':
            button.setText('▶');status.setText('Annulé');progress.setValue(0)
        elif state=='error':
            button.setText('▶');status.setText('Erreur');status.setToolTip(event.get('error',''))
    bridge.changed.connect(on_event)
    benchmark.on_event = bridge.changed.emit
    def toggle():
        if benchmark.running: benchmark.stop()
        else:
            status.setText('Lancement…')
            benchmark.start()
    button.clicked.connect(toggle)
    panel._nexus_bridge = bridge  # keep alive for the widget lifetime
    return panel


class QtLayerCache:
    """Native QPixmap frame cache for fixed chassis and measured instruments."""
    def __init__(self, graphics_cache):
        self.cache = graphics_cache

    def chassis_frame(self, width, height, theme, draw_static):
        from PySide6.QtGui import QPixmap,QPainter
        from PySide6.QtCore import Qt
        def render():
            frame = QPixmap(width,height)
            frame.fill(Qt.GlobalColor.transparent)
            painter = QPainter(frame)
            try: draw_static(painter,width,height)
            finally:painter.end()
            return frame
        return self.cache.chassis((width,height,theme),render)

    def instruments_frame(self, plugin, key, width, height, draw_data):
        from PySide6.QtGui import QPixmap,QPainter
        from PySide6.QtCore import Qt
        def render():
            frame=QPixmap(width,height);frame.fill(Qt.GlobalColor.transparent)
            painter=QPainter(frame)
            try: draw_data(painter,width,height)
            finally:painter.end()
            return frame
        return self.cache.instruments(plugin,(key,width,height),render)

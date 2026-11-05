"""N3XV5 Slim Neon — visual-only replacement for NovaBar 0.8.2.2 BottomDock.

Keeps original task/window management, tray, icons, launchers and mouse handling.
No modifications to installed NovaBar files or its configuration are made.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient, QPainterPath
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton

from healthbar import bottom_dock as legacy_dock
from healthbar import cockpit_style as legacy_style
from healthbar.config import Settings

CYAN = QColor("#17ceff")
ROYAL = QColor("#176efa")
BLOOD = QColor("#aa1933")
CONFIG = Path.home() / ".config" / "n3xvs-bottom" / "appearance.json"


def _clamp(number, low, high):
    try:
        return max(low, min(high, int(number)))
    except (ValueError, TypeError, OverflowError):
        return low


def load_appearance():
    defaults = {"height": 70, "opacity": 46}
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            defaults["height"] = _clamp(data.get("height", 70), 62, 94)
            defaults["opacity"] = _clamp(data.get("opacity", 46), 15, 85)
    except (OSError, ValueError, TypeError):
        pass
    return defaults


def _thin_stroke(painter, path, color, width=0.85, hot=False):
    color = QColor(color)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    haze = QColor(color)
    haze.setAlpha(17 if not hot else 28)
    painter.setPen(QPen(haze, width + (3 if not hot else 4)))
    painter.drawPath(path)
    color.setAlpha(165 if not hot else 230)
    painter.setPen(QPen(color, width))
    painter.drawPath(path)


def slim_frame_paint(self, event):
    """Single bezel, two faint PCB rails, original launch/task/status areas preserved."""
    p = QPainter(self)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    p.fillRect(self.rect(), Qt.GlobalColor.transparent)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    width, height = self.width(), self.height()
    if width < 25 or height < 25:
        p.end()
        return

    outer = legacy_style.cut_path(QRectF(2.0, 3.0, width - 4.0, height - 6.0), 13)
    base = QLinearGradient(0, 0, 0, height)
    base.setColorAt(0, QColor("#12253b"))
    base.setColorAt(0.20, QColor("#071524"))
    base.setColorAt(0.65, QColor("#06111d"))
    base.setColorAt(1, QColor("#0a1a2c"))

    opacity = max(0.18, min(0.84, self.glass_opacity / 100))
    p.save()
    p.setOpacity(opacity)
    p.fillPath(outer, base)
    p.restore()
    _thin_stroke(p, outer, CYAN, 0.95, hot=self.underMouse())

    # Fine internal separation, not a second thick glowing bezel.
    p.setPen(QPen(QColor(35, 111, 174, 90), 0.55))
    inset = legacy_style.cut_path(QRectF(5, 6, width - 10, height - 12), 11)
    p.drawPath(inset)

    # Localized housings make launcher and status sections readable without
    # boxing the central task buttons inside a third metallic ring.
    p.setClipPath(outer)
    regions = self.regions() if callable(getattr(self, "regions", None)) else []
    for region in regions:
        if region.width() < 28 or region.height() < 12:
            continue
        rect = QRectF(region).adjusted(-1, 0, 1, 0)
        box = legacy_style.cut_path(rect, 8)
        shade = QLinearGradient(0, rect.top(), 0, rect.bottom())
        shade.setColorAt(0, QColor(10, 38, 63, 155))
        shade.setColorAt(1, QColor(2, 15, 29, 165))
        p.fillPath(box, shade)
        _thin_stroke(p, box, QColor("#1664a9"), 0.6)

    # Low-density circuit tracks; only one moving luminous segment per side.
    phase = float(getattr(self, "phase", 0))
    for yy, sign in ((8, 1), (height - 9, -1)):
        rail = QPainterPath(QPointF(19, yy))
        rail.lineTo(width - 19, yy)
        p.setPen(QPen(QColor(ROYAL.red(), ROYAL.green(), ROYAL.blue(), 105), 0.65))
        p.drawPath(rail)
        for x in range(65, width - 60, 180):
            trace = QPainterPath(QPointF(x, yy))
            trace.lineTo(x + 22, yy)
            trace.lineTo(x + 28, yy + 3 * sign)
            trace.lineTo(x + 47, yy + 3 * sign)
            p.setPen(QPen(QColor(21, 160, 218, 110), 0.55))
            p.drawPath(trace)
            if (x // 180) % 5 == 2:
                p.setPen(QPen(QColor(BLOOD.red(), BLOOD.green(), BLOOD.blue(), 200), 1))
                p.drawLine(QPointF(x + 19, yy), QPointF(x + 24, yy + 2 * sign))
        # Only a tiny LED travels the rail, no full-length flashing.
        progress = (phase / (2 * math.pi) + (0.27 if sign < 0 else 0.0)) % 1
        cx = 25 + (width - 50) * progress
        pulse = QPainterPath(QPointF(max(18, cx - 8), yy))
        pulse.lineTo(min(width - 18, cx + 8), yy)
        _thin_stroke(p, pulse, QColor("#35dfff"), 1.1, hot=True)

    p.setClipping(False)
    p.end()


def slim_glow(p, path, color, width=1.2):
    """Reduce the old thick shadow on task-button borders."""
    _thin_stroke(p, path, color, min(0.9, width * 0.65))


def apply_skin():
    """Patch drawing only; deliberately leave signal connections and logic untouched."""
    legacy_style.CockpitFrame.paintEvent = slim_frame_paint
    legacy_dock.glow = slim_glow


def new_dock():
    appearance = load_appearance()
    settings = Settings.load()
    # These values are applied in memory only, never saved to legacy settings.json.
    settings.theme = "blue-neon"
    settings.bottom_dock_enabled = True
    settings.bottom_dock_height = appearance["height"]
    settings.bottom_nav_opacity = appearance["opacity"]
    apply_skin()
    dock = legacy_dock.BottomDock(settings)
    dock.setWindowTitle("N3XV5 • Navbar Bottom — Slim Neon")
    dock.row.setContentsMargins(16, 11, 16, 11)
    dock.row.setSpacing(5)
    dock.pins.setSpacing(3)
    dock.tasks.setSpacing(5)
    # Keep all task buttons, launcher actions, notification host and status icons.
    dock.body.update()
    return dock


def show_appearance(dock):
    dialog = QDialog(dock)
    dialog.setWindowTitle("N3XV5 • Navbar Bottom")
    dialog.setMinimumWidth(345)
    dialog.setStyleSheet("""
        QDialog {background:#071626;color:#d6f4ff;border:1px solid #167aca;}
        QLabel {color:#dbf5ff;padding:4px;}
        QSlider::groove:horizontal {background:#123554;height:5px;border-radius:2px;}
        QSlider::handle:horizontal {background:#1ed7ff;width:14px;margin:-5px 0;border-radius:7px;}
        QPushButton {color:#e5f9ff;background:#102c49;border:1px solid #1788c6;padding:8px;}
        QPushButton:hover {border-color:#35ddff;background:#12406a;}
    """)
    outer = QVBoxLayout(dialog)
    outer.addWidget(QLabel("NAVBAR BOTTOM · SLIM NEON"))
    values = load_appearance()
    sliders = {}
    for name, label, low, high in (("height", "Hauteur", 62, 94),
                                   ("opacity", "Opacité", 15, 85)):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(values[name])
        row.addWidget(slider, 1)
        value = QLabel(str(values[name]))
        slider.valueChanged.connect(lambda v, text=value: text.setText(str(v)))
        row.addWidget(value)
        outer.addLayout(row)
        sliders[name] = slider

    note = QLabel("La Navbar conserve tous les favoris, tâches et icônes système.")
    note.setWordWrap(True)
    outer.addWidget(note)
    actions = QHBoxLayout()
    cancel = QPushButton("ANNULER")
    save = QPushButton("APPLIQUER")
    cancel.clicked.connect(dialog.reject)
    save.clicked.connect(dialog.accept)
    actions.addWidget(cancel)
    actions.addWidget(save)
    outer.addLayout(actions)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    values = {k: s.value() for k, s in sliders.items()}
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, CONFIG)
    dock.settings.bottom_dock_height = values["height"]
    dock.settings.bottom_nav_opacity = values["opacity"]
    dock.apply_settings(dock.settings)
    dock.row.setContentsMargins(16, 11, 16, 11)
    dock.row.setSpacing(5)
    dock.body.update()


def main():
    app = QApplication([])
    app.setApplicationName("N3XV5 Bottom Navbar Slim")
    app.setQuitOnLastWindowClosed(True)
    dock = new_dock()
    dock.settings_requested.connect(lambda: show_appearance(dock))
    dock.quit_requested.connect(app.quit)
    dock.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

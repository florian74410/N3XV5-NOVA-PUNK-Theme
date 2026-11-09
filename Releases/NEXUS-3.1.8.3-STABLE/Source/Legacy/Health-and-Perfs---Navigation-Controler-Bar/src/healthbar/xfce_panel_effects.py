"""Read-only transparent PCB/electron pulse overlay for the EXISTING Xfce panel.

It never receives mouse events, so every original launcher and systray icon
continues to work. The geometry follows the native panel on X11; the overlay
does not change the panel's original height.
"""
from __future__ import annotations

import math
import os
import sys
import time

from PySide6.QtCore import QPointF, Qt, QTimer, QRect, QRectF
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget

from .overlay import apply_all_workspaces, apply_priority
from .xfce_panel_skin import PALETTES


def _is_bottom_native_panel(rect, screen_geometry):
    """Bottom anchored, sufficiently wide visible native panel."""
    if rect.width() < 120 or rect.height() < 15 or rect.height() > 210:
        return False
    edge = screen_geometry.y() + screen_geometry.height()
    return (abs(rect.bottom() + 1 - edge) <= 16
            and rect.right() >= screen_geometry.left()
            and rect.left() <= screen_geometry.right())


def panel_x11_bounds(screen_geometry):
    """Locate the REAL xfce4-panel window from X11 clients or their descendants.

    Xfwm4 does not guarantee the panel to be an immediate root-window child:
    recurse through window wrappers and prefer the widest bottom-anchored
    visible native panel. Never synthesize a second system tray.
    """
    if not sys.platform.startswith("linux") or not os.environ.get("DISPLAY"):
        return None
    try:
        from Xlib import X, display, error
        connection = display.Display()
        try:
            root = connection.screen().root
            candidates = []
            seen = set()
            pending = [(root, 0)]
            while pending and len(seen) < 1200:
                parent, depth = pending.pop()
                if depth > 5:
                    continue
                try:
                    children = parent.query_tree().children
                except (error.XError, OSError, ValueError):
                    continue
                for window in children:
                    xid = window.id
                    if xid in seen:
                        continue
                    seen.add(xid)
                    try:
                        klass = " ".join(window.get_wm_class() or ()).lower()
                        title = (window.get_wm_name() or "").lower()
                        attrs = window.get_attributes()
                        if ("xfce4-panel" in klass or "xfce4-panel" in title) and (
                                attrs.map_state == X.IsViewable):
                            rect = window.get_geometry()
                            pos = window.translate_coords(root, 0, 0)
                            bounds = QRect(pos.x, pos.y, rect.width, rect.height)
                            if _is_bottom_native_panel(bounds, screen_geometry):
                                candidates.append(bounds)
                        # Children may contain the real top-level Xfce panel
                        # even when the WM decorates or reparents the window.
                        if depth < 5:
                            pending.append((window, depth+1))
                    except (error.XError, OSError, ValueError, TypeError, AttributeError):
                        continue
            return max(candidates, key=lambda r: (r.width(), r.height())) if candidates else None
        finally:
            connection.close()
    except (ImportError, OSError, ValueError, RuntimeError):
        return None


class XFCEPanelCircuitEffects(QWidget):
    """Click-through overlay: narrow cyber traces, pulses and microchip nodes."""
    def __init__(self, settings):
        super().__init__(None)
        self.settings = settings
        self._phase = 0.0
        self._native_bounds = None
        flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                 Qt.WindowType.WindowStaysOnTopHint |
                 Qt.WindowType.WindowDoesNotAcceptFocus |
                 Qt.WindowType.WindowTransparentForInput)
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.poller = QTimer(self)
        self.poller.setInterval(900)
        self.poller.timeout.connect(self.locate_native_panel)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.tick)
        self.poller.start()
        self.locate_native_panel()

    def locate_native_panel(self):
        if (not getattr(self.settings, "xfce_skin_enabled", False)
                or self.settings.xfce_skin_fx_intensity == 0):
            self.hide()
            self.timer.stop()
            return
        screens = QApplication.screens()
        if not screens:
            self.hide()
            return
        screen = screens[min(self.settings.screen, len(screens)-1)]
        rect = panel_x11_bounds(screen.geometry())
        if rect is None:
            self.hide()
            self.timer.stop()
            self._native_bounds = None
            return
        if self._native_bounds != rect:
            self._native_bounds = rect
            self.setGeometry(rect)
        if not self.isVisible():
            self.show()
            apply_priority(self, True)
            from .overlay import schedule_all_workspaces
            schedule_all_workspaces(self)
        if not self.timer.isActive():
            self.timer.start()

    def tick(self):
        if self.isVisible():
            self._phase = time.monotonic() % 12 / 12
            self.update()
        else:
            self.timer.stop()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        if width < 60 or height < 12:
            p.end()
            return
        theme = PALETTES.get(self.settings.theme, PALETTES["blue-neon"])
        accent = QColor(theme[0])
        soft = QColor(theme[1])
        strength = max(0.0, min(1.0, self.settings.xfce_skin_fx_intensity/100.0))
        if strength == 0:
            p.end()
            return
        alpha = round(170 * strength)
        accent.setAlpha(alpha)
        soft.setAlpha(round(125 * strength))

        # Microtraces only in the top/bottom 4px and at the endpoints:
        # they never paint over the native XFCE icons or tray hit targets.
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(soft, 1))
        p.drawLine(QPointF(0, 2), QPointF(width, 2))
        p.drawLine(QPointF(0, height-2), QPointF(width, height-2))
        for x in range(20, width-10, 52):
            p.setPen(QPen(soft, .7))
            p.drawLine(QPointF(x, 1.5), QPointF(x+9, 1.5))
            p.drawLine(QPointF(x+9, 1.5), QPointF(x+14, 4.5))
            p.drawLine(QPointF(x+14, 4.5), QPointF(x+32, 4.5))
            p.setPen(QPen(accent, 1))
            p.drawEllipse(QPointF(x+32, 4.5), 1.4, 1.4)
        # Subminiature silicon nodes are confined to the thin upper edge.
        # No added row: all existing launcher and systray hit zones remain native.
        for chip_x in range(108, width-35, 224):
            core = QColor(theme[0]); core.setAlpha(round(35*strength))
            p.setPen(QPen(soft, .7))
            p.setBrush(core)
            p.drawRoundedRect(QRectF(chip_x, .5, 18, 7), 1.2, 1.2)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(chip_x+5, 2.3, 8, 3.1))
            for pin in (3, 8, 13):
                p.drawLine(QPointF(chip_x+pin, 0), QPointF(chip_x+pin, 1.5))
                p.drawLine(QPointF(chip_x+pin, 6.9), QPointF(chip_x+pin, 8.3))
        for x in (9, width-10):
            p.setPen(QPen(accent, 1))
            p.drawEllipse(QPointF(x, height-4), 2.4, 2.4)

        # Cyber chassis — layered angular endcaps, PCB vias and transistor banks.
        # Content remains click-through: all art stays at the panel's edges.
        p.save()
        edge = QColor(theme[0]);edge.setAlpha(round(190*strength))
        for mirrored in (False, True):
            p.save()
            if mirrored:
                p.translate(width, 0)
                p.scale(-1, 1)
            p.setPen(QPen(edge, 1.3))
            upper = QPainterPath(QPointF(0, 11))
            for x,y in ((5,6),(17,6),(25,1.5),(35,1.5)):
                upper.lineTo(x,y)
            p.drawPath(upper)
            lower = QPainterPath(QPointF(0, height-11))
            for x,y in ((5,height-6),(17,height-6),(25,height-1.5),(35,height-1.5)):
                lower.lineTo(x,y)
            p.drawPath(lower)
            for px in (7,13,19):
                p.setPen(QPen(soft,.8))
                p.drawLine(QPointF(px,1), QPointF(px+4,3))
                p.drawLine(QPointF(px,height-1), QPointF(px+4,height-3))
            p.restore()
        for k in range(0, max(0,width-80), 104):
            p.setPen(QPen(soft,.8))
            upper=QPainterPath(QPointF(k+39,3))
            upper.lineTo(k+50,3);upper.lineTo(k+54,6);upper.lineTo(k+72,6)
            p.drawPath(upper)
            lower=QPainterPath(QPointF(k+39,height-3))
            lower.lineTo(k+50,height-3)
            lower.lineTo(k+54,height-6);lower.lineTo(k+72,height-6)
            p.drawPath(lower)
            via=QColor(theme[0]);via.setAlpha(round(150*strength))
            p.setPen(QPen(via,1))
            p.drawEllipse(QPointF(k+72,6),1.4,1.4)
            p.drawEllipse(QPointF(k+72,height-6),1.4,1.4)
        for k in range(130,width-30,238):
            p.setPen(QPen(soft,.8))
            p.drawRoundedRect(QRectF(k,height-9,27,7),1.2,1.2)
            for j in range(5):
                on=(self._phase*7+j*.37+k*.01)%1<.38
                led=QColor(theme[0]);led.setAlpha(round((210 if on else 44)*strength))
                p.setPen(QPen(led,1.4))
                p.drawLine(QPointF(k+3+j*5,height-7),QPointF(k+3+j*5,height-5))
        p.restore()

        # Electron pulses travel in opposite directions around the PCB rails.
        for fraction, y, direction in ((self._phase, 2.5, 1),
                                        ((self._phase+.43)%1, height-2.5, -1)):
            cx = fraction*width if direction > 0 else (1-fraction)*width
            trail = QLinearGradient(cx-27*direction, y, cx+14*direction, y)
            bright = QColor(theme[0])
            bright.setAlpha(round(230 * strength))
            dark = QColor(theme[0]);dark.setAlpha(0)
            trail.setColorAt(0, dark)
            trail.setColorAt(.65, bright)
            trail.setColorAt(1, dark)
            p.setPen(QPen(QBrush(trail), 2.8))
            p.drawLine(QPointF(cx-27*direction, y), QPointF(cx+14*direction, y))
            p.setPen(QPen(bright, 1.4))
            p.drawEllipse(QPointF(cx, y), 2.1, 2.1)
        p.end()

    def closeEvent(self, event):
        self.poller.stop()
        self.timer.stop()
        super().closeEvent(event)

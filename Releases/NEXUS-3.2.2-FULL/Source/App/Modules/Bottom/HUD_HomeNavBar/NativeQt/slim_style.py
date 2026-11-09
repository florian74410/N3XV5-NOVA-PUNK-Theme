"""N3XV5 V2.4.0 bottom bar tuning.

Refines the legacy NovaBar BottomDock without touching task lifecycle.
Goals:
- thicker task tabs for better integration in the bar
- right system block visually closer in size to its outer container
- preserve animated active-task neon
"""
from __future__ import annotations
import math
import time

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QLinearGradient


def apply_skin():
    from healthbar import cockpit_style, bottom_dock
    from PySide6.QtCore import QSize, QTimer

    bottom_dock.bottom_height = lambda settings: max(48, min(110, int(settings.bottom_dock_height)))
    original_apply_settings = bottom_dock.BottomDock.apply_settings
    original_task_paint = bottom_dock.TaskButton.paintEvent
    original_dock_init = bottom_dock.BottomDock.__init__
    original_dock_refresh = bottom_dock.BottomDock.refresh
    cut_path = cockpit_style.cut_path

    def glow(p, path, color, width=1.2):
        color = QColor(color)
        p.setBrush(Qt.BrushStyle.NoBrush)
        soft = QColor(color); soft.setAlpha(20)
        p.setPen(QPen(soft, max(1.2, width + 1.3))); p.drawPath(path)
        color.setAlpha(188)
        p.setPen(QPen(color, min(0.95, width * .65))); p.drawPath(path)

    def apply_compact_settings(self, settings):
        original_apply_settings(self, settings)
        height = self.height()
        # More presence: slightly taller widgets and tighter chrome.
        cell = max(24, min(42, height - 10))
        icon = max(16, min(28, cell - 8))
        for button in self.indicators.values():
            button.setFixedSize(cell, cell)
            button.setIconSize(QSize(icon, icon))
        self.clock.setFixedSize(max(72, min(102, round(height * 1.34))), cell)
        self.preferences.setFixedSize(cell, cell)
        self.preferences.setIconSize(QSize(icon, icon))
        # V3.1.8: do not enlarge favorites back to 42px after BottomDock applied sizes.
        # The launcher/menu button is intentionally slightly larger than pinned apps.
        for button in self.launchers.findChildren(bottom_dock.QToolButton):
            if isinstance(button,bottom_dock.GlitchFavoriteButton):
                button.setFixedSize(29,34)
                button.setIconSize(QSize(22,22))
            else:
                button.setFixedSize(36,36)
                button.setIconSize(QSize(27,27))
        vertical = max(2, (height - cell) // 2)
        self.row.setContentsMargins(7, vertical, 7, vertical)
        self.row.setSpacing(4)
        self.tasks.setSpacing(4)
        try:
            self.pins.setSpacing(1)
            self.pins.setContentsMargins(0,0,0,0)
            # Content-sized dark favorites housing, not the old oversized cell width.
            from PySide6.QtWidgets import QSizePolicy
            self.launchers.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Preferred)
            self.launchers.setFixedWidth(sum(self.pins.itemAt(i).widget().width()
                        for i in range(self.pins.count()) if self.pins.itemAt(i).widget())
                        + max(0,self.pins.count()-1)*self.pins.spacing())
        except Exception:
            pass
        # Try to let the right system cluster breathe and fill its zone.
        try:
            self.indicators.setSpacing(3)
        except Exception:
            pass

    # N3XV5 V2.4.5 system controls responsive sizing
    def _retune_system_controls(self):
        from PySide6.QtWidgets import QToolButton
        height=max(36,int(self.height()))
        cell=max(24,min(28,height-46))
        symbol=max(15,min(19,cell-7))
        # V3.1.8.3: small controls should NOT create oversized vertical row margins:
        # tasks can otherwise exceed the row's usable height and drop below the shell.
        self.row.setContentsMargins(5,3,5,3)
        self.row.setSpacing(2)
        # Center the widgets vertically without taking space away from task tabs.
        for control in [*self.indicators.values(),self.preferences,self.clock,self.tray_widget]:
            self.row.setAlignment(control, Qt.AlignmentFlag.AlignVCenter)
        controls=[*self.indicators.values(),self.preferences]
        for button in controls:
            button.setFixedSize(cell,cell)
            button.setIconSize(QSize(symbol,symbol))
            button.setStyleSheet('QToolButton{border:0;background:transparent;padding:0px;color:#ebfaff;} '
                'QToolButton:hover{background:rgba(22,108,160,100);border:1px solid #29cfff;border-radius:5px;}')
        # Clock has no QIcon, so match its baseline and width to the icon row.
        self.clock.setFixedSize(max(64,min(84,round(cell*2.55))),cell)
        self.clock.setStyleSheet('QToolButton{background:transparent;border:0;padding:0px;'
            'font-size:15px;color:#ebfaff;}')
        if getattr(self,'tray_row',None) is not None:
            self.tray_row.setContentsMargins(0,0,0,0)
            self.tray_row.setSpacing(1)
            for tray_button in self.tray_widget.findChildren(QToolButton):
                tray_button.setFixedSize(cell,cell)
                tray_button.setIconSize(QSize(symbol,symbol))
                tray_button.setStyleSheet('QToolButton{background:transparent;border:0;padding:0px;}')
        self.body.update()

    _prior_compact_settings = apply_compact_settings
    def apply_compact_settings(self, settings):
        _prior_compact_settings(self,settings)
        _retune_system_controls(self)

    _prior_update_tray = bottom_dock.BottomDock.update_tray
    def _retuned_tray(self,*args,**kwargs):
        result=_prior_update_tray(self,*args,**kwargs)
        _retune_system_controls(self)
        return result

    def paint(self, event):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if w < 30 or h < 20:
            p.end(); return
        outer = cut_path(QRectF(1, 1, w - 2, h - 2), 9)
        fill = QLinearGradient(0, 0, 0, h)
        fill.setColorAt(0, QColor('#0b2945'))
        fill.setColorAt(.28, QColor('#071726'))
        fill.setColorAt(.70, QColor('#04111e'))
        fill.setColorAt(1, QColor('#092039'))
        p.save(); p.setOpacity(max(.15, min(1, self.glass_opacity / 100)))
        p.fillPath(outer, fill); p.restore()
        glow(p, outer, '#16cfff', .8)
        p.setPen(QPen(QColor(17, 96, 172, 87), .65))
        p.drawPath(cut_path(QRectF(3, 3, w - 6, h - 6), 7))
        p.setClipPath(outer)
        # N3XV5 V2.4.1: right system housing fills the inner dock height
        regions = list(self.regions() if callable(getattr(self, 'regions', None)) else [])
        for index, rect in enumerate(regions):
            r = QRectF(rect)
            # The last region is the system tray/clock/settings cluster, as
            # provided by BottomDock.housing_regions(). Its old top=13 and
            # height=h-26 left a narrow grey strip in a taller cyan housing.
            system_housing = len(regions) >= 2 and index == len(regions) - 1
            if system_housing:
                left = max(5.0, r.left() - 5.0)
                right = min(float(w - 5), r.right() + 5.0)
                # Match the launcher housing's *visual height* while allowing
                # each side's width to follow its own contents.
                r = QRectF(left, 5.0, max(0.0, right - left), max(0.0, h - 10.0))
            if r.width() < 28 or r.height() < 15:
                continue
            # N3XV5 V2.4.7.1: shared midpoint opacity, left and right
            # Match the *same* alpha on both housings. Middle ground between
            # previous launcher (110..170) and system (244..248) treatments.
            g = QLinearGradient(0, r.top(), 0, r.bottom())
            g.setColorAt(0, QColor(10, 32, 47, 177))
            g.setColorAt(.52, QColor(6, 20, 33, 209))
            g.setColorAt(1, QColor(3, 14, 26, 207))
            shape = cut_path(r, 8)
            p.fillPath(shape, g)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(22, 106, 178, 170 if system_housing else 130), .7 if system_housing else .55))
            p.drawPath(shape)
        phase = float(getattr(self, 'phase', 0))
        for edge, sign in ((4, 1), (h - 5, -1)):
            p.setPen(QPen(QColor(21, 125, 227, 88), .7))
            p.drawLine(QPointF(24, edge), QPointF(w - 24, edge))
            for x in range(70, w - 45, 168):
                track = QPainterPath(QPointF(x, edge))
                track.lineTo(x + 13, edge)
                track.lineTo(x + 19, edge + sign * 3)
                track.lineTo(x + 28, edge + sign * 3)
                p.setPen(QPen(QColor(14, 157, 218, 95), .6)); p.drawPath(track)
                if x // 168 % 5 == 1:
                    p.setPen(QPen(QColor('#ae1934'), 1))
                    p.drawLine(QPointF(x + 12, edge), QPointF(x + 18, edge + sign * 2))
            cx = 30 + (w - 60) * ((phase / (2 * math.pi) + (0.28 if sign < 0 else 0)) % 1)
            line = QPainterPath(QPointF(cx - 8, edge)); line.lineTo(cx + 8, edge)
            glow(p, line, '#20dfff', .9)
        p.setClipping(False)
        p.end()

    def paint_active_task(self, event):
        # NEXUS V3.1.7 PHOTON: replaces the old orbiting border spark.
        original_task_paint(self, event)
        active=bool(self.property('active'))
        hovered=self.underMouse()
        if not (active or hovered) or self.width()<=35 or self.height()<=20:
            return
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        y=self.height()-5.5
        x0=12.0
        length=max(1.0,self.width()-24.0)
        painter.setPen(QPen(QColor(13,116,181,135),1.0))
        painter.drawLine(QPointF(x0,y),QPointF(x0+length,y))
        # The active tab retains a continuous marker. A laser passes on hover.
        if active:
            painter.setPen(QPen(QColor(23,226,255,200),2.0))
            painter.drawLine(QPointF(x0,y),QPointF(x0+length,y))
        if hovered:
            phase=(time.monotonic()*1.35)%1.0
            cx=x0+length*phase
            for span,alpha,thick in ((15,35,5.0),(9,95,3.0),(3,245,1.7)):
                painter.setPen(QPen(QColor(80,236,255,alpha),thick))
                painter.drawLine(QPointF(max(x0,cx-span),y),QPointF(min(x0+length,cx+span),y))
        painter.end()

    def refresh_fitted_tasks(self):
        original_dock_refresh(self)
        widgets = [self.tasks.itemAt(i).widget() for i in range(self.tasks.count())]
        widgets = [w for w in widgets if isinstance(w, bottom_dock.TaskButton)]
        if not widgets:
            return
        viewport = max(1, self.tasks_area.viewport().width())
        margins = self.tasks.contentsMargins()
        free = max(1, viewport - margins.left() - margins.right() - self.tasks.spacing() * max(0, len(widgets) - 1) - 5)
        tab_w = max(58, min(290, free // len(widgets)))
        # V3.1.8.3: respect the real available row height plus a little breathing room.
        tab_h = max(28, min(46, self.height() - 14))
        icon = max(14, min(28, tab_h - 12))
        for widget in widgets:
            widget.setMinimumWidth(40)
            widget.setMaximumWidth(max(58, tab_w))
            widget.setFixedWidth(tab_w)
            widget.setFixedHeight(tab_h)
            widget.setIconSize(bottom_dock.QSize(icon, icon))

    def dock_init_with_active_fx(self, *args, **kwargs):
        original_dock_init(self, *args, **kwargs)
        self._n3xvs_active_fx = QTimer(self)
        self._n3xvs_active_fx.setInterval(170)
        def tick():
            if not self.isVisible() or self.collapsed:
                return
            for task in self.findChildren(bottom_dock.TaskButton):
                if task.isVisible() and bool(task.property('active')):
                    task.update()
        self._n3xvs_active_fx.timeout.connect(tick)
        self._n3xvs_active_fx.start()

    cockpit_style.CockpitFrame.paintEvent = paint
    bottom_dock.glow = glow
    bottom_dock.BottomDock.apply_settings = apply_compact_settings
    bottom_dock.BottomDock.update_tray = _retuned_tray
    bottom_dock.TaskButton.paintEvent = paint_active_task
    bottom_dock.BottomDock.__init__ = dock_init_with_active_fx
    bottom_dock.BottomDock.refresh = refresh_fitted_tasks
    # NEXUS_V314_BOTTOM_GROUPS
    from App.Modules.Bottom.HUD_HomeNavBar.NativeQt.n3xvs_v31_dock import install as _nexus_v31_install_dock
    _nexus_v31_install_dock(bottom_dock)
    # NEXUS 3.1.4: 2/3-scale system icons; leave launcher and tasks unchanged.
    _nexus_prev_apply_settings = bottom_dock.BottomDock.apply_settings
    def _nexus_scaled_system_icons(self, settings):
        _nexus_prev_apply_settings(self, settings)
        from PySide6.QtCore import QSize
        controls=list(self.indicators.values()) + [self.preferences]
        for control in controls:
            current=control.iconSize()
            if current.width()>0 and current.height()>0:
                control.setIconSize(QSize(max(10,round(current.width()*2/3)),
                                          max(10,round(current.height()*2/3))))
    bottom_dock.BottomDock.apply_settings = _nexus_scaled_system_icons
    # NEXUS_V316_TRAY_ICONS

    # NEXUS V3.1.6: shrink tray + system icons to 2/3 of original reference.
    # The icons may be recreated by StatusNotifierHost: rescale after each refresh.
    def _nexus_v316_fit_icons(self):
        from PySide6.QtCore import QSize
        cell=max(21,min(36,self.height()-16))
        fixed=max(11,round(max(15,cell-5)*2/3))
        prefs=max(11,round(max(15,cell-7)*2/3))
        for button in self.indicators.values():
            button.setIconSize(QSize(fixed,fixed))
        self.preferences.setIconSize(QSize(prefs,prefs))
        for button in self.tray_widget.findChildren(bottom_dock.QToolButton):
            # Tray buttons are dynamically created with a 28px icon size.
            button.setIconSize(QSize(19,19))
    _v316_prev_apply=bottom_dock.BottomDock.apply_settings
    def _v316_apply(self,settings):
        _v316_prev_apply(self,settings)
        _nexus_v316_fit_icons(self)
    bottom_dock.BottomDock.apply_settings=_v316_apply
    _v316_prev_tray=bottom_dock.BottomDock.update_tray
    def _v316_tray(self,*args,**kwargs):
        result=_v316_prev_tray(self,*args,**kwargs)
        _nexus_v316_fit_icons(self)
        return result
    bottom_dock.BottomDock.update_tray=_v316_tray

        # N3XV5 V2.4.6 — full XFCE/X11 task menu
    from App.Modules.Bottom.HUD_HomeNavBar.NativeQt.n3xvs_task_actions import install as install_task_actions
    install_task_actions(bottom_dock)

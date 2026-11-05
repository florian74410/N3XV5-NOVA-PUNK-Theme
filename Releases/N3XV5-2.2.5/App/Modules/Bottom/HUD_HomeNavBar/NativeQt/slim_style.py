"""Paint-only N3XV5 Slim treatment for the original NovaBar BottomDock.

Do not change its task/window lifecycle, tray, application icons, or close events.
"""
from __future__ import annotations
import math
import time

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QLinearGradient


def apply_skin():
    from healthbar import cockpit_style, bottom_dock
    cut_path=cockpit_style.cut_path

    def glow(p, path, color, width=1.2):
        color=QColor(color)
        p.setBrush(Qt.BrushStyle.NoBrush)
        soft=QColor(color);soft.setAlpha(20)
        p.setPen(QPen(soft,max(1.2,width+1.3)));p.drawPath(path)
        color.setAlpha(188)
        p.setPen(QPen(color,min(0.95,width*.65)));p.drawPath(path)

    def paint(self,event):
        p=QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(self.rect(),Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height()
        if w<30 or h<20:
            p.end();return
        outer=cut_path(QRectF(1,1,w-2,h-2),9)
        fill=QLinearGradient(0,0,0,h)
        fill.setColorAt(0,QColor('#0b2945'))
        fill.setColorAt(.28,QColor('#071726'))
        fill.setColorAt(.70,QColor('#04111e'))
        fill.setColorAt(1,QColor('#092039'))
        p.save();p.setOpacity(max(.15,min(1,self.glass_opacity/100)))
        p.fillPath(outer,fill);p.restore()
        glow(p,outer,'#16cfff',.8)
        # One subdued inner rule instead of the old double-metallic bezel.
        p.setPen(QPen(QColor(17,96,172,87),.65))
        p.drawPath(cut_path(QRectF(3,3,w-6,h-6),7))
        p.setClipPath(outer)
        for rect in (self.regions() if callable(getattr(self,'regions',None)) else []):
            r=QRectF(rect)
            if r.width()<28 or r.height()<15:continue
            g=QLinearGradient(0,r.top(),0,r.bottom())
            g.setColorAt(0,QColor(10,39,63,110));g.setColorAt(1,QColor(2,18,33,170))
            shape=cut_path(r,8)
            p.fillPath(shape,g)
            p.setPen(QPen(QColor(22,106,178,130),.55));p.drawPath(shape)
        phase=float(getattr(self,'phase',0))
        for edge,sign in ((4,1),(h-5,-1)):
            p.setPen(QPen(QColor(21,125,227,88),.7))
            p.drawLine(QPointF(24,edge),QPointF(w-24,edge))
            for x in range(70,w-45,168):
                track=QPainterPath(QPointF(x,edge))
                track.lineTo(x+13,edge)
                track.lineTo(x+19,edge+sign*3)
                track.lineTo(x+28,edge+sign*3)
                p.setPen(QPen(QColor(14,157,218,95),.6));p.drawPath(track)
                if x//168%5==1:
                    p.setPen(QPen(QColor('#ae1934'),1))
                    p.drawLine(QPointF(x+12,edge),QPointF(x+18,edge+sign*2))
            cx=30+(w-60)*((phase/(2*math.pi)+(0.28 if sign<0 else 0))%1)
            line=QPainterPath(QPointF(cx-8,edge));line.lineTo(cx+8,edge)
            glow(p,line,'#20dfff',.9)
        p.setClipping(False)
        p.end()

    cockpit_style.CockpitFrame.paintEvent=paint
    bottom_dock.glow=glow

    # Preserve and emphasize the original animated neon that outlines ACTIVE
    # task buttons. No task-management, click or tray code is replaced.
    from PySide6.QtCore import QTimer
    original_task_paint = bottom_dock.TaskButton.paintEvent
    original_dock_init = bottom_dock.BottomDock.__init__

    def paint_active_task(self, event):
        original_task_paint(self, event)
        if not bool(self.property('active')) or self.width() <= 35 or self.height() <= 20:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        frame = cut_path(QRectF(2.5, 2.5, self.width()-5, self.height()-5), 8)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(20, 170, 255, 105), 0.7))
        painter.drawPath(frame)
        phase = (time.monotonic() * 0.16) % 1.0
        start = frame.pointAtPercent(phase)
        end = frame.pointAtPercent(min(0.999, phase + 0.025))
        if (end-start).manhattanLength() < 60:
            painter.setPen(QPen(QColor(35, 222, 255, 180), 1.3))
            painter.drawLine(start, end)
        painter.end()

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

    bottom_dock.TaskButton.paintEvent = paint_active_task
    bottom_dock.BottomDock.__init__ = dock_init_with_active_fx

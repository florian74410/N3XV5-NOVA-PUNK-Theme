"""Native animated vector identity: binary signature and energy-routing microchip."""
import math
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


from .ui_kit import QColor

class BrandHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(138)
        self.frame = 0
        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def tick(self):
        self.frame += 1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width()/820, self.height()/138)
        p.setPen(QPen(QColor("#00649b"), 1))
        for y in (5, 128):
            p.drawLine(12, y, 808, y)
        # Main mark: paired chevrons and an electronic nexus.
        path = QPainterPath(QPointF(24, 59))
        for x,y in ((49,26),(75,59),(49,92),(24,59),(49,48),(75,59)):
            path.lineTo(x,y)
        for width, color in ((9, "#153d63"), (3, "#00c9ff"), (1, "#a3ff57")):
            p.setPen(QPen(QColor(color), width)); p.drawPath(path)
        p.setFont(QFont("DejaVu Sans", 21, QFont.Weight.Bold))
        for delta, alpha in ((2, 45), (0, 255)):
            color=QColor("#9eff65");color.setAlpha(alpha);p.setPen(color)
            p.drawText(QPointF(99+delta, 54), "CYBER NEXUS HUD")
        p.setFont(QFont("DejaVu Sans", 10));p.setPen(QColor("#8ddaff"))
        p.drawText(QPointF(102, 76), "NOVABAR / VOTRE PC. VOTRE COCKPIT.")
        p.setFont(QFont("DejaVu Sans", 9));p.setPen(QColor("#cae6ff"))
        p.drawText(QPointF(102, 109), "© 2026  0verF1ow  &  La Puce")
        # Transparent Matrix signature, cycling the specified bit rows.
        rows=("101011", "101101", "001010")
        p.setFont(QFont("DejaVu Sans Mono", 11, QFont.Weight.Bold))
        offset=(self.frame//5)%18
        stream="".join(rows)
        for r in range(3):
            color=QColor("#6eff91" if r==self.frame//5%3 else "#16b65b");p.setPen(color)
            row=(stream[offset:]+stream[:offset])[r*6:r*6+6]
            p.drawText(QPointF(599, 46+r*20), row)
        # Chip + 4 PCB routes on every side, inside a compact 110px emblem.
        p.save();p.translate(716, 17)
        phase=(self.frame%100)/100
        routes=[]
        for side in range(4):
            for i in range(4):
                path=QPainterPath(QPointF(-12+i*8, -18))
                for x,y in ((-12+i*8,-27),(-20+i*12,-35),(-20+i*12,-46)):
                    path.lineTo(x,y)
                from PySide6.QtGui import QTransform
                transform=QTransform();transform.translate(43,50);transform.rotate(side*90)
                routes.append(transform.map(path))
        for i,path in enumerate(routes):
            p.setPen(QPen(QColor("#165478"),1.5));p.drawPath(path)
            if phase > .28:
                energy=(phase-.28)/.72
                part=path.pointAtPercent(min(1,energy))
                color=QColor.fromHsv((int(self.frame*3)+i*17)%360,210,255)
                p.setPen(QPen(color,3));p.drawEllipse(part,2.3,2.3)
        p.setBrush(QColor("#020914"));p.setPen(QPen(QColor("#18bfff"),2))
        p.drawRoundedRect(QRectF(25,32,36,36),5,5)
        p.setPen(QPen(QColor("#2774dc"),1));p.drawRect(QRectF(32,39,22,22))
        if phase < .4:
            radius=9*(1-phase/.4)
            center=QPointF(43, 10+phase/.4*40)
            grad=QRadialGradient(center,max(1,radius*2.5));grad.setColorAt(0,QColor("#eaffb2"));grad.setColorAt(.35,QColor("#6dff9c"));grad.setColorAt(1,QColor("#0000ff00"))
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(grad);p.drawEllipse(center,radius*2.5,radius*2.5)
        p.restore()
        from .ui_kit import chip
        chip(p,QRectF(716,17,86,100))
        p.end()

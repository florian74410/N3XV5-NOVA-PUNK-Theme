"""Transparent network chart: two byte-rate curves and independent ICMP bars."""
from collections import deque
import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget

UP = '#39ef7d'
DOWN = '#ff4f61'
PING = '#388dff'


def valid(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


class NetworkChart(QWidget):
    WINDOW = 120
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = deque(maxlen=240)
        self.last_ping_at = None
        self.setFixedHeight(118)
        self.setAccessibleName('Historique réseau : UP vert, DOWN rouge, ping bleu')
        self.setToolTip('120 secondes · débits à gauche, ping en ms à droite · absence de sonde = interruption du tracé')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def record(self, data):
        now = data.get('net_sample_at')
        if not valid(now) or (self.points and now <= self.points[-1]['at']):
            return
        ping_at = data.get('net_ping_sample_at')
        ping = data.get('net_ping_ms') if ping_at != self.last_ping_at else None
        if ping_at is not None:
            self.last_ping_at = ping_at
        self.points.append({'at': now, 'up': data.get('net_up_mbs'), 'down': data.get('net_down_mbs'), 'ping': ping, 'interface': data.get('net_interface')})
        while self.points and self.points[0]['at'] < now-self.WINDOW:
            self.points.popleft()
        self.update()

    def scales(self):
        rates = [row[key] for row in self.points for key in ('up','down') if valid(row[key])]
        pings = [row['ping'] for row in self.points if valid(row['ping'])]
        return max(.001, max(rates, default=0)*1.15), max(10, max(pings, default=0)*1.15)

    def label(self, painter, x, y, value, color='#eaf7ff'):
        font=QFont('DejaVu Sans');font.setPixelSize(10);font.setBold(True)
        path=QPainterPath();path.addText(QPointF(x,y),font,value)
        painter.setPen(QPen(QColor('#010813'),3));painter.setBrush(QColor(color));painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen);painter.drawPath(path)

    def paintEvent(self, event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.label(p,4,12,'UP',UP);self.label(p,55,12,'DOWN',DOWN);self.label(p,127,12,'PING',PING)
        self.label(p,max(205,self.width()-105),12,'120 s · ICMP 10 s')
        area=QRectF(43,32,max(1,self.width()-90),65)
        rate_max,ping_max=self.scales()
        unit='MB/s' if rate_max>=1 else 'kB/s'
        display_max=rate_max if unit=='MB/s' else rate_max*1000
        self.label(p,0,27,f'{display_max:.1f} {unit}')
        self.label(p,self.width()-44,27,f'{ping_max:.0f} ms',PING)
        for fraction in (0,.5,1):
            y=area.top()+fraction*area.height()
            p.setPen(QPen(QColor(115,170,195,90),.6));p.drawLine(QPointF(area.left(),y),QPointF(area.right(),y))
        self.label(p,area.left(),114,'−120 s');self.label(p,area.center().x()-18,114,'−60 s');self.label(p,area.right()-25,114,'0 s')
        if not self.points:
            self.label(p,area.left()+8,area.center().y(),'En attente de mesures…');p.end();return
        end=self.points[-1]['at']
        def x(row):return area.right()-(end-row['at'])/self.WINDOW*area.width()
        p.save();p.setClipRect(area.adjusted(-1,-1,1,1))
        for row in self.points:
            if valid(row['ping']):
                h=row['ping']/ping_max*area.height()
                bar=QRectF(x(row)-3,area.bottom()-h,6,max(1,h))
                p.setPen(QPen(QColor('#010813'),2));p.setBrush(QColor(56,141,255,160));p.drawRect(bar)
                p.setPen(QPen(QColor(PING),1));p.drawRect(bar)
        for key,color in [('down',DOWN),('up',UP)]:
            path=QPainterPath();connected=False;interface=None
            for row in self.points:
                if not valid(row[key]):connected=False;continue
                if interface != row['interface']:connected=False
                interface=row['interface']
                point=QPointF(x(row),area.bottom()-row[key]/rate_max*area.height())
                if connected:path.lineTo(point)
                else:path.moveTo(point)
                connected=True
                # Show a real single point without inventing an adjacent sample.
                p.setPen(QPen(QColor('#010813'),4));p.drawPoint(point)
                p.setPen(QPen(QColor(color),2));p.drawPoint(point)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor('#010813'),4));p.drawPath(path)
            p.setPen(QPen(QColor(color),1.8));p.drawPath(path)
        p.restore();p.end()

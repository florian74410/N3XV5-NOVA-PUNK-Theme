"""Resolution-independent metallic cockpit: bevels, luminous rails and real icon fallback."""
from pathlib import Path
import math
from PySide6.QtCore import Qt,QRectF,QPointF,QSize
from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen,QLinearGradient,QPolygonF,QIcon,QPixmap
from PySide6.QtWidgets import QFrame
from PySide6.QtSvg import QSvgRenderer
from .xfce_panel_skin import PALETTES
from .redblack_shell import active as redblack_active, paint_surface


def cut_path(rect,cut=12):
    x,y,w,h=rect.x(),rect.y(),rect.width(),rect.height();c=min(cut,h/3)
    p=QPainterPath();p.addPolygon(QPolygonF([QPointF(x+c,y),QPointF(x+w-c,y),QPointF(x+w,y+c),QPointF(x+w,y+h-c),QPointF(x+w-c,y+h),QPointF(x+c,y+h),QPointF(x,y+h-c),QPointF(x,y+c)]));p.closeSubpath();return p


def glow(p,path,color,width=1.2):
    c=QColor(color)
    for size,alpha in ((width+7,15),(width+4,35),(width+2,75)):
        c.setAlpha(alpha);p.setPen(QPen(c,size));p.drawPath(path)
    c.setAlpha(255);p.setPen(QPen(c,width));p.drawPath(path)


class CockpitFrame(QFrame):
    def __init__(self,theme='blue-neon',parent=None):
        super().__init__(parent);self.theme=theme;self.phase=0;self.glass_opacity=55
        self.setObjectName('cockpit');self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground,True)
        self.setAutoFillBackground(False)

    def paintEvent(self,event):
        if redblack_active(self.theme):
            p=QPainter(self)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(self.rect(),Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            paint_surface(p,QRectF(self.rect()).adjusted(2,2,-2,-2),
                          "dock",self.phase,self.underMouse())
            p.end()
            return
        p=QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(self.rect(),Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height();primary,secondary,_=PALETTES.get(self.theme,PALETTES['blue-neon'])
        outer=cut_path(QRectF(2,2,w-4,h-4),19)
        metal=QLinearGradient(0,0,0,h)
        for pos,col in ((0,'#34566b'),(.12,'#07121c'),(.24,'#183f56'),(.43,'#020912'),(.75,'#071c2c'),(.87,'#294c60'),(1,'#030a12')):metal.setColorAt(pos,QColor(col))
        p.save()
        p.setOpacity(max(.12,min(1,self.glass_opacity/100)))
        p.fillPath(outer,metal)
        p.restore()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save();p.setOpacity(.68+.23*(.5+.5*math.sin(self.phase)))
        glow(p,outer,secondary,1.5)
        p.restore()
        inner=cut_path(QRectF(9,9,w-18,h-18),14);glow(p,inner,primary,1.7)
        cavity=cut_path(QRectF(16,16,w-32,h-32),11)
        glass=QLinearGradient(0,16,0,h-16)
        for pos,col in ((0,'#0d2939'),(.18,'#071a29'),(.5,'#03101e'),(1,'#071625')):glass.setColorAt(pos,QColor(col))
        p.save();p.setOpacity(max(.1,min(1,self.glass_opacity/100)))
        p.fillPath(cavity,glass);p.restore();p.setPen(QPen(QColor('#43829a'),.7));p.drawPath(cavity)
        p.setClipPath(outer)
        # Separate metal housings for launchers and native indicators.
        for rect in self.regions() if callable(getattr(self,'regions',None)) else []:
            if rect.width()<30:continue
            r=QRectF(rect);housing=cut_path(r,12)
            g=QLinearGradient(0,r.top(),0,r.bottom());g.setColorAt(0,QColor('#24546b'));g.setColorAt(.2,QColor('#051320'));g.setColorAt(.8,QColor('#05111c'));g.setColorAt(1,QColor('#23495e'))
            p.fillPath(housing,g);p.setBrush(Qt.BrushStyle.NoBrush);glow(p,housing,primary,1.1)
            inset=cut_path(r.adjusted(3,3,-3,-3),9);p.setPen(QPen(QColor('#3c6e81'),.7));p.drawPath(inset)
            # Machined joints on both sides of each housing, with little light wells.
            for x in (r.left()-7,r.right()+7):
                p.setPen(QPen(QColor('#304958'),2));p.drawLine(QPointF(x,r.top()+10),QPointF(x,r.bottom()-10))
                p.setPen(QPen(QColor(primary),1.3));p.drawEllipse(QPointF(x,r.center().y()),2,2)
        # Layered top/bottom rails with inset vents, circuit traces, screws and indicator LEDs.
        for edge in (0,1):
            y=7 if edge==0 else h-8;sign=1 if edge==0 else -1
            for x in range(42,w-40,94):
                trace=QPainterPath(QPointF(x,y));trace.lineTo(x+15,y);trace.lineTo(x+20,y+sign*5);trace.lineTo(x+66,y+sign*5);trace.lineTo(x+72,y)
                glow(p,trace,secondary,.8)
                for k in range(4):
                    p.setPen(QPen(QColor('#274453'),2));p.drawLine(QPointF(x+4+k*5,y+sign*6),QPointF(x+8+k*5,y+sign*10))
                p.setPen(Qt.PenStyle.NoPen);c=QColor(primary);c.setAlpha(150 if (x//94+int(self.phase))%4 else 255);p.setBrush(c);p.drawRoundedRect(QRectF(x+43,y-1.5,11,2.5),1,1)
        for x in (8,w-9):
            for y in (h*.34,h*.67):
                p.setPen(QPen(QColor('#8da6b3'),.6));p.setBrush(QColor('#081420'));p.drawEllipse(QPointF(x,y),2,2)
                p.setPen(QPen(QColor('#3a5a6a'),.7));p.drawLine(QPointF(x-1,y+1),QPointF(x+1,y-1))
        p.setClipping(False);p.end()


_SVGS={
 'wifi':'<path d="M4 12q20-18 40 0M10 21q14-12 28 0M17 30q7-6 14 0"/><circle cx="24" cy="38" r="3" fill="currentColor" stroke="none"/>',
 'ethernet':'<path d="M10 6h28v25H10zM16 6v9m8-9v9m8-9v9M17 31v8h14v-8M24 39v6"/>',
 'volume':'<path d="M7 19h9L27 9v30L16 29H7zM33 17q8 7 0 14m5-21q15 14 0 28"/>',
 'muted':'<path d="M7 19h9L27 9v30L16 29H7zM33 18l11 12m0-12L33 30"/>',
 'bluetooth':'<path d="M23 3v42l15-12L12 12m0 24L38 15 23 3"/>',
 'battery':'<rect x="4" y="12" width="36" height="24" rx="3"/><path d="M44 19v10M10 18h23v12H10z"/>',
 'power':'<path d="M17 5v10m14-10v10M12 15h24v7a12 12 0 0 1-24 0zM24 34v10"/>',
 'bell':'<path d="M10 33c6-6-1-23 14-23s8 17 14 23zM20 40h8M24 5v5"/>',
 'shield':'<path d="M24 4 41 11v12c0 11-17 21-17 21S7 34 7 23V11zM18 24l5 5 10-13"/>',
 'settings':'<path d="m20 5 8 0 2 7 7-2 5 7-5 6 5 6-5 7-7-2-2 7h-8l-2-7-7 2-5-7 5-6-5-6 5-7 7 2z"/><circle cx="24" cy="23" r="7"/>',
 'apps':'<rect x="7" y="7" width="13" height="13" rx="2"/><rect x="28" y="7" width="13" height="13" rx="2"/><rect x="7" y="28" width="13" height="13" rx="2"/><rect x="28" y="28" width="13" height="13" rx="2"/>',
 'folder':'<path fill="#e9b545" stroke="#ffe1a5" d="M4 10h16l5 6h19v24H4z"/><path fill="#efc65a" stroke="none" d="M4 20h40v20H4z"/>',
 'terminal':'<rect x="3" y="6" width="42" height="36" rx="4" fill="#172b3a"/><path d="m11 16 9 8-9 8m16 1h10"/>',
 'document':'<path fill="#2583cf" d="M10 4h20l9 9v31H10z"/><path d="M29 5v10h10M16 23h16m-16 7h16m-16 7h10"/>',
 'browser':'<circle cx="24" cy="24" r="19" fill="#247cc7"/><path stroke="#72d6ff" d="M6 24h36M24 5c-14 12-14 26 0 38m0-38c14 12 14 26 0 38M10 13h28M10 35h28"/>',
 'application':'<rect x="4" y="5" width="40" height="38" rx="5" fill="#2b80ac"/><path d="M4 15h40M12 25h10v10H12m17-10h8m-8 8h8"/>',
 'search':'<circle cx="20" cy="20" r="13"/><path d="m30 30 13 13"/>',
 'logout':'<path d="M22 7H7v34h15m8-26 11 9-11 9M17 24h24"/>',
}


def symbol_icon(kind,color='#e7f3fc'):
    body=_SVGS.get(kind,_SVGS['application']).replace('currentColor',color)
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><g fill="none" stroke="{color}" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>'
    pix=QPixmap(96,96);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);QSvgRenderer(svg.encode()).render(p);p.end();return QIcon(pix)


_icon_files=None


def lookup_icon(name):
    """Qt/desktop icons first, packaged Papirus icons only as a fallback."""
    global _icon_files
    if not name:return QIcon()
    icon=QIcon(str(name)) if Path(str(name)).is_absolute() else QIcon.fromTheme(str(name))
    if not icon.isNull():return icon
    bundled=Path(__file__).parent/'assets/icons'/(str(name)+'.svg')
    if bundled.is_file():return QIcon(str(bundled))
    # Offscreen/minimal Qt and some frozen builds lack the GTK theme integration.
    # Index native files once, avoiding a directory walk for each task button.
    if _icon_files is None:
        _icon_files={}
        import os
        roots=[Path.home()/'.icons',Path(os.getenv('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'icons',Path('/usr/share/icons'),Path('/usr/local/share/icons')]
        for root in roots:
            if root.is_dir():
                for path in root.rglob('*'):
                    if path.suffix.lower() in ('.svg','.png','.xpm') and path.stem not in _icon_files:_icon_files[path.stem]=path
    path=_icon_files.get(str(name))
    return QIcon(str(path)) if path else QIcon()


def app_icon(name,fallback='application'):
    icon=lookup_icon(name)
    if icon.isNull():icon=lookup_icon({'folder':'system-file-manager','terminal':'utilities-terminal','browser':'firefox','settings':'preferences-system'}.get(fallback,'applications-other'))
    return icon if not icon.isNull() else symbol_icon(fallback)

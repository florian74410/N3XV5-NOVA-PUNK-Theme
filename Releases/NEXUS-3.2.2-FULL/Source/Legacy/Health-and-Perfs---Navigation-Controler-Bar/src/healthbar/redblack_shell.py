"""NOVA REDBLACK 0.8.2.2: independent graphical language on existing telemetry.

This is not hue swapping: component geometry, layering, material, lighting and
information layout are rendered here. No behavior/telemetry/shortcuts replaced.
No system theme or panel settings are touched by these painters.
"""
from __future__ import annotations

from functools import lru_cache
import math
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QHBoxLayout, QPushButton

THEME = "redblack-0822"
CRIMSON = "#FF2647"
HOT = "#FF7585"
DEEP = "#050406"
PANEL = "#0D060A"
METAL = "#686067"
WHITE = "#FFF2F4"
MUTED = "#C7A8AD"
ASSET_ROOT = Path(__file__).resolve().parent / "assets" / "redblack"

def active(theme=None):
    if theme is not None:
        return theme == THEME
    from .ui_kit import active_theme
    return active_theme() == THEME

def _color(value,alpha=None):
    color=QColor(value)
    if alpha is not None:
        color.setAlpha(max(0,min(255,int(alpha))))
    return color

def _path(rect,cut=16,notch=False):
    x,y,w,h=rect.x(),rect.y(),rect.width(),rect.height()
    cut=max(1,min(float(cut),h*.29,w*.18))
    path=QPainterPath(QPointF(x+cut,y))
    if notch and w>200:
        for px,py in ((x+w*.38,y),(x+w*.40,y+6),
                      (x+w*.58,y+6),(x+w*.61,y)):
            path.lineTo(px,py)
    path.lineTo(x+w-cut,y)
    for px,py in ((x+w,y+cut),(x+w,y+h-cut),(x+w-cut,y+h),
                  (x+cut,y+h),(x,y+h-cut),(x,y+cut)):
        path.lineTo(px,py)
    path.closeSubpath()
    return path

def _route(p,points,color=CRIMSON,width=1,alpha=180):
    if not points:return
    line=QPainterPath(QPointF(*points[0]))
    for x,y in points[1:]:
        line.lineTo(x,y)
    p.setPen(QPen(_color(color,alpha),width));p.setBrush(Qt.BrushStyle.NoBrush);p.drawPath(line)

def _glow(p,path,color=CRIMSON,bright=1.0):
    p.setBrush(Qt.BrushStyle.NoBrush)
    for width,alpha in ((9,12),(5,35),(2.5,75),(1.2,218)):
        p.setPen(QPen(_color(color,int(alpha*bright)),width))
        p.drawPath(path)

@lru_cache(maxsize=24)
def _svg(path):
    return QSvgRenderer(str(path))

@lru_cache(maxsize=12)
def _photo(path):
    return QPixmap(str(path))

def _layer(p,role,rect,opacity):
    """Hand-crafted SVGs are always present. Studio photos are optional."""
    file=ASSET_ROOT / {"pcb":"pcb-layers.svg",
        "metal":"chassis-layers.svg","mesh":"mesh-red.svg",
        "chevrons":"chevron-red.svg"}.get(role,"")
    if file.is_file():
        renderer=_svg(file)
        if renderer.isValid():
            p.save();p.setOpacity(opacity);renderer.render(p,rect);p.restore()
    if role=="pcb":
        from .config import data_dir
        studio=data_dir()/"Themes"/"blackred-studio"/"circuit-red-transparent.png"
        try:
            if studio.is_file() and studio.stat().st_size<16*1024*1024:
                pixmap=_photo(studio)
                if not pixmap.isNull():
                    p.save();p.setOpacity(opacity*.43)
                    p.drawPixmap(rect.toRect(),pixmap);p.restore()
        except OSError:
            pass

def paint_surface(p,rect,kind="holo",phase=0.0,selected=False):
    """Opaque clipped glass cavity; transparent outside 45-degree chrome."""
    if rect.width()<24 or rect.height()<22:return
    p.save();p.setRenderHint(p.RenderHint.Antialiasing,True)
    wide=rect.width();height=rect.height()
    compact=height<95
    cut=8 if compact else 20 if kind in ("settings","holo","notification") else 15
    shell=_path(rect,cut,notch=(kind in ("holo","settings","notification")))
    housing=QLinearGradient(0,rect.top(),0,rect.bottom())
    for stop, color in ((0,"#656168"),(.07,"#1E080F"),(.18,"#090609"),
                        (.79,"#0A0609"),(.94,"#310B16"),(1,"#565157")):
        housing.setColorAt(stop,QColor(color))
    p.fillPath(shell,housing)
    p.setClipPath(shell)
    inset=rect.adjusted(5,5,-5,-5)
    cavity=_path(inset,max(3,cut-4))
    p.fillPath(cavity,QColor(5,4,7,249 if kind=="holo" else 239))
    header_h=min(60,height*.22 if not compact else 18)
    stripe=QLinearGradient(0,rect.top(),0,rect.top()+header_h)
    stripe.setColorAt(0,_color("#871025",140))
    stripe.setColorAt(.42,_color("#260913",140))
    stripe.setColorAt(1,_color("#090609",0))
    p.fillRect(QRectF(rect.left()+6,rect.top()+4,wide-12,header_h),stripe)
    if kind in ("settings","dock","holo","notification","catalog"):
        _layer(p,"pcb",rect,.16 if kind=="settings" else .085)
    if kind in ("hud","task","button"):
        _layer(p,"metal",rect,.12)
    elif kind=="settings":
        _layer(p,"mesh",rect,.075)
    # Chamfered PCB routes and real electronic vias live in perimeter rails.
    x,y,r,b=rect.left(),rect.top(),rect.right(),rect.bottom()
    routes=(
        [(x+7,y+46),(x+19,y+46),(x+31,y+34),(x+51,y+34)],
        [(r-7,y+47),(r-18,y+47),(r-29,y+36),(r-53,y+36)],
        [(x+9,b-32),(x+19,b-32),(x+28,b-23),(x+64,b-23)],
        [(r-10,b-31),(r-23,b-31),(r-34,b-20),(r-57,b-20)]
    )
    if height>=110 and wide>=100:
        for i,route in enumerate(routes):
            _route(p,route,CRIMSON,.9,94+(i%2)*56)
            point=QPointF(*route[-1])
            p.setBrush(_color(HOT,180));p.setPen(QPen(_color(CRIMSON,210),.8))
            p.drawEllipse(point,2.3,2.3)
    # Animated current travels inside the metal rail, never through labels.
    progress=(phase%1.0)
    if wide>=90:
        trail_x=x+max(24,(wide-55)*progress)
        light=QLinearGradient(trail_x-20,y+7,trail_x+20,y+7)
        light.setColorAt(0,_color(CRIMSON,0))
        light.setColorAt(.50,_color("#FFF2F4",225 if selected else 170))
        light.setColorAt(1,_color(CRIMSON,0))
        p.fillRect(QRectF(trail_x-20,y+5,40,2.5),light)
        for j in range(min(7,max(0,int(wide//24)))):
            xx=r-14-j*9
            p.fillRect(QRectF(xx,b-11,4,2),_color(HOT,55+(j%3)*30))
    # A small machined stainless specular streak from the user's notification ref.
    shine=QLinearGradient(x+20,y,x+wide*.62,y+height*.16)
    shine.setColorAt(0,_color("#FFF6F8",45))
    shine.setColorAt(.48,_color("#FFFFFF",3))
    shine.setColorAt(.72,_color("#FBDDE4",24))
    shine.setColorAt(1,_color("#FFFFFF",0))
    p.fillRect(QRectF(x+cut,y+5,max(0,wide-2*cut),max(0,header_h*.32)),shine)
    p.setClipping(False)
    _glow(p,shell,HOT if selected else CRIMSON,1.0 if selected else .75)
    p.setPen(QPen(_color("#9E4651",155),.7))
    p.drawPath(cavity)
    # Brighter electrical junctions emphasize the real corner silhouettes.
    for ax,ay in ((x+cut+12,y+2),(r-cut-20,b-3)):
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(_color(CRIMSON,226))
        p.drawRoundedRect(QRectF(ax,ay,18,2.8),1,1)
    p.restore()

def _fitted(p,rect,content,pixel=15,color=WHITE,bold=False,align=None):
    font=p.font();font.setFamily("DejaVu Sans");font.setBold(bold)
    fsize=max(8,pixel)
    while fsize>8:
        font.setPixelSize(fsize)
        if QFontMetricsF(font).horizontalAdvance(str(content))<=max(4,rect.width()-4):
            break
        fsize-=1
    font.setPixelSize(fsize);p.setFont(font);p.setPen(QColor(color))
    p.drawText(rect,align or (Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter),str(content))

def _ratio(readings,key):
    val=readings.get(key)
    return max(0,min(1,val/100)) if isinstance(val,(float,int)) else None

def paint_hud(p,hud):
    """Completely new sensor cards, responsive to the EXISTING module hitboxes."""
    from .network_detail import format_rate
    readings=hud.readings or {}
    retracted=bool(getattr(hud.window(),"retracted",False))
    htime=(time.monotonic()*.12)%1
    slots=hud.active_slots
    meta={
      "cpu":("CPU",hud.value("cpu_temperature_c",52)+" °C",hud.value("cpu_percent",18)+"% · "+hud.value("cpu_frequency_ghz",2.4,1)+" GHz",_ratio(readings,"cpu_percent")),
      "gpu":("GPU",hud.value("gpu_temperature_c",48)+" °C",hud.value("gpu_percent",32)+"% · "+hud.gpu_ghz()+" GHz",_ratio(readings,"gpu_percent")),
      "ram":("RAM",hud.value("ram_percent",44)+"%",hud.used_free("ram","—"),_ratio(readings,"ram_percent")),
      "storage":("STOCKAGE",hud.value("disk_percent",62)+"%",hud.used_free("disk","—"),_ratio(readings,"disk_percent")),
      "fans":("VENTILATEURS",str(hud.fans()[0].get("rpm","—"))+" RPM" if hud.fans() else "— RPM","RPM réels",None),
      "network":("RÉSEAU","↓ "+format_rate(readings.get("net_down_mbs")),"↑ "+format_rate(readings.get("net_up_mbs")),None),
      "power":("ÉNERGIE",hud.power_value(),hud.power_detail(),None)
    }
    for i,kind in enumerate(slots):
        bounds=hud.module_rect(kind)
        rect=QRectF(bounds).adjusted(3,3,-3,-3)
        if rect.width()<23 or rect.height()<16:continue
        selected=(hud._hover_slot==kind)
        title,value,detail,ratio=meta[kind]
        paint_surface(p,rect,"hud",htime+i*.17,selected)
        p.save()
        inner=rect.adjusted(12,6,-12,-6)
        short=inner.height()<60
        if retracted or inner.height()<31:
            _fitted(p,inner,str(title)+"  "+str(value),11,WHITE,True)
            p.restore()
            continue
        # Metallic header + optical tick marks, not the original neon panel.
        _fitted(p,QRectF(inner.x()+2,inner.y()+3,inner.width()-36,20),
                title,11,CRIMSON,True)
        top=inner.y()+25
        if hud.vertical and inner.width()<115:
            _fitted(p,QRectF(inner.x(),top,inner.width(),26),value,15,WHITE,True)
        else:
            _fitted(p,QRectF(inner.x()+2,top,inner.width()-4,25 if short else 33),
                    value,16 if short else 23,WHITE,True)
        if not short:
            _fitted(p,QRectF(inner.x()+2,min(inner.bottom()-26,top+36),inner.width()-4,18),
                    detail,10,MUTED)
        if ratio is not None:
            by=inner.bottom()-5
            gx=inner.x()+4;gw=max(10,inner.width()-8)
            p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor("#2D121A"))
            p.drawRoundedRect(QRectF(gx,by,gw,3),1,1)
            p.setBrush(QColor(CRIMSON))
            p.drawRoundedRect(QRectF(gx,by,gw*ratio,3),1,1)
        # Decorative stripes are intentionally NOT presented as fabricated data.
        if inner.width()>155 and inner.height()>80:
            for ix in range(3):
                x=inner.right()-35+ix*7
                p.fillRect(QRectF(x,inner.y()+5,4,2),_color(HOT,180+20*ix))
        p.restore()

def holo_stylesheet():
    return """
    QWidget#cpuHolo {background:transparent;border:0;}
    QLabel {color:#FCEAEC;background:transparent;border:0;font-family:Sans;}
    QLabel#holoTitle {color:#FF5A70;font-size:16px;font-weight:900;letter-spacing:1px;}
    QLabel#holoSubtitle {color:#C4A2AA;font-size:11px;}
    QLabel#holoHeading {color:#E8C4CA;font-size:12px;font-weight:700;padding:4px;}
    QLabel#holoValue {color:#FFF6F7;font-size:12px;font-weight:800;padding:4px;}
    QLabel#holoGroup {color:#FF6374;background:#390B19;border-left:3px solid #FF2945;
      padding:7px 8px;font-size:12px;font-weight:900;}
    QLabel#holoFoot {color:#B79BA1;font-size:10px;}
    QPushButton {background:#210810;color:#FCE5E9;border:1px solid #D1213C;
      padding:5px 8px;font-weight:700;}
    QPushButton:checked {background:#5F0C22;color:white;}
    QPushButton:hover {background:#78132C;border:1px solid #FF7485;}
    QPushButton#novaClose {background:#610B1D;color:#FFFFFF;border:1px solid #FF6374;}
    QScrollArea#novaDataScroll {background:#080508;border:1px solid #581422;}
    QScrollArea#novaDataScroll QWidget {background:transparent;border:0;}
    QScrollArea#novaDataScroll QScrollBar:vertical {background:#1A080E;width:10px;}
    QScrollArea#novaDataScroll QScrollBar::handle:vertical {background:#CB2441;
      border:1px solid #FF6374;min-height:30px;}
    """

def control_stylesheet(scope="window"):
    return """
    QWidget {color:#F6E7EA;font-family:DejaVu Sans;background:transparent;}
    QLabel {color:#E7D9DC;background:transparent;}
    QLabel#title, QLabel#launcherTitle {color:#FF5E73;font-size:22px;font-weight:900;}
    QLabel#sectionHeader {color:#FF7585;font-size:15px;font-weight:800;padding:11px 5px 7px;}
    QDialog {background:#090609;color:#FFE8EC;}
    QDialog#novaSettings {background:transparent;color:#FFE8EC;}
    QWidget#generalContent, QWidget#settingsPages {
      background:rgba(9,5,9,236);border:1px solid #8C1C31;}
    QListWidget#settingsNavigation {
      background:rgba(11,5,9,246);color:#E7CCD2;border:1px solid #9D1C35;
      padding:11px;outline:none;}
    QListWidget#settingsNavigation::item {height:37px;padding:8px 10px;border-bottom:1px solid #37111B;}
    QListWidget#settingsNavigation::item:selected {color:#FFFFFF;background:#6A1028;border-left:3px solid #FF4561;}
    QListWidget#settingsNavigation::item:hover {background:#35101B;}
    QListWidget,QTreeWidget,QTableWidget {background:#080609;color:#F1E5E7;
      border:1px solid #7B1A2D;outline:none;selection-background-color:#79162C;}
    QListWidget::item:selected {background:#6F1128;color:white;border-left:2px solid #FF4561;}
    QListWidget::item:hover {background:#35101A;}
    QLineEdit,QComboBox,QSpinBox,QKeySequenceEdit {
      background:#1A0A11;color:#FFF1F3;border:1px solid #AF1C36;
      padding:7px 10px;min-height:22px;}
    QComboBox QAbstractItemView {background:#0E080D;color:#FFF1F3;
      selection-background-color:#7E132B;border:1px solid #C12341;}
    QPushButton,QToolButton {
      background:#1B0B11;color:#FCE8EB;border:1px solid #B91B39;
      padding:7px 12px;min-height:18px;font-weight:700;}
    QPushButton:hover,QToolButton:hover {background:#661124;color:#FFFFFF;border-color:#FF526B;}
    QPushButton:pressed,QToolButton:pressed {background:#96192F;}
    QPushButton:disabled {background:#171014;color:#80636A;border-color:#51232B;}
    QPushButton#nav {background:transparent;border:0;}
    QTabWidget::pane {background:#0B070B;border:1px solid #7D1730;padding:7px;}
    QTabBar::tab {background:#190911;color:#BE9EA5;border:1px solid #6B1A2D;padding:10px 14px;}
    QTabBar::tab:selected {background:#611029;color:#FFF4F4;border-bottom:2px solid #FF2945;}
    QCheckBox {color:#F2DEE2;spacing:9px;}
    QCheckBox::indicator {background:#10070A;border:1px solid #BD2742;width:18px;height:18px;}
    QCheckBox::indicator:checked {background:#F12543;border:1px solid #FF8F9D;}
    QScrollArea,QScrollArea QWidget,QScrollArea::viewport {background:transparent;border:0;}
    QScrollBar:vertical {width:9px;background:#10070C;}
    QScrollBar::handle:vertical {background:#BA1E39;min-height:28px;}
    QScrollBar:horizontal {height:8px;background:#10070C;}
    QScrollBar::handle:horizontal {background:#BA1E39;}
    QSlider::groove:horizontal {height:5px;background:#3C111D;}
    QSlider::handle:horizontal {background:#FF3454;width:14px;margin:-6px 0;}
    QMenu {background:#0B070B;color:#FDE8EA;border:1px solid #ED2748;padding:6px;}
    QMenu::item {padding:9px 18px;margin:2px;}
    QMenu::item:selected {background:#71152D;color:white;}
    QMenu::separator {height:1px;background:#682034;margin:5px;}
    QToolTip {background:#150A0F;color:#FFFFFF;border:1px solid #FF4560;}
    """

def paint_button(p,button):
    """Sharp-edge mechanical actuator drawn underneath the unchanged icon."""
    rect=QRectF(button.rect()).adjusted(1.5,1.5,-1.5,-1.5)
    paint_surface(p,rect,"button",(time.monotonic()*.16)%1,button.underMouse())
    p.save()
    p.setPen(QPen(QColor("#F35670"),1))
    # narrow metallic detent at lower right
    p.drawLine(QPointF(rect.right()-24,rect.bottom()-7),QPointF(rect.right()-9,rect.bottom()-7))
    p.restore()

class NovaRedToast(QDialog):
    """Non-modal native Qt popup; honors normal OS notifications elsewhere."""
    def __init__(self,title,message,parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(440,132)
        layout=QVBoxLayout(self);layout.setContentsMargins(27,25,27,20)
        header=QHBoxLayout()
        heading=QLabel("◈ "+str(title));heading.setStyleSheet(
            "color:#FF6577;font-size:16px;font-weight:900;background:transparent;")
        header.addWidget(heading,1)
        close=QPushButton("✕");close.setFixedSize(30,27)
        close.setStyleSheet("background:#430919;color:white;border:1px solid #F73652;")
        close.clicked.connect(self.close);header.addWidget(close)
        layout.addLayout(header)
        body=QLabel(str(message));body.setWordWrap(True)
        body.setStyleSheet("color:#FFFFFF;background:transparent;font-size:12px;")
        layout.addWidget(body,1)
        QTimer.singleShot(5500,self.close)
    def paintEvent(self,event):
        from PySide6.QtGui import QPainter
        p=QPainter(self)
        p.setCompositionMode(p.CompositionMode.CompositionMode_Clear)
        p.fillRect(self.rect(),Qt.GlobalColor.transparent)
        p.setCompositionMode(p.CompositionMode.CompositionMode_SourceOver)
        paint_surface(p,QRectF(self.rect()).adjusted(4,4,-4,-4),"notification",0)
        p.end()

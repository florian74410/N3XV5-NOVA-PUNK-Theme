"""Shared Holo palette, PCB routing and NovaBar chip identity."""
import re
from PySide6.QtGui import QColor as QtColor, QPainterPath, QPen
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter

THEMES = {"redblack-0822": "NOVA REDBLACK 0.8.2.2", "blue-neon": "Blue Neon", "green-matrix": "Green Matrix", "red-blood": "Red Blood"}
_active = "blue-neon"
_custom = {}

def active_theme():
    return _active

def set_theme(theme):
    global _active, _custom
    _active = theme if theme in ("cyber-futuriste", *THEMES) else "blue-neon"
    from .theme_overrides import load
    _custom = load().get(_active, {})
    # The cockpit, docks and XFCE skin already share one native palette table.
    from .xfce_panel_skin import PALETTES
    if _custom:
        original=PALETTES.get(_active, PALETTES["blue-neon"])
        primary=_custom.get("primary", original[0])
        secondary=_custom.get("secondary", original[1])
        rgb=QtColor(primary)
        PALETTES[_active]=(primary,secondary,
            f"{rgb.red()}, {rgb.green()}, {rgb.blue()}")

def QColor(*args):
    """Retint decorative electric blue but never semantic red warnings."""
    color = QtColor(*args)
    if len(args)==1 and isinstance(args[0],str):
        name=color.name().lower()
        if _active=="redblack-0822" and name in ("#061224","#061020","#040d1b"):
            chosen=QtColor("#08050A");chosen.setAlpha(color.alpha());return chosen
        if name in ("#061224","#061020","#040d1b") and _custom.get("background"):
            chosen=QtColor(_custom["background"])
            chosen.setAlpha(color.alpha())
            return chosen
    h,saturation,value,alpha=color.getHsvF()
    if .46 <= h <= .70 and saturation > .12:
        if _active=="redblack-0822":
            color.setHsvF(QtColor("#FF2647").hueF(),saturation,value,alpha)
            return color
        if _custom.get("primary"):
            chosen=QtColor(_custom["primary"])
            chosen.setAlphaF(alpha)
            return chosen
        if _active not in ("blue-neon","cyber-futuriste"):
            color.setHsvF(.37 if _active=="green-matrix" else .98,saturation,value,alpha)
    return color

def holo_background():
    """Uniform theme-tinted glass: 85% opaque, 15% desktop visible."""
    color = QColor('#061224')
    color.setAlpha(217)
    return color


def stylesheet(text):
    # Theme controls frames and surfaces; information keeps its own readable palette.
    def retint(match):
        prefix=text[max(0,match.start()-40):match.start()]
        if re.search(r"(?<![-\w])color\s*:\s*$",prefix):
            return match[0]
        return QColor(match[0]).name()
    result=re.sub(r"#[0-9a-fA-F]{6}\b",retint,text)
    # Titles are the only text role inheriting the decorative accent.
    return re.sub(r"(QLabel#holoTitle\s*\{[^}]*?\bcolor\s*:\s*)(#[0-9a-fA-F]{6})",
                  lambda m:m[1]+QColor(m[2]).name(),result)


def pcb(p, bounds):
    """Routes reach both endpoints of the full window, including the action area."""
    w, h = bounds.width(), bounds.height()
    p.save()
    for i in range(6):
        y = 2 + i * 3
        path = QPainterPath(QPointF(0, y))
        x = 0
        while x < w:
            path.lineTo(min(x+38,w),y)
            path.lineTo(min(x+48,w),y+6)
            path.lineTo(min(x+76,w),y+6)
            path.lineTo(min(x+86,w),y)
            x += 130
        path.lineTo(w,y)
        for width, alpha in ((5,22),(2,90),(.7,210)):
            color=QColor("#25cfff");color.setAlpha(alpha)
            p.setPen(QPen(color,width));p.drawPath(path)
        p.translate(0,h-2*y)
        p.drawPath(path)
        p.translate(0,-(h-2*y))
    p.restore()

def chip(p, rect):
    p.save();p.translate(rect.center());scale=min(rect.width(),rect.height())/64;p.scale(scale,scale)
    p.setPen(QPen(QColor("#34dfff"),1.4))
    for side in range(4):
        for x in (-12,-4,4,12):
            p.drawLine(QPointF(x,-18),QPointF(x,-27))
        p.rotate(90)
    p.setBrush(QColor("#061224"));p.drawRoundedRect(QRectF(-18,-18,36,36),4,4)
    p.drawRect(QRectF(-11,-11,22,22));p.drawText(QRectF(-11,-11,22,22),0x84,"N")
    p.restore()

class ChipLogo(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setMinimumHeight(0);self.setToolTip("NovaBar · La Puce")
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);chip(p,QRectF(self.rect()));p.end()

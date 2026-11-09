"""Painted lightweight Cyber-Neon settings shell; no texture assets, web API or timer."""
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QLinearGradient
from PySide6.QtWidgets import QDialog, QWidget
from .xfce_panel_skin import PALETTES
from .theme_overrides import load as load_theme_overrides
from .redblack_shell import active as redblack_active, paint_surface as paint_redblack, control_stylesheet


def _palette(theme):
    preset=PALETTES.get(theme, PALETTES["blue-neon"])
    custom=load_theme_overrides().get(theme,{})
    return (custom.get("primary",preset[0]),custom.get("secondary",preset[1]),
            custom.get("background","#041426"))


def settings_stylesheet(theme):
    if redblack_active(theme):return control_stylesheet()
    primary,secondary,_=_palette(theme)
    return """
    QDialog#novaSettings { background: transparent; color: #EAF6FF; }
    QLabel { color:#D7EDFF; background:transparent; font-size:13px; }
    QLabel#title { color:%s; font-size:27px; font-weight:700; }
    QLabel#sectionHeader { color:%s; font-size:16px; font-weight:700; padding:12px 5px 7px; }
    QWidget#generalContent, QWidget#settingsPages {
        background:rgba(2,14,32,175);border:1px solid %s;border-radius:13px;
    }
    QTabWidget, QTabWidget::pane, QTabWidget QWidget, QScrollArea, QScrollArea QWidget,
    QScrollArea::viewport { background: transparent; border: none; }
    QListWidget#settingsNavigation {
        color:#DDF2FF;background:rgba(2,16,37,215);
        border:1px solid %s;border-radius:12px;padding:12px;outline:0px;
    }
    QListWidget#settingsNavigation::item { height:33px; padding:7px 9px; border-radius:6px; }
    QListWidget#settingsNavigation::item:selected {
        background:rgba(4,95,151,190);border:1px solid %s;color:#FFFFFF;
    }
    QListWidget#settingsNavigation::item:hover {
        background:rgba(0,112,170,95);
    }
    QLineEdit, QComboBox, QSpinBox {
        color:#EDF8FF;background:rgba(5,32,59,232);
        border:1px solid %s;border-radius:7px;padding:8px 10px;min-height:23px;
    }
    QComboBox QAbstractItemView {
        background:#061B33;color:#E7F6FF;border:1px solid %s;
        selection-background-color:#124B7B;selection-color:#FFFFFF;
    }
    QPushButton {
        color:#E6F7FF;background:rgba(5,40,74,210);
        border:1px solid %s;border-radius:8px;padding:9px 13px;min-height:20px;
    }
    QPushButton:hover {
        color:#FFFFFF;border:1px solid %s;background:rgba(9,85,126,230);
    }
    QPushButton:pressed { background:rgba(9,112,155,230); }
    QPushButton:disabled { color:#60768B;background:rgba(3,21,40,175);border-color:#21425B; }
    QCheckBox { color:#D9F3FF;spacing:10px;background:transparent; }
    QCheckBox::indicator {width:17px;height:17px;border:1px solid %s;border-radius:5px;
        background:rgba(1,23,43,240);}
    QCheckBox::indicator:checked {background:%s;border-color:%s;}
    QSlider::groove:horizontal {height:5px;background:#14446A;border-radius:2px;}
    QSlider::handle:horizontal {width:15px;margin:-6px 0;background:%s;border-radius:7px;}
    QScrollBar:vertical {width:9px;background:rgba(2,18,38,180);border:0;}
    QScrollBar::handle:vertical {background:#14648C;border-radius:4px;min-height:30px;}
    QScrollBar:horizontal {height:8px;background:rgba(2,18,38,160);}
    QScrollBar::handle:horizontal {background:#14648C;border-radius:4px;}
    QDialogButtonBox {background:transparent;}
    """ % (primary,primary,secondary,secondary,primary,secondary,secondary,
            secondary,secondary,primary,secondary,primary,primary)


class PCBSettingsDialog(QDialog):
    """One translucent glass paint pass; trace geometry recalculated only on repaint."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName("novaSettings")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground,True)
        self._pcb_theme="blue-neon"
        self._redblack_phase=0.0
        self._redblack_timer=QTimer(self)
        self._redblack_timer.setInterval(85)
        self._redblack_timer.timeout.connect(self._animate_redblack)

    def use_pcb_theme(self,theme):
        self._pcb_theme=theme
        self.setStyleSheet(settings_stylesheet(theme))
        if redblack_active(theme) and self.isVisible():self._redblack_timer.start()
        else:self._redblack_timer.stop()
        self.update()

    def _animate_redblack(self):
        if self.isVisible() and redblack_active(self._pcb_theme):
            self._redblack_phase=(self._redblack_phase+.007)%1
            self.update()
        else:self._redblack_timer.stop()

    def showEvent(self,event):
        super().showEvent(event)
        if redblack_active(self._pcb_theme):self._redblack_timer.start()

    def hideEvent(self,event):
        self._redblack_timer.stop()
        super().hideEvent(event)

    def paintEvent(self,event):
        if redblack_active(self._pcb_theme):
            painter=QPainter(self)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.rect(),Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            paint_redblack(painter,QRectF(self.rect()).adjusted(7,7,-7,-7),
                           "settings",self._redblack_phase)
            painter.end()
            return
        painter=QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(),Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        rect=QRectF(self.rect()).adjusted(7,7,-7,-7)
        if rect.width()<110 or rect.height()<110:return
        path=QPainterPath()
        cut=22
        path.moveTo(rect.left()+cut,rect.top())
        for x,y in ((rect.right()-cut,rect.top()),(rect.right(),rect.top()+cut),
                    (rect.right(),rect.bottom()-cut),(rect.right()-cut,rect.bottom()),
                    (rect.left()+cut,rect.bottom()),(rect.left(),rect.bottom()-cut),
                    (rect.left(),rect.top()+cut)):
            path.lineTo(x,y)
        path.closeSubpath()
        primary,secondary,background=_palette(self._pcb_theme)
        glass=QColor(background);glass.setAlpha(236)
        painter.fillPath(path,glass)
        # Glass reflection on the beveled header, inspired by NOVA Notification.
        shine=QLinearGradient(rect.left(),rect.top(),rect.right(),rect.top()+rect.height()*.4)
        shine.setColorAt(0,QColor(210,242,255,46))
        shine.setColorAt(.38,QColor(210,242,255,4))
        shine.setColorAt(.7,QColor(210,242,255,28))
        shine.setColorAt(1,QColor(210,242,255,0))
        painter.fillRect(QRectF(rect.left()+13,rect.top()+5,rect.width()-26,rect.height()*.12),shine)
        painter.setClipPath(path)
        # Original, asymmetric PCB: irregular routes from all four corners,
        # short branches, vias and polished light wells. No tiling or looped
        # identical rows. Fully static => zero idle animation CPU.
        w=rect.width();h=rect.height()
        routes=(
            ((0,.12),(.09,.12),(.15,.19),(.29,.19)),
            ((0,.20),(.055,.20),(.13,.28),(.31,.28)),
            ((0,.32),(.038,.32),(.09,.38),(.19,.38)),
            ((0,.83),(.075,.83),(.13,.76),(.25,.76)),
            ((0,.92),(.13,.92),(.22,.84),(.34,.84)),
            ((.11,0),(.11,.07),(.18,.13),(.33,.13)),
            ((.24,0),(.24,.04),(.29,.08),(.36,.08)),
            ((.62,0),(.62,.045),(.67,.09),(.76,.09)),
            ((.81,0),(.81,.065),(.88,.13),(.99,.13)),
            ((1,.10),(.94,.10),(.89,.16),(.78,.16)),
            ((1,.23),(.96,.23),(.88,.30),(.75,.30)),
            ((1,.79),(.93,.79),(.88,.73),(.75,.73)),
            ((1,.88),(.96,.88),(.88,.95),(.79,.95)),
            ((.61,1),(.61,.96),(.70,.89),(.80,.89)),
            ((.38,1),(.38,.95),(.32,.89),(.25,.89)),
            ((.17,1),(.17,.96),(.23,.90),(.29,.90)),
        )
        for idx,route in enumerate(routes):
            trace=QPainterPath()
            for step,(rx,ry) in enumerate(route):
                px=rect.left()+rx*w
                py=rect.top()+ry*h
                if step==0:trace.moveTo(px,py)
                else:trace.lineTo(px,py)
            color=QColor(primary if idx%3 else secondary)
            color.setAlpha(92 if idx%4 else 165)
            painter.setPen(QPen(color,1.1 if idx%5 else 1.9))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(trace)
            point=trace.currentPosition()
            painter.setPen(QPen(color,1))
            painter.setBrush(QColor(2,25,43,220))
            painter.drawEllipse(point,2.7 if idx%3 else 4.0,2.7 if idx%3 else 4.0)
            if idx%4==1:
                sub=route[-2]
                mx=rect.left()+sub[0]*w
                my=rect.top()+sub[1]*h
                branch=QPainterPath(QPointF(mx,my))
                branch.lineTo(mx+(-12 if idx%2 else 12),my+15)
                painter.drawPath(branch)
        # Three small angular light wells, not a tiled glow pattern.
        painter.setPen(Qt.PenStyle.NoPen)
        for x,y,rx in ((.18,.04,19),(.52,.985,27),(.93,.04,14)):
            center=QPointF(rect.left()+x*w,rect.top()+y*h)
            light=QColor(primary);light.setAlpha(170)
            painter.setBrush(light)
            painter.drawRoundedRect(QRectF(center.x()-rx,center.y()-1,2*rx,2),1,1)
        painter.setClipping(False)
        for width,opacity in ((9,22),(4,64),(1.4,230)):
            color=QColor(primary);color.setAlpha(opacity)
            painter.setPen(QPen(color,width))
            painter.drawPath(path)
        painter.end()


class BarPreview(QWidget):
    """Static mini-preview. No timer, no sensors and no GPU-heavy effects."""
    def __init__(self,theme="blue-neon",parent=None):
        super().__init__(parent)
        self._theme=theme
        self.setMinimumHeight(138)
        self.setMinimumWidth(310)

    def change_theme(self,theme):
        self._theme=theme
        self.update()

    def paintEvent(self,event):
        if redblack_active(self._theme):
            p=QPainter(self)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(self.rect(),Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            paint_redblack(p,QRectF(self.rect()).adjusted(5,5,-5,-5),"hud",0)
            p.setPen(QColor("#FF6374"))
            p.drawText(self.rect().adjusted(16,8,-16,-8),
                       Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignHCenter,
                       "NOVA  /  REDBLACK 0.8.2.2")
            p.end()
            return
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        primary,secondary,_=_palette(self._theme)
        rect=QRectF(self.rect()).adjusted(4,4,-4,-4)
        p.setPen(QPen(QColor(primary),1.2))
        p.setBrush(QColor(2,17,36,210))
        p.drawRoundedRect(rect,11,11)
        p.setPen(QPen(QColor(215,239,255),1))
        font=p.font();font.setPixelSize(12);font.setBold(True);p.setFont(font)
        p.drawText(QRectF(18,10,rect.width()-25,27),"APERÇU  /  TOP HUD + NAVIGATION")
        for i,y in enumerate((46,91)):
            box=QRectF(18,y,rect.width()-37,33)
            p.setBrush(QColor(4,34,60,220))
            p.setPen(QPen(QColor(secondary),1))
            p.drawRoundedRect(box,8,8)
            p.setPen(QPen(QColor(primary),1.1))
            if i==0:
                p.drawText(box.adjusted(12,0,-8,0),"◈ CPU   12 %     RAM  23 %      NORMAL MODE")
            else:
                p.drawText(box.adjusted(12,0,-8,0),"⌂ Accueil     ▦ Apps     ⚙ Réglages     +2")
        p.end()

#!/usr/bin/env python3
"""N3XV5 TOP native Qt skin for NovaBar 0.8.2.2.

Only presentation and per-preview preferences are changed. Existing Bar,
SharedTelemetry, Holo classes and EWMH workarea code remain authoritative.
No web views, HTTP endpoints, synthetic metrics or changes to installed NovaBar.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
ASSET = ROOT / 'App/Modules/Top/HUD_Plugins_ViewBar/Assets/reference_shell.png'
DEFAULTS = {'height': 100, 'always_visible': False, 'hide_delay_s': 2,
            'edge_hover_ms': 2000, 'opacity': 82, 'contrast': 90, 'glow': 80, 'motion': True,
            'holo_enabled': True, 'hidden_modules': [], 'bottom_enabled': True, 'bottom_height': 62, 'bottom_opacity': 46,
            'telemetry_refresh_s': 2, 'visual_fps': 15, 'net_speedtest_hourly': False}
SLOTS = ['cpu', 'gpu', 'ram', 'storage', 'fans', 'network', 'power']
LABELS = {'cpu': 'CPU', 'gpu': 'GPU', 'ram': 'RAM', 'storage': 'SSD',
          'fans': 'FANS', 'network': 'NET', 'power': 'PWR'}


def _legacy_path(argument):
    if argument:
        return Path(argument).expanduser().resolve()
    return ROOT / 'Legacy/Health-and-Perfs---Navigation-Controler-Bar'


def _number(readings, key):
    n=readings.get(key)
    return float(n) if isinstance(n,(float,int)) and not isinstance(n,bool) and math.isfinite(n) else None


def _fmt(v, precision=0, unit=''):
    return f'{v:.{precision}f}{unit}' if v is not None else '—'


def _load_prefs(path):
    data=DEFAULTS.copy()
    try:
        saved=json.loads(path.read_text('utf-8'))
        if isinstance(saved,dict):
            data.update({k:v for k,v in saved.items() if k in DEFAULTS})
    except (OSError,ValueError,TypeError):
        pass
    for k,lo,hi in [('height',60,150),('hide_delay_s',1,30),('edge_hover_ms',500,4000),
                    ('opacity',20,100),('contrast',40,140),('glow',0,100),('bottom_height',62,94),('bottom_opacity',15,85),
                    ('telemetry_refresh_s',1,15),('visual_fps',5,30)]:
        v=data.get(k)
        data[k]=max(lo,min(hi,int(v))) if type(v) in (int,float) else DEFAULTS[k]
    for k in ('always_visible','motion','holo_enabled','bottom_enabled','net_speedtest_hourly'):
        data[k]=data[k] if type(data[k]) is bool else DEFAULTS[k]
    x=data.get('hidden_modules',[])
    data['hidden_modules']=[s for s in SLOTS if s in x] if isinstance(x,list) else []
    return data


def _save_prefs(path, prefs):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(prefs,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    temp.replace(path)


def _install_qt_painter(prefs):
    from PySide6.QtCore import Qt,QRectF,QPointF,QRect
    from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen,QBrush,QLinearGradient,QRadialGradient,QFont,QImage
    from healthbar.hud import HudCanvas
    from n3xvs_metrics import power_labels, storage_caps, SPEED_TEST

    BLUE=QColor('#17dfff'); ROYAL=QColor('#1378ff'); RED=QColor('#c31838')
    PALE=QColor('#ddf9ff'); MUTED=QColor('#79abc7')
    shell=QImage(str(ASSET))
    def pen(p,color,width=1): p.setPen(QPen(color,width))
    def txt(p,s,x,y,sz=11,color=PALE,bold=False,align=None,width=0):
        font=QFont('DejaVu Sans');font.setPixelSize(max(7,int(sz)));font.setBold(bold)
        p.setFont(font);pen(p,color)
        if align is not None:
            p.drawText(QRectF(x,y,width,sz+6),align,str(s))
        else:p.drawText(QPointF(x,y),str(s))
    def polygon(r,cut=9):
        x,y,w,h=r.x(),r.y(),r.width(),r.height();c=min(cut,w*.12,h*.25)
        path=QPainterPath(QPointF(x+c,y))
        for a,b in ((x+w-c,y),(x+w,y+c),(x+w,y+h-c),(x+w-c,y+h),
                    (x+c,y+h),(x,y+h-c),(x,y+c)):path.lineTo(a,b)
        path.closeSubpath();return path
    def segments(p,x,y,w,h,pct):
        n=max(3,min(17,int(w//9)));gap=2;sw=max(1,(w-gap*(n-1))/n)
        ratio=max(0,min(1,pct/100)) if pct is not None else 0
        for i in range(n):
            fill=QColor('#27dfff') if i < round(n*ratio) else QColor(22,68,106,140)
            if i>=int(n*.85) and pct is not None and pct>=90 and i<round(n*ratio):fill=RED
            p.fillRect(QRectF(x+i*(sw+gap),y,sw,h),fill)
    def gauge(p,cx,cy,r,value,maxval,title,phase):
        """20 individual arc bars; 10 blue, 5 green, 3 orange, 2 red."""
        p.setBrush(Qt.BrushStyle.NoBrush)
        fraction = max(0,min(1,value/maxval)) if value is not None and maxval>0 else 0
        lit = min(20,max(0,math.ceil(20*fraction)))
        spectrum=['#24bfff']*10+['#31dc78']*5+['#ff9c37']*3+['#f42b4b']*2
        # Use 270 degrees rather than a needle: each 10-degree band is separate.
        for i,chromatic in enumerate(spectrum):
            rect=QRectF(cx-r,cy-r,2*r,2*r)
            start=(225-i*13.5)*16
            color=QColor(chromatic) if i<lit else QColor(24,55,76,165)
            pen(p,color,max(2.3,r*.16))
            p.drawArc(rect,round(start),-round(9.8*16))
        if value is not None:
            txt(p,_fmt(value,0),cx-r*.52,cy+r*.18,max(9,r*.44),PALE,True)
        else:
            txt(p,'—',cx-r*.19,cy+r*.18,max(10,r*.52),MUTED,True)
    def geometry(self):
        """Keep old Holo anchor/click math using native rectangles."""
        slots=self.active_slots
        # top bar: 12% left identity, 18% right controls
        available=max(0,self.width()*.72)
        x=self.width()*.116
        weights={'cpu':1.12,'gpu':.82,'ram':1.03,'storage':1.05,
                 'fans':1.0,'network':1.02,'power':.92}
        scale=available/max(.1,sum(weights[s] for s in slots))
        out={}
        for s in slots:
            w=weights[s]*scale
            out[s]=QRect(round(x),0,round(w),self.height())
            x+=w
        return out
    def module_rect(self,kind): return geometry(self).get(kind,QRect())
    def module_icon_rect(self,kind):
        if getattr(self.window(),'retracted',False):return QRect()
        r=module_rect(self,kind)
        a=max(12,min(19,round(r.height()*.16)))
        return QRect(r.right()-a-6,r.top()+12,a,a)
    def module_at(self,pos):
        x=pos.x()
        slots=self.active_slots
        if not slots:return 0
        for i,s in enumerate(slots):
            if x < module_rect(self,s).right():return i
        return len(slots)-1
    def get_fields(kind,data):
        n=lambda key:_number(data,key)
        if kind=='cpu':
            temp=n('cpu_temperature_c');load=n('cpu_percent');freq=n('cpu_frequency_ghz')
            return _fmt(temp,0,' °C') if temp is not None else _fmt(load,0,'%'), _fmt(freq,2,' GHz'),load,freq,4.5
        if kind=='gpu':
            load=n('gpu_percent');temp=n('gpu_temperature_c')
            clock=n('gpu_clock_mhz')
            return _fmt(load,0,'%'),(_fmt(temp,0,' °C') if temp is not None else _fmt(clock/1000,2,' GHz') if clock else 'SONDE —'),load,None,1
        if kind=='ram':
            load=n('ram_percent');u=n('ram_used_gb');t=n('ram_total_gb')
            return _fmt(load,0,'%'),f'{_fmt(u,1)} / {_fmt(t,1)} GB',load,None,1
        if kind=='storage':
            load=n('disk_percent');u=n('disk_used_gb');t=n('disk_total_gb')
            return _fmt(load,0,'%'),f'{_fmt(u,1)} / {_fmt(t,1)} GB',load,None,1
        if kind=='fans':
            f=next((x for x in data.get('fans',[]) if isinstance(x,dict) and isinstance(x.get('rpm'),(float,int))),None)
            rpm=_number(f,'rpm') if f else None
            lim=_number(f,'max_rpm') if f else None
            return _fmt(rpm,0,' RPM'),'VENTILATION' if rpm is not None else 'SONDE —',None,rpm,lim or 5000
        if kind=='network':
            d=n('net_down_mbs');u=n('net_up_mbs')
            return _fmt(d,2,' MB/s'),'↑ '+_fmt(u,2,' MB/s'),None,None,1
        if kind=='power':
            main,sub=power_labels(data)
            return main,sub,None,None,1
        return '—','',None,None,1
    def paint(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w=self.width();h=self.height();compact=bool(getattr(self.window(),'retracted',False))
        p.fillRect(self.rect(),QColor(3,10,23,0))
        p.save()
        if not shell.isNull():
            p.setOpacity(max(.20,min(1,prefs['opacity']/100)))
            p.drawImage(QRectF(0,0,w,h),shell)
            p.setOpacity(1)
        else:
            p.fillRect(self.rect(),QColor(4,17,38,230))
        p.restore()
        phase=(time.monotonic()*.35)%1 if prefs['motion'] else .3
        if compact:
            # Compact = actual 26–32px native bar, no webpage scrolling.
            p.fillRect(QRectF(0,1,w,h-2),QColor(3,12,29,235))
            pen(p,BLUE,1.4);p.drawLine(QPointF(0,h-2),QPointF(w,h-2))
            txt(p,'N3XV5',10,min(21,h-6),11,BLUE,True)
            slots=self.active_slots
            if slots:
                avail=max(10,w-245);cell=avail/len(slots)
                for i,s in enumerate(slots):
                    a,b,pct,_,_=get_fields(s,self.readings or {})
                    xx=95+i*cell
                    txt(p,LABELS[s]+' '+a,xx,min(21,h-6),max(8,min(10,int(cell/13))),PALE,i==0)
                    if i:pen(p,QColor(20,144,220,95),1);p.drawLine(QPointF(xx-5,5),QPointF(xx-5,h-5))
            txt(p,'◈  SYS READY',w-122,min(21,h-6),10,BLUE,True)
            p.end();return
        # Cover baked-in demonstration text from the reference shell with native
        # graphite-glass panels. All new labels below come from real readings.
        p.fillRect(QRectF(0,h*.25,w*.115,h*.50),QColor(2,12,28,206))
        txt(p,'N3XV5',max(8,w*.025),h*.48,max(12,min(17,h*.17)),PALE,True)
        txt(p,'TOP  /  NATIVE',max(8,w*.025),h*.66,max(7,min(10,h*.09)),BLUE)
        for slot in self.active_slots:
            area=module_rect(self,slot)
            r=QRectF(area).adjusted(2,4,-2,-4)
            if r.width()<30:continue
            shape=polygon(r)
            grad=QLinearGradient(r.topLeft(),r.bottomRight())
            grad.setColorAt(0,QColor(8,39,75,232));grad.setColorAt(.50,QColor(4,15,33,240));grad.setColorAt(1,QColor(10,24,44,225))
            p.save();p.setOpacity(max(.45,min(1,prefs['contrast']/100)));p.fillPath(shape,QBrush(grad));p.restore()
            c=BLUE if self._hover_slot==slot else QColor(23,113,217,210)
            p.save();p.setOpacity(max(.1,prefs['glow']/100));pen(p,c,1.25);p.drawPath(shape);p.restore()
            pen(p,QColor(45,212,255,145),1)
            p.drawLine(QPointF(r.left()+12,r.top()+3),QPointF(r.left()+min(43,r.width()*.42),r.top()+3))
            p.setPen(Qt.PenStyle.NoPen)
            p.fillRect(QRectF(r.right()-20,r.bottom()-3,14,2),RED)
            # Dynamic PCB impulse follows each module's top rail.
            if prefs['motion']:
                xx=r.left()+12+(r.width()-32)*phase
                gg=QRadialGradient(QPointF(xx,r.top()+2),min(14,r.width()*.10))
                gg.setColorAt(0,QColor(215,255,255,220));gg.setColorAt(.45,QColor(9,206,255,90));gg.setColorAt(1,QColor(0,74,255,0))
                p.setPen(Qt.PenStyle.NoPen);p.setBrush(gg);p.drawEllipse(QPointF(xx,r.top()+2),8,6)
            main,secondary,pct,gval,gmax=get_fields(slot,self.readings or {})
            x=r.left()+12
            txt(p,LABELS[slot],x,r.top()+min(20,h*.21),max(10,min(13,h*.14)),PALE,True)
            if slot in ('cpu','fans') and r.width()>90:
                radius=min(h*.27,(r.width()-25)*.27)
                cx=r.left()+r.width()*.67;cy=r.top()+h*.52
                gauge(p,cx,cy,radius,gval,gmax,LABELS[slot],phase)
                txt(p,secondary,x,r.bottom()-12,max(7,min(9,h*.10)),MUTED)
                if slot=='cpu':txt(p,main,x,r.top()+h*.52,max(11,min(17,h*.17)),BLUE,True)
            else:
                txt(p,main,x,r.top()+h*.48,max(11,min(19,h*.21)),BLUE,True)
                txt(p,secondary,x,r.top()+h*.64,max(7,min(10,h*.10)),MUTED)
                if pct is not None:
                    segments(p,x,r.bottom()-18,max(15,r.width()-25),4,pct)
                if slot=='storage':
                    # Show source-backed manufacturer throughput or nominal SATA
                    # ceiling. Never substitute a benchmark as manufacturer data.
                    data=self.readings or {}
                    read=_number(data,'storage_datasheet_read_mbs')
                    write=_number(data,'storage_datasheet_write_mbs')
                    if read is not None or write is not None:
                        note=f"SSD fiche: {_fmt(read,0)}↓/{_fmt(write,0)}↑ MB/s"
                    else:
                        note=storage_caps(data) or 'Lien : débit non déterminé'
                    txt(p,note[:37],x,r.bottom()-5,max(6,min(8,h*.075)),MUTED)
                if slot=='network':
                    note=SPEED_TEST.summary()
                    txt(p,note[:32],x,r.bottom()-5,max(6,min(8,h*.075)),MUTED)
            # Small module icon in the same native geometric contract as Holo.
            icon_rect=module_icon_rect(self,slot)
            from healthbar.hud import icon as legacy_icon
            if icon_rect.width()>0:
                legacy_icon(p,slot,icon_rect.x(),icon_rect.y(),icon_rect.width())
        # Utility area is actually part of our same Qt canvas (not another UI).
        right=w*.845
        p.fillRect(QRectF(right,8,w-right-6,h-16),QColor(2,17,34,242))
        pen(p,QColor(20,151,244,180),1.2)
        p.drawLine(QPointF(right,8),QPointF(right,h-7))
        txt(p,'SYS READY',right+12,h*.37,max(9,min(12,h*.12)),PALE,True)
        # A compact gear-chip with a fine cyan frame, not an oversized label.
        bx=right+12;by=h*.51;bw=min(95,w-right-24);bh=min(28,h*.28)
        button=polygon(QRectF(bx,by,bw,bh),5)
        p.fillPath(button,QColor(8,35,59,215));pen(p,QColor(21,153,221,155),.8);p.drawPath(button)
        txt(p,'⚙  RÉGLAGES',bx+9,by+bh*.69,max(8,min(10,bh*.43)),PALE,True)
        pen(p,BLUE,1.5);p.drawLine(QPointF(2,h-3),QPointF(w-2,h-3))
        p.end()
    HudCanvas.paintEvent=paint
    HudCanvas.module_rect=module_rect
    HudCanvas.module_icon_rect=module_icon_rect
    HudCanvas.module_at=module_at
    return HudCanvas



def _settings_workspace_bounds(screen_rect, available_rect, top_rect=None, bottom_rect=None):
    """Return a usable (left, top, right-exclusive, bottom-exclusive) rectangle.

    X11 WM workarea is authoritative when present. Native HUD geometry is a
    further guard while EWMH struts catch up with retract/reveal transitions.
    Pure geometry helper: no PySide6 dependency; deterministic unit tests.
    """
    sx, sy, sw, sh = screen_rect
    ax, ay, aw, ah = available_rect
    left = max(sx, ax)
    top = max(sy, ay)
    right = min(sx + sw, ax + aw)
    bottom = min(sy + sh, ay + ah)
    if top_rect is not None:
        tx, ty, tw, th = top_rect
        if th > 0 and ty <= sy + 2 and tx < right and tx + tw > left:
            top = max(top, ty + th)
    if bottom_rect is not None:
        bx, by, bw, bh = bottom_rect
        if bh > 0 and by + bh >= sy + sh - 2 and bx < right and bx + bw > left:
            bottom = min(bottom, by)
    # Broken/stale WM workarea must not produce a negative window geometry.
    if right <= left or bottom <= top:
        return (sx, sy, sx + sw, sy + sh)
    return left, top, right, bottom


def _settings_window_rect(bounds, preferred=(760, 610), margin=12, decoration=38):
    """Return client-area x,y,w,h, leaving room for the window manager frame."""
    left, top, right, bottom = bounds
    avail_w = max(160, right - left - 2 * margin)
    avail_h = max(120, bottom - top - 2 * margin - decoration)
    width = min(preferred[0], avail_w)
    height = min(preferred[1], avail_h)
    x = left + max(0, (right - left - width) // 2)
    # y includes the expected titlebar frame, preventing the footer from
    # touching or hiding behind the bottom taskbar.
    y = top + margin + decoration
    return int(x), int(y), int(width), int(height)


def _make_settings_dialog(bar,prefs,prefpath,apply_callback):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
        QCheckBox,QSpinBox,QSlider,QPushButton,QGroupBox,QWidget,QScrollArea,QFrame,QApplication)
    dlg=QDialog(bar)
    dlg.setWindowTitle('N3XV5 — Paramètres TOP HUD')
    # Do not trust Qt's default parent-relative dialog placement: the parent
    # TopBar sits on the screen edge and can push the dialog under BottomDock.
    from PySide6.QtCore import QTimer
    screen=QApplication.screenAt(bar.geometry().center()) or QApplication.primaryScreen()
    dlg.setMinimumSize(240, 190)
    dlg.resize(660, 550)
    dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground,False)
    dlg.setStyleSheet('''
      QDialog { background: #061223; color: #d7f7ff; border: 1px solid #136dba; }
      QScrollArea { background: #061223; border: 0; }
      QScrollArea > QWidget > QWidget { background: #061223; }
      QScrollBar:vertical { background:#071b2e; width:10px; margin:0; }
      QScrollBar::handle:vertical { background:#146aa2; min-height:26px; border-radius:4px; }
      QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
      QLabel,QCheckBox,QGroupBox { color: #d5f5ff; font-size: 12px; }
      QGroupBox { background: rgba(12,33,57,210); border: 1px solid #146c9d;
                  margin-top: 15px; padding: 16px 8px 8px; font-weight:bold; }
      QGroupBox::title { color:#26dfff; subcontrol-origin: margin; left:12px; padding:0 6px; }
      QPushButton { background: #0d3155; color: #aeeaff; border:1px solid #178fe9;
                    padding:9px; font-weight:bold; }
      QPushButton:hover { background: #13527e; border:1px solid #2be7ff; }
      QSpinBox { background:#061a32; color:#d8faff; border:1px solid #1486d3;
                 min-width:68px; padding:4px; }
      QSlider::groove:horizontal { background:#0e355c; height:5px; }
      QSlider::handle:horizontal { background:#24dfff; width:14px; margin:-5px 0; }
      QCheckBox::indicator { width:17px;height:17px; border:1px solid #268bf5; background:#04152a; }
      QCheckBox::indicator:checked { background:#20bded; border:1px solid #94faff; }
    ''')
    root=QVBoxLayout(dlg)
    root.setContentsMargins(12,10,12,10)
    root.setSpacing(7)
    hd=QLabel('N3XV5    /    TOP HUD  •  CONFIGURATION NATIVE XFCE')
    hd.setStyleSheet('color:#40e4ff;font-size:17px;font-weight:bold;padding:10px;')
    root.addWidget(hd)
    scroll=QScrollArea(dlg)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    contents=QWidget()
    contents.setObjectName('n3xvsSettingsContents')
    content_layout=QVBoxLayout(contents)
    content_layout.setContentsMargins(4,4,8,4)
    content_layout.setSpacing(12)
    scroll.setWidget(contents)
    root.addWidget(scroll,1)
    group=QGroupBox('COMPORTEMENT / AFFICHAGE')
    grid=QGridLayout(group)
    always=QCheckBox('Toujours afficher la barre (désactive la rétraction automatique)')
    always.setChecked(prefs['always_visible']);grid.addWidget(always,0,0,1,2)
    height=QSpinBox();height.setRange(60,150);height.setSuffix(' px');height.setValue(prefs['height'])
    delay=QSpinBox();delay.setRange(1,30);delay.setSuffix(' s');delay.setValue(prefs['hide_delay_s'])
    grid.addWidget(QLabel('Hauteur déployée'),1,0);grid.addWidget(height,1,1)
    grid.addWidget(QLabel('Délai de rétraction après départ'),2,0);grid.addWidget(delay,2,1)
    grid.addWidget(QLabel('Survol du haut de l’écran pour ouvrir : 2 secondes'),3,0,1,2)
    content_layout.addWidget(group)
    plugin_group=QGroupBox('PLUGINS — AFFICHER / MASQUER')
    plugin_grid=QGridLayout(plugin_group)
    boxes={}
    for i,s in enumerate(SLOTS):
        cb=QCheckBox(LABELS[s]);cb.setChecked(s not in prefs['hidden_modules'])
        plugin_grid.addWidget(cb,i//4,i%4);boxes[s]=cb
    content_layout.addWidget(plugin_group)
    effects=QGroupBox('LUMINOSITÉ / EFFETS')
    eg=QGridLayout(effects)
    glow=QSlider(Qt.Orientation.Horizontal);glow.setRange(0,100);glow.setValue(prefs['glow'])
    eg.addWidget(QLabel('Intensité néon'),0,0);eg.addWidget(glow,0,1)
    opacity=QSlider(Qt.Orientation.Horizontal);opacity.setRange(20,100);opacity.setValue(prefs['opacity'])
    contrast=QSlider(Qt.Orientation.Horizontal);contrast.setRange(40,140);contrast.setValue(prefs['contrast'])
    eg.addWidget(QLabel('Opacité TopBar'),1,0);eg.addWidget(opacity,1,1)
    eg.addWidget(QLabel('Contraste modules'),2,0);eg.addWidget(contrast,2,1)
    motion=QCheckBox('Animations de pistes PCB activées');motion.setChecked(prefs['motion'])
    holo=QCheckBox('Holo Qt activés');holo.setChecked(prefs['holo_enabled'])
    eg.addWidget(motion,3,0,1,2);eg.addWidget(holo,4,0,1,2)
    content_layout.addWidget(effects)
    navigation=QGroupBox('NAVBAR BOTTOM — TASKBAR NATIVE')
    ng=QGridLayout(navigation)
    bottom_enabled=QCheckBox('Afficher la barre de navigation inférieure')
    bottom_enabled.setChecked(prefs['bottom_enabled'])
    bottom_height=QSpinBox(); bottom_height.setRange(62,94); bottom_height.setSuffix(' px')
    bottom_height.setValue(prefs['bottom_height'])
    bottom_opacity=QSpinBox();bottom_opacity.setRange(15,85);bottom_opacity.setSuffix(' %')
    bottom_opacity.setValue(prefs['bottom_opacity'])
    ng.addWidget(bottom_enabled,0,0,1,2)
    ng.addWidget(QLabel('Hauteur Navbar'),1,0);ng.addWidget(bottom_height,1,1)
    ng.addWidget(QLabel('Opacité Navbar'),2,0);ng.addWidget(bottom_opacity,2,1)
    content_layout.addWidget(navigation)
    perf_group=QGroupBox('PERFORMANCES / RAFRAÎCHISSEMENT')
    pg=QGridLayout(perf_group)
    telemetry_s=QSpinBox();telemetry_s.setRange(1,15);telemetry_s.setSuffix(' s')
    telemetry_s.setValue(prefs['telemetry_refresh_s'])
    visual_fps=QSpinBox();visual_fps.setRange(5,30);visual_fps.setSuffix(' FPS')
    visual_fps.setValue(prefs['visual_fps'])
    hourly=QCheckBox('Test Internet automatique toutes les heures (consomme des données)')
    hourly.setChecked(prefs['net_speedtest_hourly'])
    test_now=QPushButton('↻  REFRESH — TEST DÉBIT INTERNET')
    test_state=QLabel('Test Internet : aucun résultat enregistré pour cette session')
    pg.addWidget(QLabel('Télémétrie'),0,0);pg.addWidget(telemetry_s,0,1)
    pg.addWidget(QLabel('Animations maximales'),1,0);pg.addWidget(visual_fps,1,1)
    pg.addWidget(hourly,2,0,1,2);pg.addWidget(test_now,3,0,1,2)
    pg.addWidget(test_state,4,0,1,2)
    from n3xvs_metrics import SPEED_TEST
    test_now.clicked.connect(lambda: (SPEED_TEST.start(),test_state.setText('Test en cours ou déjà lancé…')))
    test_timer=QTimer(dlg);test_timer.setInterval(1000)
    test_timer.timeout.connect(lambda: test_state.setText(SPEED_TEST.summary()))
    test_timer.start()
    content_layout.addWidget(perf_group)
    turbo_group=QGroupBox('CPU — TURBO BOOST (AUTORISATION SYSTÈME)')
    tg=QGridLayout(turbo_group)
    turbo_status=QLabel('État : lecture du commutateur noyau…')
    turbo_toggle=QPushButton('CHANGER TURBO ON / OFF')
    tg.addWidget(turbo_status,0,0,1,2)
    tg.addWidget(turbo_toggle,1,0,1,2)
    content_layout.addWidget(turbo_group)

    def turbo_status_read():
        from healthbar.cpu_backends import system_backend
        try:
            state=system_backend().read()
            return state, ('Turbo actif' if state else 'Turbo désactivé')
        except (OSError,ValueError) as exc:
            return None, str(exc)

    current,caption=turbo_status_read()
    turbo_status.setText('État du noyau : '+caption)
    turbo_toggle.setEnabled(current is not None)

    def do_turbo():
        import shutil
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtCore import QProcess
        current,caption=turbo_status_read()
        if current is None:
            QMessageBox.warning(dlg,'Turbo indisponible',caption);return
        desired=not current
        action='ACTIVER' if desired else 'DÉSACTIVER'
        if QMessageBox.question(dlg,'Confirmation Turbo',
            f'{action} le Turbo CPU ?\n\nCette action agit sur le commutateur noyau et nécessite une autorisation administrateur.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
            return
        if shutil.which('pkexec') is None:
            QMessageBox.warning(dlg,'Polkit absent','Installer policykit-1 / pkexec et un agent Polkit XFCE.');return
        helper='/usr/local/libexec/n3xvs-hud-turbo'
        import os
        if not os.path.isfile(helper):
            QMessageBox.warning(dlg,'Utilitaire manquant','Relancer l’installateur N3XV5 pour installer l’utilitaire root.');return
        if getattr(bar,'_n3xvs_turbo_process',None) is not None:
            return
        proc=QProcess(bar)
        bar._n3xvs_turbo_process=proc
        turbo_toggle.setEnabled(False)
        turbo_status.setText('Demande d’autorisation système en cours…')
        proc.setProgram('pkexec')
        proc.setArguments([helper,'on' if desired else 'off'])
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        def completed(code,exit_status):
            bar._n3xvs_turbo_process=None
            actual,message=turbo_status_read()
            if dlg.isVisible():
                turbo_status.setText('État du noyau : '+message)
                turbo_toggle.setEnabled(actual is not None)
            if code!=0 or actual is not desired:
                QMessageBox.warning(bar,'Turbo non modifié',
                    'Commande refusée, indisponible ou non appliquée.\n'+
                    bytes(proc.readAllStandardOutput()).decode('utf-8','replace')[-900:])
            proc.deleteLater()
        proc.finished.connect(completed)
        proc.errorOccurred.connect(lambda err: None)
        proc.start()
    turbo_toggle.clicked.connect(do_turbo)
    info=QLabel('Les mesures et les Holo proviennent de NovaBar 0.8.2.2. Les données indisponibles restent « — ».')
    info.setWordWrap(True);info.setStyleSheet('color:#82bedc;');content_layout.addWidget(info)
    content_layout.addStretch(1)
    buttons=QHBoxLayout();cancel=QPushButton('ANNULER');apply=QPushButton('APPLIQUER')
    buttons.addStretch();buttons.addWidget(cancel);buttons.addWidget(apply);root.addLayout(buttons)
    cancel.clicked.connect(dlg.reject)
    def commit():
        prefs.update(height=height.value(),always_visible=always.isChecked(),hide_delay_s=delay.value(),
                     glow=glow.value(),opacity=opacity.value(),contrast=contrast.value(),motion=motion.isChecked(),holo_enabled=holo.isChecked(),
                     hidden_modules=[s for s,cb in boxes.items() if not cb.isChecked()],
                     bottom_enabled=bottom_enabled.isChecked(),bottom_height=bottom_height.value(),
                     bottom_opacity=bottom_opacity.value(),telemetry_refresh_s=telemetry_s.value(),
                     visual_fps=visual_fps.value(),net_speedtest_hourly=hourly.isChecked())
        _save_prefs(prefpath,prefs)
        apply_callback();dlg.accept()
    apply.clicked.connect(commit)

    # Read the WM workarea again while the modal dialog is displayed. XFCE's
    # usable region changes asynchronously when the TopBar retracts/reveals.
    # The geometry is clamped, not continuously re-centered on every tick.
    last_bounds = [None]
    def _bounds_now():
        current_screen=QApplication.screenAt(bar.geometry().center()) or QApplication.primaryScreen()
        if current_screen is None:
            return (0, 0, 1280, 800)
        sr=current_screen.geometry()
        ar=current_screen.availableGeometry()
        top_rect=None
        if not bar.retracted and bar.isVisible():
            r=getattr(bar, 'full_rect', bar.geometry())
            top_rect=(r.x(), r.y(), r.width(), r.height())
        dock=getattr(bar, 'bottom_dock', None)
        bottom_rect=None
        if dock is not None and dock.isVisible() and not getattr(dock, 'collapsed', False):
            r=getattr(dock, 'full_rect', dock.geometry())
            bottom_rect=(r.x(), r.y(), r.width(), r.height())
        return _settings_workspace_bounds(
            (sr.x(), sr.y(), sr.width(), sr.height()),
            (ar.x(), ar.y(), ar.width(), ar.height()), top_rect, bottom_rect)

    def fit_settings_window(force=False):
        bounds=_bounds_now()
        # Reconcile EWMH struts and parent geometry only after changes; avoid
        # interfering with manual resizing/moving while the screen is steady.
        if not force and bounds == last_bounds[0]:
            return
        last_bounds[0]=bounds
        x, y, w, h=_settings_window_rect(bounds, preferred=(700, 610))
        if force:
            dlg.setGeometry(x, y, w, h)
            return
        # Preserve user's smaller size, but move/resize when it would overflow.
        from PySide6.QtCore import QRect
        current=dlg.geometry()
        w=min(current.width(), w)
        h=min(current.height(), h)
        margin=12
        left, top, right, bottom=bounds
        minimum_y=top+margin+38
        nx=max(left+margin, min(current.x(), right-margin-w))
        ny=max(minimum_y, min(current.y(), bottom-margin-h))
        dlg.setGeometry(QRect(nx, ny, w, h))

    fit_settings_window(force=True)
    timer=QTimer(dlg)
    timer.setInterval(300)
    timer.timeout.connect(fit_settings_window)
    # Run only during the modal session, never poll the workspace in background.
    dlg.finished.connect(timer.stop)
    from PySide6.QtCore import QTimer as _Timer
    _Timer.singleShot(0, lambda: fit_settings_window(force=True))
    timer.start()
    return dlg


def main():
    parser=argparse.ArgumentParser(description='N3XV5 native Qt/XFCE top + bottom; no webpage')
    parser.add_argument('--legacy',help='NovaBar 0.8.2.2 source repository')
    parser.add_argument('--height',type=int,default=None)
    parser.add_argument('--preview',help='Export PNG offscreen and exit')
    args=parser.parse_args()
    legacy=_legacy_path(args.legacy)
    if not (legacy/'src/healthbar/app.py').is_file():
        parser.error('NovaBar 0.8.2.2 source missing; use start_n3xvs_native.sh')
    if not args.preview and not os.environ.get('DISPLAY'):
        parser.error('Native XFCE/X11 session required (DISPLAY missing)')
    if not args.preview and os.environ.get('XDG_SESSION_TYPE','x11')=='wayland':
        parser.error('Prototype requires X11')
    sys.path.insert(0,str(legacy/'src'))
    os.environ.setdefault('HEALTHBAR_DATA_DIR',str(Path.home()/'.config/n3xvs-hud'))
    configroot=Path(os.environ['HEALTHBAR_DATA_DIR'])
    prefpath=configroot/'n3xvs-unified.json'
    prefs=_load_prefs(prefpath)
    if args.height is not None:
        prefs['height']=max(60,min(150,args.height))
    if args.preview:
        os.environ['QT_QPA_PLATFORM']='offscreen'
    from PySide6.QtCore import QLockFile,QTimer,Qt
    from PySide6.QtWidgets import QApplication
    from healthbar.config import Settings
    from healthbar.app import Bar
    sys.path.insert(0, str(ROOT))
    from App.Modules.Bottom.HUD_HomeNavBar.NativeQt.slim_style import apply_skin
    apply_skin()
    _install_qt_painter(prefs)
    from n3xvs_metrics import SPEED_TEST
    app=QApplication([sys.argv[0]])
    app.setApplicationName('N3XV5 HUD Theme • Unified Qt XFCE')
    app.setQuitOnLastWindowClosed(False)
    # Strictly separate from ~/.config/health-perfs-bar and installed executables.
    settings=Settings(configured=True,theme='blue-neon',position='top',thickness=prefs['height'],
        hud_enabled=True,dock_left_enabled=False,dock_right_enabled=False,bottom_dock_enabled=prefs['bottom_enabled'],
        bottom_dock_height=prefs['bottom_height'],bottom_nav_opacity=prefs['bottom_opacity'],
        xfce_skin_enabled=False,auto_hide=not prefs['always_visible'],
        retract_mode='manual' if prefs['always_visible'] else 'auto',
        top_reserved=True,top_hover_ms=2000,top_trigger_px=10,hide_seconds=max(3,prefs['hide_delay_s']),
        always_on_top=True,length_percent=100,opacity=prefs['opacity'],
        hidden_modules=prefs['hidden_modules'],holo_enabled=prefs['holo_enabled'],autostart=False)
    settings.slot_order=SLOTS.copy()
    settings.validate()
    configroot.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(configroot/'n3xvs-top-native.lock'))
    if not lock.tryLock(100):
        raise SystemExit('Une instance N3XV5 native est déjà active.')
    bar=Bar(settings)
    # Original NovaBar reserves top screen space even when collapsed.
    # For N3XV5 release the TOP strut entirely while retracted; a maximized
    # window can then occupy the top edge. The BOTTOM dock has its own strut.
    from healthbar.x11_workarea import reserve_edge
    def n3xvs_reserve_top_workarea():
        if not settings.hud_enabled or not settings.top_reserved or bar.retracted:
            reserve_edge(bar,'top',0,False)
        else:
            reserve_edge(bar,'top',bar.geometry().height(),True)
    bar._reserve_workarea=n3xvs_reserve_top_workarea
    bar._reserve_workarea()
    if bar.bottom_dock is not None:
        bar.bottom_dock.row.setContentsMargins(8,5,8,5)
        bar.bottom_dock.row.setSpacing(3)
        bar.bottom_dock.pins.setSpacing(2)
        bar.bottom_dock.tasks.setSpacing(3)
    # The historical Settings schema enforces 3..120 seconds for hide_seconds.
    # Keep its config valid and implement the N3XV5 2-second timeout directly
    # on the existing QTimer, without modifying NovaBar's source or user profile.
    def n3xvs_arm_hide():
        bar.hide_timer.stop()
        if (settings.retract_mode == 'auto' and not bar.busy and not bar.retracted):
            bar.hide_timer.start(max(1000, int(prefs['hide_delay_s']) * 1000))
    bar.arm_hide = n3xvs_arm_hide
    bar.setWindowTitle('N3XV5 — Native Qt TOP HUD')
    bar.root.setSpacing(0)
    bar.actions.hide()
    bar.chip_logo.hide()
    bar.canvas.slot_order=SLOTS.copy()
    bar.canvas.hidden_modules=list(prefs['hidden_modules'])
    # Do not show legacy redundant action controls / badges; native canvas
    # paints the full shell. The original button handlers still exist.
    def apply_prefs():
        settings.thickness=prefs['height']
        settings.bottom_dock_enabled=prefs['bottom_enabled']
        settings.bottom_dock_height=prefs['bottom_height']
        settings.bottom_nav_opacity=prefs['bottom_opacity']
        settings.hidden_modules=prefs['hidden_modules'][:]
        settings.holo_enabled=prefs['holo_enabled']
        settings.hide_seconds=max(3,prefs['hide_delay_s'])
        settings.top_hover_ms=2000
        settings.retract_mode='manual' if prefs['always_visible'] else 'auto'
        settings.auto_hide=not prefs['always_visible']
        settings.validate()
        bar.apply_settings()
        bar.sync_xfce_skin()
        if bar.bottom_dock is not None:
            try:
                bar.bottom_dock.settings_requested.disconnect()
            except (RuntimeError,TypeError):
                pass
            bar.bottom_dock.settings_requested.connect(show_settings)
            bar.bottom_dock.row.setContentsMargins(8,5,8,5)
            bar.bottom_dock.row.setSpacing(3)
            bar.bottom_dock.pins.setSpacing(2)
            bar.bottom_dock.tasks.setSpacing(3)
        bar.actions.hide();bar.root.setSpacing(0)
        bar.canvas.hidden_modules=prefs['hidden_modules'][:]
        bar.canvas.update()
        # Native telemetry runs on a shared worker; do not spawn a second probe.
        try:
            settings.refresh_seconds=prefs['telemetry_refresh_s']
            bar.sensor_timer.setInterval(prefs['telemetry_refresh_s']*1000)
        except (AttributeError,ValueError):pass
        try:
            bar.canvas.visual_timer.setInterval(max(33,round(1000/prefs['visual_fps'])))
        except (AttributeError,ValueError):pass
        if prefs['always_visible'] and bar.retracted:bar.reveal()
        if not prefs['always_visible']:bar.arm_hide()
    # Wrap old methods so its transition never shows the retired action column.
    old_finish=bar._finish_transition
    def finish():
        old_finish();bar.actions.hide();bar.root.setSpacing(0)
    bar._finish_transition=finish
    old_reveal=bar.reveal
    def reveal():
        old_reveal();bar.actions.hide();bar.root.setSpacing(0)
    bar.reveal=reveal
    # Keep native Holo panels, even when plugin manager has not installed
    # a ZIP viewer in this isolated test profile.
    def open_holo(slot):
        if not prefs['holo_enabled']:return
        from PySide6.QtWidgets import QApplication
        if slot=='cpu':
            panel=bar.holo
        else:
            panel=bar.module_holos.get(slot)
        if panel is None:return
        if panel.isVisible():panel.close_panel();return
        screen=QApplication.screens()[min(settings.screen,len(QApplication.screens())-1)]
        panel.set_telemetry(bar.canvas.readings or {})
        panel.show_at(bar.canvas.module_global_rect(slot),screen.availableGeometry(),'top')
    bar.canvas.module_activated.disconnect()
    bar.canvas.module_activated.connect(open_holo)
    def show_settings():
        bar.busy=True;bar.hide_timer.stop()
        try:
            dlg=_make_settings_dialog(bar,prefs,prefpath,apply_prefs)
            dlg.exec()
        finally:
            bar.busy=False;bar.arm_hide()
    # Native canvas's right-hand menu is drawn in QPainter and clickable.
    old_release=bar.canvas.mouseReleaseEvent
    def release(event):
        if event.button()==Qt.MouseButton.LeftButton and event.position().x()>=bar.canvas.width()*.845:
            bar.canvas._drag_origin=None;bar.canvas._drag_start=None
            show_settings();return
        old_release(event)
    bar.canvas.mouseReleaseEvent=release
    # The old gear and bottom navbar open the same unified settings page.
    bar.preferences=show_settings
    apply_prefs()
    # Hourly Internet tests are off by default. Even when enabled, the service
    # enforces a 1-hour minimum between attempts and runs off the UI thread.
    from PySide6.QtCore import QTimer as _N3QTimer
    speed_timer=_N3QTimer(bar);speed_timer.setInterval(60000)
    speed_timer.timeout.connect(lambda: SPEED_TEST.start(automatic=True)
        if prefs['net_speedtest_hourly'] else None)
    speed_timer.start()
    if args.preview:
        bar.resize(1600,prefs['height']);bar.show();app.processEvents()
        out=Path(args.preview).expanduser().resolve()
        if not bar.grab().save(str(out)):
            raise SystemExit('Failed to save preview')
        bar.close();return 0
    bar.show()
    app.aboutToQuit.connect(bar.close)
    return app.exec()

if __name__=='__main__':raise SystemExit(main())

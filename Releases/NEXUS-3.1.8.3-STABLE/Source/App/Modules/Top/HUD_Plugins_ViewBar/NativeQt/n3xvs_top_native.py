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
ASSET = ROOT / 'App/Modules/Top/HUD_Plugins_ViewBar/Assets/nexus_v3_neon_shell.png'
DEFAULTS = {'height': 100, 'always_visible': False, 'hide_delay_s': 2,
            'edge_hover_ms': 2000, 'opacity': 82, 'contrast': 90, 'glow': 80, 'motion': True,
            'holo_enabled': True, 'hidden_modules': [], 'bottom_enabled': True, 'bottom_height': 56, 'bottom_opacity': 46,
            'telemetry_refresh_s': 2, 'visual_fps': 15, 'net_speedtest_hourly': False, 'fan_max_rpm': {}}
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


def _fan_reference(fan, prefs):
    """Prefer explicit user reference, otherwise hardware-provided max."""
    if not isinstance(fan,dict):
        return None, 'indisponible'
    key=str(fan.get('name') or '').strip().lower()[:80]
    saved=prefs.get('fan_max_rpm') or {}
    manual=saved.get(key) if isinstance(saved,dict) else None
    if type(manual) is int and 100 <= manual <= 30000:
        return manual, 'référence utilisateur'
    actual=_number(fan,'max_rpm')
    if actual is not None and actual > 0:
        return actual, 'capteur noyau'
    return None, 'max inconnu'


def _fan_percent(rpm, maximum):
    if rpm is None or maximum is None or maximum <= 0:
        return None
    return max(0,min(100,round(100 * rpm / maximum)))


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
                    ('opacity',20,100),('contrast',40,140),('glow',0,100),('bottom_height',44,100),('bottom_opacity',15,85),
                    ('telemetry_refresh_s',1,15),('visual_fps',5,30)]:
        v=data.get(k)
        data[k]=max(lo,min(hi,int(v))) if type(v) in (int,float) else DEFAULTS[k]
    for k in ('always_visible','motion','holo_enabled','bottom_enabled','net_speedtest_hourly'):
        data[k]=data[k] if type(data[k]) is bool else DEFAULTS[k]
    # Persistent user reference RPMs, with bounded values and safe identifiers.
    limits=data.get('fan_max_rpm')
    data['fan_max_rpm']={str(name).strip().lower()[:80]:int(rpm) for name,rpm in (limits.items() if isinstance(limits,dict) else [])
                         if isinstance(name,str) and type(rpm) is int and 100 <= rpm <= 30000}
    x=data.get('hidden_modules',[])
    data['hidden_modules']=[s for s in SLOTS if s in x] if isinstance(x,list) else []
    return data


def _save_prefs(path, prefs):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(prefs,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    temp.replace(path)
    from n3xvs_network_archive import backup_runtime_preferences
    backup_runtime_preferences(path,prefs)


# NEXUS_HYBRID_P5_ASSET_20_SEGMENTS
# NEXUS_HYBRID_P5_1_DIALS_ONLY_CPU_FANS
# NEXUS_V313_PING_LAYOUT
_NEXUS_V31_PING_MS = None
def _install_qt_painter(prefs):
    from PySide6.QtCore import Qt,QRectF,QPointF,QRect
    from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen,QBrush,QLinearGradient,QRadialGradient,QFont,QImage
    from healthbar.hud import HudCanvas
    from n3xvs_metrics import power_labels, storage_caps, SPEED_TEST, POWER_PROBE
    from n3xvs_storage_bench import STORAGE_BENCH

    BLUE=QColor('#17dfff'); ROYAL=QColor('#1378ff'); RED=QColor('#c31838')
    PALE=QColor('#ddf9ff'); MUTED=QColor('#79abc7')
    shell=QImage(str(ASSET))
    def pen(p,color,width=1): p.setPen(QPen(color,width))
    # N3XV5 V2.4.3: uniform +1px typography for all TOP modules
    FONT_BUMP=1
    def txt(p,s,x,y,sz=11,color=PALE,bold=False,align=None,width=0,max_width=None):
        font=QFont('DejaVu Sans');font.setPixelSize(max(8,int(sz)+FONT_BUMP));font.setBold(bold)
        p.setFont(font);pen(p,color)
        label=str(s)
        if max_width is not None:
            # Elide text against its OWN module width, not the full screen.
            from PySide6.QtGui import QFontMetrics
            label=QFontMetrics(font).elidedText(label,Qt.TextElideMode.ElideRight,max(1,int(max_width)))
        if align is not None:
            p.drawText(QRectF(x,y,width,sz+FONT_BUMP+6),align,label)
        else:p.drawText(QPointF(x,y),label)
    def polygon(r,cut=9):
        x,y,w,h=r.x(),r.y(),r.width(),r.height();c=min(cut,w*.12,h*.25)
        path=QPainterPath(QPointF(x+c,y))
        for a,b in ((x+w-c,y),(x+w,y+c),(x+w,y+h-c),(x+w-c,y+h),
                    (x+c,y+h),(x,y+h-c),(x,y+c)):path.lineTo(a,b)
        path.closeSubpath();return path
    def segments(p,x,y,w,h,pct):
        """NEXUS V3: 20 beveled bars, fixed zones 10 cyan / 5 green / 3 orange / 2 red.

        Lighting follows source-backed percent. Unknown values leave every LED off.
        """
        from PySide6.QtGui import QPolygonF
        palette=([QColor('#1bcfff')]*10 + [QColor('#30e785')]*5
                 + [QColor('#ffaa33')]*3 + [QColor('#fa345a')]*2)
        gap=max(0.75,min(1.8,w*.009))
        width=max(.1,(w-gap*19)/20)
        amount=None if pct is None else max(0.0,min(100.0,float(pct)))
        lit=0 if amount is None else min(20,math.ceil(amount/5))
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        # Track is rendered once; it is never an animated background layer.
        p.setBrush(QColor(2,12,30,238))
        p.drawRoundedRect(QRectF(x-2,y-2,w+4,h+4),2.5,2.5)
        for i,base in enumerate(palette):
            sx=x+i*(width+gap)
            bevel=min(width*.26,2.0)
            poly=QPolygonF([QPointF(sx+bevel,y), QPointF(sx+width,y),
                            QPointF(sx+width-bevel,y+h), QPointF(sx,y+h)])
            if i<lit:
                under=QColor(base);under.setAlpha(85)
                p.setBrush(under)
                p.drawRect(QRectF(sx,y+h-1,width,2))
                p.setBrush(base)
            else:
                # Dim segments keep the 4 fixed color zones recognizable.
                dim=QColor(base);dim.setAlpha(52)
                p.setBrush(dim)
            p.drawPolygon(poly)
        p.restore()
    def gauge(p,cx,cy,r,value,maxval,title,phase):
        """20 individually lit circular LED dots, centered numeric readout."""
        fraction=max(0.0,min(1.0,float(value)/maxval)) if value is not None and maxval>0 else 0.0
        lit=min(20,max(0,math.ceil(20*fraction)))
        palette=['#24bfff']*10+['#31dc78']*5+['#ff9c37']*3+['#f42b4b']*2
        p.save();p.setPen(Qt.PenStyle.NoPen)
        for i,shade in enumerate(palette):
            angle=math.radians(225-i*(270/19))
            pos=QPointF(cx+math.cos(angle)*r,cy-math.sin(angle)*r)
            rr=max(1.35,min(3.6,r*.11))
            if i<lit:
                color=QColor(shade);aura=QColor(shade);aura.setAlpha(40)
                p.setBrush(aura);p.drawEllipse(pos,rr+1.35,rr+1.35)
            else:color=QColor(31,65,88,165)
            p.setBrush(color);p.drawEllipse(pos,rr,rr)
        text=_fmt(value,2) if title=='CPU' and value is not None else (_fmt(value,0) if value is not None else '—')
        font=QFont('DejaVu Sans');font.setPixelSize(max(9,int(r*(.33 if title=='CPU' else .45))+FONT_BUMP));font.setBold(True)
        p.setFont(font);p.setPen(PALE if value is not None else MUTED)
        center=QRectF(cx-r*.72,cy-r*.38,r*1.44,r*.76)
        p.drawText(center,Qt.AlignmentFlag.AlignCenter,text)
        if title=='CPU' and value is not None:
            font.setPixelSize(max(8,int(r*.21)+FONT_BUMP));font.setBold(False);p.setFont(font);p.setPen(MUTED)
            p.drawText(QRectF(cx-r*.70,cy+r*.19,r*1.4,r*.38),Qt.AlignmentFlag.AlignCenter,'GHz')
        p.restore()
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
    def _net_rate(mbs):
        # Telemetry values are MB/s. At low traffic use kB/s or B/s,
        # otherwise the old two-decimal formatting displays misleading zeros.
        if mbs is None:return '—'
        if mbs >= 1:return f'{mbs:.2f} MB/s'
        if mbs >= .001:return f'{mbs*1000:.1f} kB/s'
        return f'{mbs*1000000:.0f} B/s'
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
            mem_type=str((data.get('ram_type') or data.get('memory_type') or data.get('memory_kind') or '')).upper().replace(' SDRAM','').strip()
            bars=data.get('ram_slots_used') or data.get('memory_slots_used') or data.get('ram_modules') or data.get('memory_modules')
            extra=[]
            if mem_type and mem_type not in ('NONE','UNKNOWN','—'):
                extra.append(mem_type)
            try:
                bars_int=int(bars)
                if bars_int>0:
                    extra.append(f'{bars_int} bar.')
            except (TypeError,ValueError):
                pass
            info=f'{_fmt(u,1)} / {_fmt(t,1)} GB'
            if extra:
                info+=' · '+' · '.join(extra)
            return _fmt(load,0,'%'),info,load,None,1
        if kind=='storage':
            load=n('disk_percent');u=n('disk_used_gb');t=n('disk_total_gb')
            return _fmt(load,0,'%'),f'{_fmt(u,1)} / {_fmt(t,1)} GB',load,None,1
        if kind=='fans':
            f=next((x for x in data.get('fans',[]) if isinstance(x,dict) and isinstance(x.get('rpm'),(float,int))),None)
            rpm=_number(f,'rpm') if f else None
            lim,source=_fan_reference(f,prefs)
            pct=_fan_percent(rpm,lim)
            # Only a compact percentage in the HUD; provenance stays in FANS Holo/settings.
            subtitle=f'{pct} %' if pct is not None else '— %'
            return _fmt(rpm,0,' RPM'),subtitle,pct,rpm,lim or 5000
        if kind=='network':
            d=n('net_down_mbs');u=n('net_up_mbs')
            return _net_rate(d),_net_rate(u),None,None,1
        if kind=='power':
            main,sub=power_labels({**(data or {}),**POWER_PROBE.snapshot()})
            return main,sub,None,None,1
        return '—','',None,None,1
# NEXUS_V316_SEVEN_SEGMENT_CLOCK
    # NEXUS V3.1.6: built-in 7-segment painter; no external font dependency.
    def _nexus_clock7(p,rect,clock):
        digits={'0':'abcdef','1':'bc','2':'abged','3':'abgcd',
                '4':'fgbc','5':'afgcd','6':'afgecd','7':'abc',
                '8':'abcdefg','9':'abcdfg'}
        # Segment positions in an abstract 20x34 digit.
        lines={
            'a':[(4,2),(16,2),(14,5),(6,5)],
            'g':[(4,16),(16,16),(14,19),(6,19)],
            'd':[(4,32),(16,32),(14,29),(6,29)],
            'f':[(3,4),(6,7),(6,14),(3,17)],
            'b':[(17,4),(14,7),(14,14),(17,17)],
            'e':[(3,19),(6,22),(6,29),(3,32)],
            'c':[(17,19),(14,22),(14,29),(17,32)],
        }
        # Four digits and a colon: 4*20+8+gaps.
        logical_w=98.0;logical_h=36.0
        scale=min(rect.width()/logical_w,rect.height()/logical_h)
        if scale<=0:return
        ox=rect.x()+(rect.width()-logical_w*scale)*.5
        oy=rect.y()+(rect.height()-logical_h*scale)*.5
        p.save();p.setPen(Qt.PenStyle.NoPen)
        for index,ch in enumerate(clock[:5]):
            x=0 if index==0 else 23 if index==1 else 46 if index==2 else 55 if index==3 else 78
            if ch==':':
                p.setBrush(QColor('#20eaff'))
                for cy in (12,25):
                    p.drawEllipse(QRectF(ox+(x+2)*scale,oy+cy*scale,2.8*scale,2.8*scale))
                continue
            for code in 'abcdefg':
                points=lines[code]
                path=QPainterPath()
                path.moveTo(QPointF(ox+(x+points[0][0])*scale,oy+points[0][1]*scale))
                for px,py in points[1:]:
                    path.lineTo(QPointF(ox+(x+px)*scale,oy+py*scale))
                path.closeSubpath()
                p.setBrush(QColor('#1df4fa') if code in digits.get(ch,'') else QColor(4,54,73,100))
                p.fillPath(path,p.brush())
        p.restore()
    def paint(self,event):
        self._n3xvs_net_refresh_rect=None
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
            # The compact native canvas has independent, centered instrument slots.
            p.fillRect(QRectF(0,1,w,h-2),QColor(3,12,29,235))
            pen(p,BLUE,1.4);p.drawLine(QPointF(0,h-2),QPointF(w,h-2))
            def compact_text(msg,rect,color=PALE,bold=False):
                p.save();p.setPen(color)
                font=QFont('DejaVu Sans');font.setBold(bold)
                size=10;font.setPixelSize(size);p.setFont(font)
                while size>7 and p.fontMetrics().horizontalAdvance(msg)>rect.width()-6:
                    size-=1;font.setPixelSize(size);p.setFont(font)
                p.drawText(rect,Qt.AlignmentFlag.AlignCenter,
                           p.fontMetrics().elidedText(msg,Qt.TextElideMode.ElideRight,max(1,int(rect.width()-6))))
                p.restore()
            brand_w=97;clock_w=90
            compact_text('N3XV5 v3.1.8',QRectF(3,1,brand_w-6,h-2),BLUE,True)
            slots=self.active_slots
            if slots:
                cell=max(1,w-brand_w-clock_w-6)/len(slots)
                for i,s in enumerate(slots):
                    a,b,pct,_,_=get_fields(s,self.readings or {})
                    xx=brand_w+i*cell
                    ping=_NEXUS_V31_PING_MS
                    msg=('DEBIT '+a+' - PING '+(f'{ping:.0f}ms' if ping is not None else '—')) if s=='network' else LABELS[s]+' '+a
                    compact_text(msg,QRectF(xx+3,1,max(1,cell-7),h-2),PALE,i==0)
                    if i:
                        pen(p,QColor(20,144,220,95),1)
                        p.drawLine(QPointF(xx,4),QPointF(xx,h-4))
            p.save()
            clock_font=QFont('DejaVu Sans Mono')
            clock_font.setBold(True);clock_font.setPixelSize(max(9,min(14,int(h*.53))))
            p.setFont(clock_font);p.setPen(BLUE)
            p.drawText(QRectF(w-clock_w,1,clock_w-3,h-2),
                       Qt.AlignmentFlag.AlignCenter,time.strftime('%H:%M'))
            p.restore()
            p.end();return
        # Cover baked-in demonstration text from the reference shell with native
        # graphite-glass panels. All new labels below come from real readings.
        p.fillRect(QRectF(0,h*.25,w*.115,h*.50),QColor(2,12,28,255))
        # Clean title plate: hide demonstration text baked into the visual asset.
        p.fillRect(QRectF(5,h*.25,w*.108,h*.5),QColor(2,14,35,255))
        txt(p,'N3XV5 v3.1.8',max(8,w*.019),h*.48,max(10,min(15,h*.15)),PALE,True)
        txt(p,'TOP  /  NATIVE',max(8,w*.025),h*.66,max(7,min(10,h*.09)),BLUE)
        for slot in self.active_slots:
            area=module_rect(self,slot)
            r=QRectF(area).adjusted(2,4,-2,-4)
            if r.width()<30:continue
            shape=polygon(r)
            grad=QLinearGradient(r.topLeft(),r.bottomRight())
            grad.setColorAt(0,QColor(8,39,75,232));grad.setColorAt(.50,QColor(4,15,33,240));grad.setColorAt(1,QColor(10,24,44,225))
            # NEXUS_HYBRID_P4_OPAQUE_INSTRUMENT_BACKPLATE
            # Opaque undercoat hides baked-in demo captions from reference_shell.png.
            # Keep original gradient + border + glow + animated PCB and instruments.
            p.fillPath(shape,QColor(4,15,33,178))
            p.save();p.setOpacity(max(.45,min(1,prefs['contrast']/100)));p.fillPath(shape,QBrush(grad));p.restore()
            c=BLUE if self._hover_slot==slot else QColor(23,113,217,210)
            p.save();p.setOpacity(max(.1,prefs['glow']/100));pen(p,c,1.25);p.drawPath(shape);p.restore()
            pen(p,QColor(45,212,255,145),1)
            p.drawLine(QPointF(r.left()+12,r.top()+3),QPointF(r.left()+min(43,r.width()*.42),r.top()+3))
            p.setPen(Qt.PenStyle.NoPen)
            p.fillRect(QRectF(r.right()-20,r.bottom()-3,14,2),RED)
            # NEXUS V3.1.8.2 PACKETS: autonomous multi-lane particles, reduced density.
            # Painted BEFORE telemetry to preserve label readability.
            if prefs['motion']:
                p.save()
                p.setClipPath(shape)
                lane_w=max(8.0,r.width()-32)
                now=time.monotonic()
                lane_profiles=(
                    # NEXUS V3.1.8.2: same autonomous motion model, ~50% less density.
                    (.31, 1, ((.03,.24,1.00,1.85),(.61,.30,.90,1.48))),
                    (.51,-1, ((.31,.26,.96,1.62),)),
                    (.72, 1, ((.18,.19,1.16,1.64),(.73,.29,.92,1.34))),
                )
                slot_bias=SLOTS.index(slot)*.137
                for lane_idx,(height_fraction,direction,packets) in enumerate(lane_profiles):
                    base_y=r.top()+r.height()*height_fraction
                    for packet_idx,(phase,speed,size_mul,radius) in enumerate(packets):
                        # Each particle has its own temporal offset, speed and tiny vertical drift
                        # so the stream feels organic rather than synchronized.
                        jitter=.018*math.sin(now*(1.35+packet_idx*.41)+phase*11.0+lane_idx*1.7+slot_bias*9.0)
                        progress=(now*speed+phase+slot_bias+jitter)%1.0
                        if direction<0:
                            progress=1.0-progress
                        xx=r.left()+14+lane_w*progress
                        bob=math.sin(now*(1.9+packet_idx*.37)+phase*13.0+lane_idx*2.2)*(.45+packet_idx*.10)
                        lane_y=base_y+bob
                        trail=(( -18*size_mul,22,3.0),(-11*size_mul,54,2.1),(-5*size_mul,118,1.6))
                        for distance,alpha,thickness in trail:
                            p.setPen(QPen(QColor(20,203,244,alpha if self._hover_slot!=slot else min(210,alpha+22)),thickness,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
                            p.drawLine(QPointF(xx+direction*distance,lane_y),QPointF(xx+direction*(distance+5*size_mul),lane_y))
                        p.setPen(Qt.PenStyle.NoPen)
                        core=QColor(90,239,255,205 if self._hover_slot==slot else 150)
                        p.setBrush(QColor(core.red(),core.green(),core.blue(),54))
                        p.drawEllipse(QPointF(xx,lane_y),radius+1.2,radius+1.2)
                        p.setBrush(core)
                        p.drawEllipse(QPointF(xx,lane_y),radius,radius)
                p.restore()
            main,secondary,pct,gval,gmax=get_fields(slot,self.readings or {})
            x=r.left()+10
            available=max(18,r.width()-20)
            # Clip every label to its own cell: never overlap neighboring plugins.
            p.save();p.setClipRect(r.adjusted(2,2,-2,-2))
            txt(p,LABELS[slot],x,r.top()+min(20,h*.21),max(10,min(13,h*.14)),PALE,True,max_width=available)
            if slot in ('cpu','fans') and r.width()>90:
                radius=min(h*.245,(r.width()-24)*.255)
                cx=r.left()+r.width()*.67;cy=r.top()+h*.49
                gauge(p,cx,cy,radius,gval,gmax,LABELS[slot],phase)
                gauge_left=max(18,cx-radius-x-4)
                if slot=='fans':
                    # N3XV5 V2.4.4: balanced plugin spacing + network arrow colors
                    secondary_y=r.top()+h*.49
                    txt(p,secondary,x,secondary_y,max(8,min(10,h*.11)),MUTED,False,
                        max_width=gauge_left)
                else:
                    txt(p,secondary,x,r.bottom()-11,max(8,min(10,h*.11)),MUTED,
                        max_width=gauge_left)
                    txt(p,main,x,r.top()+h*.52,max(11,min(17,h*.17)),BLUE,True,
                        max_width=gauge_left)
            else:
                # Linear plugins: move the secondary line away from the primary value
                # and keep it centered between the main line and the LED bar / footer.
                main_y=r.top()+min(38,h*.41)
                led_y=r.bottom()-13
                note_y=r.bottom()-5
                main_fs=max(11,min(19,h*.19))
                secondary_fs=max(8,min(11,h*.11))
                note_fs=max(6,min(8,h*.075))
                if slot=='network':
                    up_y=main_y + (note_y-main_y)*.48
                    txt(p,'↓',x,main_y,main_fs,RED,True)
                    txt(p,main,x+14,main_y,main_fs,BLUE,True,max_width=max(18,available-14))
                    txt(p,'↑',x,up_y,secondary_fs,QColor('#31dc78'),True)
                    txt(p,secondary,x+14,up_y,secondary_fs,MUTED,False,max_width=max(18,available-14))
                    note=SPEED_TEST.summary()
                    txt(p,note,x,note_y,note_fs,MUTED,max_width=available)
                    # Distinct click target: button does not interfere with NET Holo icon.
                    bx=r.right()-83; by=r.top()+28
                    if bx>x+28 and by+18<r.bottom()-19:
                        self._n3xvs_net_refresh_rect=QRect(round(bx),round(by),76,18)
                        shape=polygon(QRectF(self._n3xvs_net_refresh_rect),4)
                        p.fillPath(shape,QColor(8,51,78,228))
                        pen(p,QColor(38,204,255),.8);p.drawPath(shape)
                        txt(p,'↻ RAFRAÎCHIR',bx+5,by+12,8,PALE,True)
                else:
                    secondary_y=main_y + ((led_y if pct is not None else (r.bottom()-10)) - main_y)*.50
                    txt(p,main,x,main_y,main_fs,BLUE,True,max_width=available)
                    txt(p,secondary,x,secondary_y,secondary_fs,MUTED,False,max_width=available)
                    if pct is not None:
                        pass  # P5: single 20-segment rail painted below for every module
                    if slot=='storage':
                        # Show source-backed manufacturer throughput or nominal SATA
                        # ceiling. Never substitute a benchmark as manufacturer data.
                        data=self.readings or {}
                        read=_number(data,'storage_datasheet_read_mbs')
                        write=_number(data,'storage_datasheet_write_mbs')
                        if read is not None or write is not None:
                            note=f"SSD fiche: {_fmt(read,0)}↓/{_fmt(write,0)}↑ MB/s"
                        else:
                            note=STORAGE_BENCH.summary() if STORAGE_BENCH.result or STORAGE_BENCH.running else 'TEST 1 Gio DANS HOLO SSD'
                        txt(p,note,x,note_y,note_fs,MUTED,max_width=available)
            p.restore()
            # NEXUS V3: one segmented progress rail per visible module.
            # Measured percentages only; if the denominator is unknown, leave it dark.
            rail_pct=pct
            if rail_pct is None and slot=='fans' and gval is not None and gmax:
                rail_pct=100.0*float(gval)/float(gmax)
            elif rail_pct is None and slot=='network':
                _down=_number(self.readings or {},'net_down_mbs')
                _link=_number(self.readings or {},'net_link_mbps')
                if _down is not None and _link is not None and _link>0:
                    rail_pct=100.0*8.0*_down/_link
            elif rail_pct is None and slot=='power':
                rail_pct=_number(self.readings or {},'battery_percent')
            # Track is tucked inside each existing slot; leave the click / Holo geometry unchanged.
            # NEXUS P5.1: circular instruments and horizontal rails are mutually exclusive.
            if slot not in ('cpu', 'fans'):
                segments(p,x,r.bottom()-9,max(15,r.width()-25),max(3,min(6,h*.052)),rail_pct)
            # Small module icon in the same native geometric contract as Holo.
            icon_rect=module_icon_rect(self,slot)
            from healthbar.hud import icon as legacy_icon
            if icon_rect.width()>0:
                legacy_icon(p,slot,icon_rect.x(),icon_rect.y(),icon_rect.width())
        # NEXUS V3.1.6: débit and ping share the SAME font size and baseline.
        if 'network' in self.active_slots:
            _net_rect=QRectF(module_rect(self,'network')).adjusted(2,4,-2,-4)
            if _net_rect.width()>55:
                _down,_up,_,_,_=get_fields('network',self.readings or {})
                _ping=_NEXUS_V31_PING_MS
                _ping_text=f'PING {_ping:.0f}ms' if _ping is not None else 'PING —'
                # Cover the old one-sided value with the same opaque graphite backing.
                _value_rect=QRectF(_net_rect.left()+8,_net_rect.top()+min(23,h*.26),
                                   max(20,_net_rect.width()-16),max(15,min(24,h*.24)))
                p.save()
                p.fillRect(_value_rect,QColor(4,15,33,255))
                _gap=max(3,min(8,_value_rect.width()*.035))
                _left_w=max(12,(_value_rect.width()-_gap)*.52)
                _right_w=max(12,_value_rect.width()-_gap-_left_w)
                _left=QRectF(_value_rect.left(),_value_rect.top(),_left_w,_value_rect.height())
                _right=QRectF(_left.right()+_gap,_value_rect.top(),_right_w,_value_rect.height())
                _font=QFont('DejaVu Sans');_font.setBold(True)
                _sz=max(8,min(19,int(h*.19)))
                _font.setPixelSize(_sz);p.setFont(_font)
                while _sz>7 and (p.fontMetrics().horizontalAdvance(_down)>_left.width()-2 or
                                 p.fontMetrics().horizontalAdvance(_ping_text)>_right.width()-2):
                    _sz-=1;_font.setPixelSize(_sz);p.setFont(_font)
                p.setPen(BLUE)
                p.drawText(_left,Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft,
                           p.fontMetrics().elidedText(_down,Qt.TextElideMode.ElideRight,max(1,int(_left.width()-2))))
                p.drawText(_right,Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignRight,
                           p.fontMetrics().elidedText(_ping_text,Qt.TextElideMode.ElideRight,max(1,int(_right.width()-2))))
                p.restore()
        # Utility area is actually part of our same Qt canvas (not another UI).
        right=w*.845
        p.fillRect(QRectF(right,8,w-right-6,h-16),QColor(2,17,34,255))
        pen(p,QColor(20,151,244,180),1.2)
        p.drawLine(QPointF(right,8),QPointF(right,h-7))
        # NEXUS V3.1.8: center clock in the upper half of the utility plate.
        # Keep its geometry independent of the settings button below.
        clock_area=QRectF(right+7,h*.16,max(24,w-right-14),h*.33)
        _nexus_clock7(p,clock_area,time.strftime('%H:%M'))
        # A compact gear-chip with a fine cyan frame, not an oversized label.
        # V3.1.8.3: geometrically center the entire Settings chip inside the utility plate.
        util_left=right+7
        util_width=max(24,w-right-14)
        bw=min(108,max(68,util_width-18))
        bh=min(28,max(17,h*.23))
        bx=util_left+(util_width-bw)*.5
        by=h*.61+(h*.28-bh)*.5
        button_rect=QRectF(bx,by,bw,bh)
        button=polygon(button_rect,5)
        p.fillPath(button,QColor(8,35,59,215));pen(p,QColor(21,153,221,155),.8);p.drawPath(button)
        # Static button, label horizontally and vertically centered (no PHOTON animation).
        p.save()
        label_font=QFont('DejaVu Sans')
        label_font.setPixelSize(max(8,min(10,int(bh*.47))))
        label_font.setBold(True)
        p.setFont(label_font)
        p.setPen(PALE)
        p.drawText(button_rect,Qt.AlignmentFlag.AlignCenter,'⚙  RÉGLAGES')
        p.restore()
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
    dlg.resize(760, 550)
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
    # N3XV5 v2.3.9: settings navigation pages
    from PySide6.QtWidgets import QStackedWidget, QListWidget, QListWidgetItem, QSizePolicy
    pages = QStackedWidget(dlg)
    nav = QListWidget(dlg)
    nav.setObjectName('n3xvsSettingsNav')
    nav.setFixedWidth(170)
    nav.setSpacing(3)
    nav.setStyleSheet('''
      QListWidget#n3xvsSettingsNav {background:#06182b;border:1px solid #145785;
        color:#b9e6fb;padding:5px;outline:none;}
      QListWidget#n3xvsSettingsNav::item {padding:8px 7px;border:1px solid transparent;
        min-height:21px;border-radius:4px;}
      QListWidget#n3xvsSettingsNav::item:selected {background:#0f3d64;border-color:#23bfff;
        color:#e7fbff;font-weight:bold;}
      QListWidget#n3xvsSettingsNav::item:hover {background:#102e4b;}
    ''')
    main_area = QHBoxLayout()
    main_area.setSpacing(9)
    main_area.addWidget(nav)
    main_area.addWidget(pages, 1)
    root.addLayout(main_area, 1)
    page_layouts={}
    page_titles={
      'general':'GÉNÉRALE', 'performance':'PERFORMANCES', 'display':'AFFICHAGE',
      'cpu':'CPU', 'gpu':'GPU', 'ram':'RAM', 'storage':'SSD / HDD',
      'fans':'FANS', 'network':'NETWORK', 'power':'POWER'
    }
    for key,title in page_titles.items():
        pane=QScrollArea(dlg)
        pane.setWidgetResizable(True)
        pane.setFrameShape(QFrame.Shape.NoFrame)
        pane.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contents=QWidget()
        contents.setObjectName('n3xvsPage_'+key)
        layout=QVBoxLayout(contents)
        layout.setContentsMargins(8,8,12,8)
        layout.setSpacing(13)
        heading=QLabel(title+'  /  N3XV5')
        heading.setStyleSheet('color:#45dfff;font-size:15px;font-weight:bold;padding:5px 0 7px;')
        layout.addWidget(heading)
        layout.addStretch(1)
        pane.setWidget(contents)
        page_layouts[key]=layout
        pages.addWidget(pane)
        nav.addItem(title)
    nav.currentRowChanged.connect(pages.setCurrentIndex)
    nav.setCurrentRow(0)
    def add_settings_group(page,group):
        layout=page_layouts[page]
        layout.insertWidget(layout.count()-1,group)
    def add_settings_note(page,message):
        label=QLabel(message)
        label.setWordWrap(True)
        label.setStyleSheet('color:#91bfd7;padding:7px;')
        layout=page_layouts[page]
        layout.insertWidget(layout.count()-1,label)
    add_settings_note('general','Comportement et éclairage.')
    add_settings_note('performance','Turbo CPU et fréquence de rafraîchissement des capteurs.')
    add_settings_note('display','TopBar, Navbar Bottom et visibilité des modules.')
    behavior=QGroupBox('COMPORTEMENT')
    bg=QGridLayout(behavior)
    always=QCheckBox('Toujours afficher la barre (désactive la rétraction automatique)')
    always.setChecked(prefs['always_visible']);bg.addWidget(always,0,0,1,2)
    delay=QSpinBox();delay.setRange(1,30);delay.setSuffix(' s');delay.setValue(prefs['hide_delay_s'])
    bg.addWidget(QLabel('Délai de rétraction après départ'),1,0);bg.addWidget(delay,1,1)
    bg.addWidget(QLabel('Survol du haut de l’écran pour ouvrir : 2 secondes'),2,0,1,2)
    add_settings_group('general',behavior)
    group=QGroupBox('AFFICHAGE TOPBAR')
    grid=QGridLayout(group)
    height=QSpinBox();height.setRange(60,150);height.setSuffix(' px');height.setValue(prefs['height'])
    grid.addWidget(QLabel('Hauteur déployée'),0,0);grid.addWidget(height,0,1)
    add_settings_group('display',group)
    boxes={}
    for slot in SLOTS:
        plugin_group=QGroupBox('PLUGIN '+LABELS[slot].upper())
        plugin_layout=QVBoxLayout(plugin_group)
        cb=QCheckBox('Activer '+LABELS[slot]+' dans la TopBar')
        cb.setChecked(slot not in prefs['hidden_modules'])
        plugin_layout.addWidget(cb)
        boxes[slot]=cb
        add_settings_group(slot,plugin_group)
    add_settings_note('cpu','Turbo et performances globales : voir la page PERFORMANCES.')
    add_settings_note('gpu','Les mesures restent dépendantes des pilotes et des capteurs du système.')
    add_settings_note('ram','Les données de mémoire et barrettes sont disponibles dans le Holo RAM.')
    add_settings_note('storage','Benchmarks de lecture/écriture et BleachBit : depuis le Holo SSD/HDD.')
    add_settings_note('network','Test Speedtest et débit instantané : depuis le Holo Network.')
    # N3XV5 v2.3.10: provider selection
    from PySide6.QtWidgets import QComboBox
    from n3xvs_network_archive import config as _n3xvs_network_config
    network_cfg=_n3xvs_network_config()
    provider_group=QGroupBox('SOURCE DES TESTS INTERNET')
    provider_layout=QVBoxLayout(provider_group)
    provider_layout.addWidget(QLabel('Fournisseur principal (conservé entre redémarrages)'))
    provider_choice=QComboBox(provider_group)
    provider_choice.addItem('Speedtest (Ookla CLI)', 'speedtest')
    provider_choice.addItem('nPerf (si connecteur compatible ; secours Speedtest)', 'nperf')
    provider_choice.setCurrentIndex(1 if network_cfg.get('preferred_provider')=='nperf' else 0)
    provider_layout.addWidget(provider_choice)
    provider_layout.addWidget(QLabel('Les mesures nPerf et Speedtest sont archivées séparément.\n'
        'Le même ServerID est réutilisé ; aucun changement automatique de serveur.'))
    add_settings_group('network', provider_group)

    add_settings_note('power','Les sondes matérielles indisponibles ne sont pas simulées.')
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
    add_settings_group('general',effects)
    navigation=QGroupBox('NAVBAR BOTTOM — TASKBAR NATIVE')
    ng=QGridLayout(navigation)
    bottom_enabled=QCheckBox('Afficher la barre de navigation inférieure')
    bottom_enabled.setChecked(prefs['bottom_enabled'])
    bottom_height=QSpinBox(); bottom_height.setRange(44,100); bottom_height.setSuffix(' px')
    bottom_height.setValue(prefs['bottom_height'])
    bottom_opacity=QSpinBox();bottom_opacity.setRange(15,85);bottom_opacity.setSuffix(' %')
    bottom_opacity.setValue(prefs['bottom_opacity'])
    ng.addWidget(bottom_enabled,0,0,1,2)
    ng.addWidget(QLabel('Hauteur Navbar'),1,0);ng.addWidget(bottom_height,1,1)
    ng.addWidget(QLabel('Opacité Navbar'),2,0);ng.addWidget(bottom_opacity,2,1)
    # N3XV5 V2.4.5 navbar belongs to AFFICHAGE
    add_settings_group('display',navigation)
    fans_group=QGroupBox('VENTILATEURS — VITESSE MAXIMALE DE RÉFÉRENCE')
    fg=QGridLayout(fans_group)
    fan_inputs={}
    detected={}
    for fan in (bar.canvas.readings or {}).get('fans') or []:
        if isinstance(fan,dict):
            label=str(fan.get('name') or '').strip()[:80]
            if label:detected[label.lower()]=label
    for key in (prefs.get('fan_max_rpm') or {}):
        detected.setdefault(key,key)
    if not detected:
        fg.addWidget(QLabel('Aucun ventilateur détecté actuellement. Ouvrir de nouveau après télémétrie.'),0,0,1,2)
    for row,(key,label) in enumerate(sorted(detected.items())):
        control=QSpinBox()
        control.setRange(0,30000)
        control.setSpecialValueText('Auto / inconnu')
        control.setSuffix(' RPM')
        control.setValue((prefs.get('fan_max_rpm') or {}).get(key,0))
        control.setToolTip('0 : utiliser le maximum matériel si disponible. Valeur manuelle : référence pour le pourcentage, pas contrôle de vitesse.')
        fg.addWidget(QLabel(label),row,0)
        fg.addWidget(control,row,1)
        fan_inputs[key]=control
    hint=QLabel('0 = automatique. Une valeur manuelle définit seulement 100 % sur la jauge ; elle ne pilote pas le ventilateur. Max affiché : 100 / 100 %.')
    hint.setWordWrap(True)
    fg.addWidget(hint,len(detected)+1,0,1,2)
    add_settings_group('fans',fans_group)
    perf_group=QGroupBox('PERFORMANCES / RAFRAÎCHISSEMENT')
    pg=QGridLayout(perf_group)
    telemetry_s=QSpinBox();telemetry_s.setRange(1,15);telemetry_s.setSuffix(' s')
    telemetry_s.setValue(prefs['telemetry_refresh_s'])
    visual_fps=QSpinBox();visual_fps.setRange(5,30);visual_fps.setSuffix(' FPS')
    visual_fps.setValue(prefs['visual_fps'])
    hourly=QCheckBox('Speedtest automatique toutes les heures (optionnel, consomme des données)')
    hourly.setChecked(prefs['net_speedtest_hourly'])
    test_now=QPushButton('↻  RAFRAÎCHIR — TEST INTERNET (Speedtest, pas nPerf)')
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
    add_settings_group('performance',perf_group)
    turbo_group=QGroupBox('CPU — TURBO BOOST (AUTORISATION SYSTÈME)')
    tg=QGridLayout(turbo_group)
    turbo_status=QLabel('État : lecture du commutateur noyau…')
    turbo_toggle=QPushButton('CHANGER TURBO ON / OFF')
    tg.addWidget(turbo_status,0,0,1,2)
    tg.addWidget(turbo_toggle,1,0,1,2)
    add_settings_group('performance',turbo_group)

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
    info.setWordWrap(True);info.setStyleSheet('color:#82bedc;');add_settings_note('general',info.text())
    buttons=QHBoxLayout();cancel=QPushButton('ANNULER');apply=QPushButton('APPLIQUER')
    buttons.addStretch();buttons.addWidget(cancel);buttons.addWidget(apply);root.addLayout(buttons)
    cancel.clicked.connect(dlg.reject)
    def commit():
        prefs.update(height=height.value(),always_visible=always.isChecked(),hide_delay_s=delay.value(),
                     glow=glow.value(),opacity=opacity.value(),contrast=contrast.value(),motion=motion.isChecked(),holo_enabled=holo.isChecked(),
                     hidden_modules=[s for s,cb in boxes.items() if not cb.isChecked()],
                     bottom_enabled=bottom_enabled.isChecked(),bottom_height=bottom_height.value(),
                     bottom_opacity=bottom_opacity.value(),telemetry_refresh_s=telemetry_s.value(),
                     visual_fps=visual_fps.value(),net_speedtest_hourly=hourly.isChecked(),
                     fan_max_rpm={key:control.value() for key,control in fan_inputs.items() if control.value() >= 100})
        from n3xvs_network_archive import CONFIG as _net_config_file, _atomic_json as _save_network_config
        network_cfg['preferred_provider']=provider_choice.currentData()
        _save_network_config(_net_config_file,network_cfg)
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
        x, y, w, h=_settings_window_rect(bounds, preferred=(850, 610))
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
        bottom_dock_height=max(62,prefs['bottom_height']),bottom_nav_opacity=prefs['bottom_opacity'],
        xfce_skin_enabled=False,auto_hide=not prefs['always_visible'],
        retract_mode='manual' if prefs['always_visible'] else 'auto',
        top_reserved=True,top_hover_ms=2000,top_trigger_px=10,hide_seconds=max(3,prefs['hide_delay_s']),
        always_on_top=True,length_percent=100,opacity=prefs['opacity'],
        hidden_modules=prefs['hidden_modules'],holo_enabled=prefs['holo_enabled'],autostart=False)
    settings.slot_order=SLOTS.copy()
    settings.validate()
    settings.bottom_dock_height=prefs['bottom_height']  # after legacy 62px schema validation
    configroot.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(configroot/'n3xvs-top-native.lock'))
    if not lock.tryLock(100):
        raise SystemExit('Une instance N3XV5 native est déjà active.')
    bar=Bar(settings)
    # N3XV5 V2.4.0 - install SSD/HDD BleachBit controller
    from App.Modules.Top.HUD_Plugins_ViewBar.NativeQt.n3xvs_bleachbit_holo import attach_storage_cleaner
    attach_storage_cleaner(bar)
    # Live POWER sensor cache: reads only accessible sysfs telemetry, never
    # estimates PSU wall power from TDP or CPU percent.
    from n3xvs_metrics import POWER_PROBE
    power_timer=QTimer(bar)
    power_timer.setInterval(2000)
    power_timer.timeout.connect(POWER_PROBE.poll)
    POWER_PROBE.poll()
    power_timer.start()
    # V2.3.4 — Holo telemetry has independent refresh cycles. Enrich every
    # actual Holo update instead of only the first time the panel is opened.
    # Never generate artificial electrical readings or change Turbo policy.
    from healthbar.cpu_backends import system_backend as _boost_backend_factory
    def _actual_turbo_state(data):
        state = data.get('cpu_turbo_enabled')
        if type(state) is bool:
            return state
        try:
            state = _boost_backend_factory().read()
            return state if type(state) is bool else None
        except (OSError, ValueError, PermissionError):
            return None

    cpu_panel = bar.holo
    _cpu_original_set_telemetry = cpu_panel.set_telemetry
    def _cpu_set_telemetry_with_turbo(data):
        readings = dict(data or {})
        readings.update(POWER_PROBE.snapshot())
        readings['cpu_turbo_enabled'] = _actual_turbo_state(readings)
        _cpu_original_set_telemetry(readings)
        # Add the line AFTER Package / Total in the 4-column CPU table.
        core_count = len((readings.get('cpu_cores') or [])[:128])
        row = core_count + 2
        state = readings['cpu_turbo_enabled']
        label = 'ACTIVÉ' if state is True else 'DÉSACTIVÉ' if state is False else 'INDISPONIBLE'
        for column, value in enumerate(('MODE TURBO', label, '', '')):
            cpu_panel._add_cell(value, row, column, column == 0)
        cpu_panel.grid.setVerticalSpacing(7)
        cpu_panel.grid_widget.adjustSize()
    cpu_panel.set_telemetry = _cpu_set_telemetry_with_turbo
    _cpu_set_telemetry_with_turbo(bar.canvas.readings or {})

    power_panel = bar.module_holos.get('power')
    if power_panel is not None:
        _power_original_set_telemetry = power_panel.set_telemetry
        def _power_set_telemetry_with_diagnostics(data):
            readings = dict(data or {})
            readings.update(POWER_PROBE.snapshot())
            _power_original_set_telemetry(readings)
            # Battery voltage/capacity remain informative even without wattage.
            battery_voltage = _number(readings, 'battery_voltage_v')
            battery_capacity = _number(readings, 'battery_capacity_percent')
            if battery_voltage is not None or battery_capacity is not None:
                row = power_panel.grid.rowCount()
                for label, value in (
                    ('BATTERIE · TENSION', f'{battery_voltage:.3f} V' if battery_voltage is not None else '—'),
                    ('BATTERIE · CHARGE', f'{max(0,min(100,battery_capacity)):.0f} / 100 %' if battery_capacity is not None else '—'),
                    ('ALIMENTATION SECTEUR', 'BRANCHÉE' if readings.get('power_ac_online') is True else 'DÉBRANCHÉE' if readings.get('power_ac_online') is False else 'INCONNUE'),
                    ('BATTERIE · ÉTAT', str(readings.get('battery_status') or '—'))):
                    power_panel._add_cell(label, row, 0, True)
                    power_panel._add_cell(value, row, 1)
                    row += 1
            # Distinguish unavailable sensors from a genuine reading of 0 W.
            cpu_w = _number(readings, 'cpu_power_w')
            gpu_w = _number(readings, 'gpu_power_w')
            battery_w = _number(readings, 'battery_discharge_w')
            wall_w = _number(readings, 'power_total_w')
            if any(v is not None for v in (cpu_w, gpu_w, battery_w, wall_w)):
                source = readings.get('power_source') or readings.get('gpu_power_source') or 'capteur local'
                power_panel.cpu_name.setText('SONDES PHYSIQUES · ' + str(source)[:90])
                power_panel.note.setText('W mesurés par les pilotes accessibles · CPU/GPU et prise secteur sont des mesures distinctes.')
            else:
                power_panel.cpu_name.setText('SONDES POWER NON EXPOSÉES PAR LE NOYAU')
                power_panel.note.setText('Aucun compteur W accessible (RAPL / hwmon / nvidia-smi / batterie).\n'
                    'Température, charge et fréquence ne permettent pas de calculer la consommation réelle. '
                    'Utiliser un wattmètre USB/secteur compatible pour mesurer le PC complet.')
                # Other real sensor data is still useful in POWER, but is not watts.
                row = power_panel.grid.rowCount()
                temp = _number(readings, 'cpu_temperature_c')
                freq = _number(readings, 'cpu_frequency_ghz')
                for key, val in (('Température CPU (sonde)', f'{temp:.0f} °C' if temp is not None else '—'),
                                 ('Fréquence CPU (sonde)', f'{freq:.2f} GHz' if freq is not None else '—')):
                    power_panel._add_cell(key, row, 0, True)
                    power_panel._add_cell(val, row, 1)
                    row += 1
            power_panel.grid.setVerticalSpacing(7)
        power_panel.set_telemetry = _power_set_telemetry_with_diagnostics
        _power_set_telemetry_with_diagnostics(bar.canvas.readings or {})

    # Fan percentages must never exceed 100%, but measured RPM remain raw.
    # With unknown max RPM, show no fabricated percentage.
    fan_panel = bar.module_holos.get('fans')
    if fan_panel is not None:
        _fan_original_set_telemetry = fan_panel.set_telemetry
        def _fan_set_telemetry_clamped(data):
            safe = dict(data or {})
            fans=[]
            for item in safe.get('fans') or []:
                if not isinstance(item,dict):
                    continue
                fan=dict(item)
                maximum,source=_fan_reference(fan,prefs)
                rpm=_number(fan,'rpm')
                fan['max_rpm']=maximum
                fan['percent_max']=_fan_percent(rpm,maximum)
                fan['reference_source']=source
                fans.append(fan)
            safe['fans']=fans
            _fan_original_set_telemetry(safe)
            for fan in fans:
                if fan.get('reference_source') == 'référence utilisateur':
                    fan_panel.cpu_name.setText('MAX RPM : référence utilisateur (jauge uniquement)')
        fan_panel.set_telemetry=_fan_set_telemetry_clamped
        _fan_set_telemetry_clamped(bar.canvas.readings or {})

    # Improve readability in the FAN/SSD/CPU detail tables: compact but not
    # overlapping with their headers, notes, or scroll viewport.
    for _slot in ('fans', 'storage', 'cpu', 'power'):
        _panel = bar.holo if _slot == 'cpu' else bar.module_holos.get(_slot)
        if _panel is not None:
            _panel.grid.setVerticalSpacing(7)
            _panel.grid.setHorizontalSpacing(11)
            _panel.note.setMinimumHeight(22)
            _panel.note.setWordWrap(True)

    # NET Holo — visible actions inside the real popup, not tiny HUD-only ink.
    net_panel=bar.module_holos.get('network')
    if net_panel is not None:
        from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton
        from PySide6.QtGui import QDesktopServices,QPainter,QPen,QColor
        from PySide6.QtCore import QUrl,QPoint,QRectF,QTimer,Qt

        class NetTestIndicator(QWidget):
            """Painted status directly below Holo's pin control; no emoji fonts needed."""
            def __init__(self, panel):
                super().__init__(panel)
                self.setFixedSize(26, 26)
                self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                self.setToolTip('NET : aucun test effectué')
                self._frame = 0
                self._state = 'idle'
                self._ticker = QTimer(self)
                self._ticker.setInterval(90)
                self._ticker.timeout.connect(self._tick)
                self.hide()

            def _tick(self):
                self._frame = (self._frame + 1) % 12
                self.update()

            def set_status(self, state, detail):
                if state != self._state:
                    self._state = state
                    if state == 'running':
                        self._ticker.start()
                    else:
                        self._ticker.stop()
                    self.update()
                self.setToolTip(detail)
                self.setVisible(state != 'idle')

            def reposition(self):
                # Pin is on the first row; reserve the narrow empty slot beneath.
                pin = net_panel.pin_button
                top_left = pin.mapTo(net_panel, QPoint(0, pin.height() + 3))
                self.move(top_left.x() + (pin.width() - self.width()) // 2,
                          top_left.y())
                self.raise_()

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                if self._state == 'running':
                    painter.setPen(QPen(QColor('#1d5070'), 2.2))
                    painter.drawEllipse(QRectF(3, 3, 20, 20))
                    painter.setPen(QPen(QColor('#28dfff'), 2.7, Qt.PenStyle.SolidLine,
                                        Qt.PenCapStyle.RoundCap))
                    painter.drawArc(QRectF(3, 3, 20, 20),
                                    (90 - self._frame * 30) * 16, -110 * 16)
                elif self._state == 'success':
                    painter.setPen(QPen(QColor('#48eb85'), 2.7,
                                        Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                        Qt.PenJoinStyle.RoundJoin))
                    painter.drawLine(QPoint(5, 13), QPoint(11, 19))
                    painter.drawLine(QPoint(11, 19), QPoint(22, 7))
                elif self._state == 'error':
                    painter.setPen(QPen(QColor('#ff4a67'), 2.7,
                                        Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    painter.drawLine(QPoint(7, 7), QPoint(19, 19))
                    painter.drawLine(QPoint(19, 7), QPoint(7, 19))
                painter.end()

        net_indicator = NetTestIndicator(net_panel)
        # The widget follows the pin even after Holo window bounds change.
        tools=QWidget(net_panel)
        line=QHBoxLayout(tools);line.setContentsMargins(4,2,4,2);line.setSpacing(6)
        test_button=QPushButton('↻ Rafraîchir · Speedtest',tools)
        test_button.setFixedHeight(27)
        test_button.setToolTip('Test officiel Ookla si installé (sinon speedtest-cli). Consomme des données.')
        nperf_button=QPushButton('Ouvrir nPerf',tools)
        nperf_button.setFixedHeight(27)
        nperf_button.setToolTip('Ouvre le site officiel nPerf pour un test manuel ; aucun résultat nPerf n’est inventé.')
        test_button.setMinimumWidth(0);nperf_button.setMinimumWidth(0)
        test_button.setStyleSheet('font-size:11px;padding:2px 5px;')
        nperf_button.setStyleSheet('font-size:11px;padding:2px 5px;')
        line.addWidget(test_button,3);line.addWidget(nperf_button,2)
        status=QLabel('Internet : aucun test effectué',net_panel)
        status.setWordWrap(True)
        status.setStyleSheet('color:#8fdef9;padding:2px 5px;font-size:11px;')
        net_panel.layout().insertWidget(6,tools)
        net_panel.layout().insertWidget(7,status)
        net_panel.resize(min(500,max(450,net_panel.width())),max(440,net_panel.height()))
        def on_net_test_clicked():
            if SPEED_TEST.start():
                status.setText('Test Internet en cours… mesure des débits réels, merci de patienter.')
            else:
                status.setText('Test déjà en cours. Vérifie son état ci-dessous.')
            update_test_label()
        test_button.clicked.connect(on_net_test_clicked)
        nperf_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('https://www.nperf.com/fr/')))
        net_status_timer=QTimer(net_panel)
        net_status_timer.setInterval(1300)
        def update_test_label():
            test_button.setEnabled(not SPEED_TEST.running)
            result=SPEED_TEST.result
            error=SPEED_TEST.error
            # Error has priority over cached results; a previous successful
            # test must not turn a new failed attempt into a green checkmark.
            if SPEED_TEST.running:
                state,detail = 'running','Test de débit en cours…'
            elif error and error not in ('Test non effectué', 'Test en cours'):
                state,detail = 'error','Échec du dernier test : ' + str(error)
            elif result:
                state,detail = 'success','Dernier test réussi : réception et envoi mesurés'
            else:
                state,detail = 'idle','Aucun test de débit effectué'
            net_indicator.set_status(state,detail)
            net_indicator.reposition()
            if result and not SPEED_TEST.running:
                from datetime import datetime
                at=datetime.fromtimestamp(result['measured_at']).strftime('%H:%M')
                source='Ookla' if result['source']=='ookla' else 'speedtest-cli'
                status.setText(f"Speedtest {source} • {at} • ↓ {result['download_mbps']:.2f} / ↑ {result['upload_mbps']:.2f} Mbit/s (Mb/s, pas Mo/s)" + (' • Valeur faible : vérifier serveur, Wi-Fi et outil de mesure' if min(result['download_mbps'],result['upload_mbps']) < 1 else '') + (f" • Dernier échec : {SPEED_TEST.error}" if SPEED_TEST.error else ''))
            elif SPEED_TEST.running: status.setText('Mesure en cours…')
            else:status.setText('Test Internet : '+str(SPEED_TEST.error or 'non effectué')+'\nDébit instantané = trafic local, pas résultat du test.')
        net_status_timer.timeout.connect(update_test_label)
        update_test_label()
        net_status_timer.start()
        # Animation independent of network polling; 90 ms only during test.
    # STORAGE Holo — explicit opt-in 1 GiB file benchmark; never block the Qt UI.
    storage_panel=bar.module_holos.get('storage')
    if storage_panel is not None:
        from PySide6.QtWidgets import QWidget,QHBoxLayout,QLabel,QPushButton
        from n3xvs_storage_bench import STORAGE_BENCH
        storage_tools=QWidget(storage_panel)
        storage_line=QHBoxLayout(storage_tools)
        storage_line.setContentsMargins(5,3,5,3)
        storage_button=QPushButton('↻ Tester 1 Gio · lecture/écriture',storage_tools)
        storage_button.setToolTip('Test sur le volume du dossier personnel : 1 Gio en écriture + lecture.\nLancé au démarrage si nécessaire, puis au maximum une fois par heure.')
        storage_line.addWidget(storage_button)
        storage_label=QLabel(storage_panel)
        storage_label.setWordWrap(True)
        storage_label.setStyleSheet('color:#8fdef9;padding:3px 8px;')
        storage_panel.layout().insertWidget(6,storage_tools)
        storage_panel.layout().insertWidget(7,storage_label)
        storage_panel.resize(max(510,storage_panel.width()),max(380,storage_panel.height()))
        def on_storage_test_clicked():
            if STORAGE_BENCH.start(automatic=False):
                storage_label.setText('Benchmark 1 Gio démarré : écriture puis lecture…')
            elif STORAGE_BENCH.running:
                storage_label.setText('Test SSD déjà en cours : '+STORAGE_BENCH.progress)
            else:
                remain=STORAGE_BENCH.seconds_remaining()
                storage_label.setText(('Limite de sécurité : encore '+str((remain+59)//60)+' minute(s) avant un nouveau test.' if remain else
                                       'Test refusé : '+str(STORAGE_BENCH.error or STORAGE_BENCH.progress)))
            if STORAGE_BENCH.running:
                update_storage_bench_status()
        storage_button.clicked.connect(on_storage_test_clicked)
        storage_status_timer=QTimer(storage_panel)
        storage_status_timer.setInterval(1200)
        def update_storage_bench_status():
            storage_button.setEnabled(not STORAGE_BENCH.running)
            storage_button.setText('↻ Tester 1 Gio · lecture/écriture' if STORAGE_BENCH.seconds_remaining() == 0 else '↻ Test SSD (délai : '+str((STORAGE_BENCH.seconds_remaining()+59)//60)+' min)')
            data=bar.canvas.readings or {}
            manufacturer=any(_number(data,k) is not None for k in ('storage_datasheet_read_mbs','storage_datasheet_write_mbs'))
            if manufacturer:
                storage_label.setText('Données constructeur disponibles. Le test est facultatif et ne les remplace pas.')
            elif STORAGE_BENCH.error:
                storage_label.setText('Test échoué : '+STORAGE_BENCH.error+'\n'+STORAGE_BENCH.summary())
            else:
                storage_label.setText(STORAGE_BENCH.summary()+'\nSource : benchmark local 1 Gio sur le dossier personnel · non constructeur · lecture possiblement influencée par le cache Linux.')
            bar.canvas.update()
        storage_status_timer.timeout.connect(update_storage_bench_status)
        update_storage_bench_status()
        storage_status_timer.start()
    # V2.3 — One benchmark at startup (after sensors warm up), then hourly.
    # If full manufacturer throughput is known, no benchmark is needed.
    # Timer and button share the same persistent throttle across sessions.
    from n3xvs_storage_bench import STORAGE_BENCH as _STORAGE_BENCH
    def n3xvs_hourly_disk_check():
        readings = bar.canvas.readings or {}
        # Never benchmark when the manufacturer's read/write values are both known.
        known = all(_number(readings, key) is not None for key in (
            'storage_datasheet_read_mbs', 'storage_datasheet_write_mbs'))
        if not known:
            _STORAGE_BENCH.start(automatic=True)
    disk_test_timer = QTimer(bar)
    disk_test_timer.setInterval(60000)
    disk_test_timer.timeout.connect(n3xvs_hourly_disk_check)
    disk_test_timer.start()
    # Delay initial check to let the async telemetry worker populate readings.
    QTimer.singleShot(12000, n3xvs_hourly_disk_check)

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
    # XFWM/X11 can retain an obsolete top strut after a geometry animation.
    # Inspect only this application's own window; never touch other processes.
    # Re-apply only when the actual EWMH property differs from our Qt state.
    def n3xvs_strut_guard():
        if not bar.isVisible():
            return
        try:
            from Xlib import display
            con=display.Display()
            try:
                win=con.create_resource_object('window',int(bar.winId()))
                atom=con.intern_atom('_NET_WM_STRUT_PARTIAL')
                prop=win.get_full_property(atom,0)
                actual=tuple(int(v) for v in prop.value[:4]) if prop is not None else (0,0,0,0)
            finally:
                con.close()
            wanted=0 if bar.retracted or not settings.top_reserved or not settings.hud_enabled else int(bar.geometry().height())
            # 4-strut tuple: left, right, top, bottom.
            if actual[2]!=wanted or any(actual[i] for i in (0,1,3)):
                n3xvs_reserve_top_workarea()
        except (ImportError,RuntimeError,OSError,ValueError):
            pass
    strut_guard_timer=QTimer(bar)
    strut_guard_timer.setInterval(2000)
    strut_guard_timer.timeout.connect(n3xvs_strut_guard)
    strut_guard_timer.start()
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
        settings.bottom_dock_height=max(62,prefs['bottom_height'])
        settings.bottom_nav_opacity=prefs['bottom_opacity']
        settings.hidden_modules=prefs['hidden_modules'][:]
        settings.holo_enabled=prefs['holo_enabled']
        settings.hide_seconds=max(3,prefs['hide_delay_s'])
        settings.top_hover_ms=2000
        settings.retract_mode='manual' if prefs['always_visible'] else 'auto'
        settings.auto_hide=not prefs['always_visible']
        settings.validate()
        settings.bottom_dock_height=prefs['bottom_height']
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
        if fan_panel is not None:
            fan_panel.set_telemetry(bar.canvas.readings or {})
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
    # Qt timers are connected to the legacy bound retract method, therefore
    # synchronise via the state watchdog instead of monkey-patching retract().
    def finish():
        old_finish();bar.actions.hide();bar.root.setSpacing(0)
    bar._finish_transition=finish
    old_reveal=bar.reveal
    def reveal():
        old_reveal();bar.actions.hide();bar.root.setSpacing(0)
    bar.reveal=reveal
    # V2.3.7 — a single native Holo for all slots, pinned or not.
    # Coordinate from the REAL TopBar window geometry during animation, not
    # screen.availableGeometry() (which may lag behind XFWM/EWMH strut updates).
    from PySide6.QtCore import QRect, QPoint
    _holo_panels = {'cpu': bar.holo, **bar.module_holos}
    _holo_state = {'slot': None, 'last_geometry': None}
    _holo_position_timer = QTimer(bar)
    _holo_position_timer.setInterval(60)

    def _current_holo():
        slot = _holo_state['slot']
        return _holo_panels.get(slot) if slot else None

    def _holo_close_others(active):
        for other in dict.fromkeys(_holo_panels.values()):
            if other is not active and other.isVisible():
                other.close_panel()  # also releases pinned Holos

    def _holo_place():
        panel = _current_holo()
        if panel is None or not panel.isVisible():
            _holo_position_timer.stop()
            _holo_state['slot'] = None
            _holo_state['last_geometry'] = None
            return
        screen = QApplication.screenAt(bar.geometry().center()) or QApplication.primaryScreen()
        if screen is None:
            return
        physical = screen.geometry()
        top = max(physical.top() + 2, bar.geometry().bottom() + 3)
        bottom = physical.bottom() - 5
        dock = getattr(bar, 'bottom_dock', None)
        if dock is not None and dock.isVisible() and not getattr(dock, 'collapsed', False):
            bottom = min(bottom, dock.geometry().top() - 6)
        if bottom - top < 180:
            return  # avoid invalid geometry during temporary screen changes

        # Reserve no arbitrary 70/100px: follow the real TopBar edge. Limit
        # Holo size to remaining space, maintaining the QWidget minimum height.
        minimum_height = panel.minimumHeight()
        wanted_h = min(panel.height(), max(minimum_height, bottom - top + 1))
        if wanted_h > bottom - top + 1:
            wanted_h = bottom - top + 1
        wanted_w = min(panel.width(), max(240, physical.width() - 12))
        if panel.height() != wanted_h or panel.width() != wanted_w:
            panel.resize(wanted_w, wanted_h)

        slot = _holo_state['slot']
        if not bar.retracted:
            try:
                anchor = bar.canvas.module_global_rect(slot)
                anchor_x = anchor.center().x()
            except (AttributeError, ValueError):
                anchor_x = bar.geometry().center().x()
        else:
            # On retract the canvas is only 28px tall: retain the horizontal
            # location of the selected module from the full-width layout.
            order = list(getattr(bar.canvas, 'slot_order', []) or [])
            count = max(1, len(order))
            index = order.index(slot) if slot in order else count // 2
            full = bar.full_rect
            anchor_x = full.left() + int(full.width() * (index + 0.5) / count)
        x = max(physical.left() + 4, min(int(anchor_x - wanted_w / 2), physical.right() - wanted_w - 3))
        y = top
        wanted = (x, y, wanted_w, wanted_h)
        if _holo_state['last_geometry'] != wanted:
            panel.setGeometry(QRect(*wanted))
            _holo_state['last_geometry'] = wanted

    _holo_position_timer.timeout.connect(_holo_place)
    for _panel in dict.fromkeys(_holo_panels.values()):
        # The historical panel emits this signal on its own close button.
        _panel.closed.connect(lambda: QTimer.singleShot(0, _holo_place))

    def open_holo(slot):
        if not prefs['holo_enabled']:
            return
        panel = _holo_panels.get(slot)
        if panel is None:
            return
        active = _current_holo()
        if active is panel and panel.isVisible():
            panel.close_panel()
            _holo_state['slot'] = None
            _holo_position_timer.stop()
            return
        _holo_close_others(panel)
        _holo_state['slot'] = slot
        _holo_state['last_geometry'] = None
        screen = QApplication.screenAt(bar.geometry().center()) or QApplication.primaryScreen()
        if screen is None:
            return
        panel.set_telemetry({**(bar.canvas.readings or {}), **POWER_PROBE.snapshot()})
        panel.show_at(bar.canvas.module_global_rect(slot),screen.geometry(),'top')
        _holo_place()
        _holo_position_timer.start()

    bar.canvas.module_activated.disconnect()
    bar.canvas.module_activated.connect(open_holo)
    def show_settings():
        bar.busy=True;bar.hide_timer.stop()
        try:
            dlg=_make_settings_dialog(bar,prefs,prefpath,apply_prefs)
            dlg.exec()
        finally:
            bar.busy=False;bar.arm_hide()
    # Ping (5s): external probe runs asynchronously, never blocks Qt UI.
    from PySide6.QtCore import QProcess as _NexusPingProcess, QTimer as _NexusPingTimer
    import re as _nexus_ping_regex
    _nexus_ping_proc=_NexusPingProcess(bar)
    _nexus_ping_timer=_NexusPingTimer(bar)
    _nexus_ping_timer.setInterval(5000)
    def _nexus_ping_finished(code,status):
        text=bytes(_nexus_ping_proc.readAllStandardOutput()).decode('utf-8','replace')
        match=_nexus_ping_regex.search(r'time[=<]\s*([0-9]+(?:\.[0-9]+)?)',text)
        globals()['_NEXUS_V31_PING_MS']=float(match.group(1)) if match else None
        bar.canvas.update()
    def _nexus_ping_poll():
        if 'network' not in bar.canvas.active_slots:
            globals()['_NEXUS_V31_PING_MS']=None
            return
        if _nexus_ping_proc.state()!=_NexusPingProcess.ProcessState.NotRunning:return
        _nexus_ping_proc.start('ping',['-n','-c','1','-W','1','1.1.1.1'])
    _nexus_ping_proc.finished.connect(_nexus_ping_finished)
    _nexus_ping_timer.timeout.connect(_nexus_ping_poll)
    _nexus_ping_timer.start()
    _NexusPingTimer.singleShot(1000,_nexus_ping_poll)
    # Native canvas's right-hand menu is drawn in QPainter and clickable.
    old_release=bar.canvas.mouseReleaseEvent
    def release(event):
        if event.button()==Qt.MouseButton.LeftButton and not bar.retracted:
            refresh=getattr(bar.canvas,'_n3xvs_net_refresh_rect',None)
            if refresh is not None and refresh.contains(event.position().toPoint()):
                if SPEED_TEST.start():
                    bar.canvas.setToolTip('Test Internet lancé en arrière-plan (Ookla Speedtest ou speedtest-cli)')
                else:
                    bar.canvas.setToolTip('Un test de débit est déjà en cours')
                return
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

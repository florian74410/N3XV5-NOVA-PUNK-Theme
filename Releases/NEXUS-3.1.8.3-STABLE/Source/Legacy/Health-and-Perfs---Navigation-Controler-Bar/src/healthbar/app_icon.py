"""CYBER NEXUS / NovaBar icon shared by taskbar, system tray, and installers."""
from __future__ import annotations
from pathlib import Path
import struct

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPolygonF, QPixmap

COLORS = {
    "blue-neon": "#23e6e8", "cyber-futuriste": "#23e6e8",
    "green-matrix": "#5df68c", "red-blood": "#ff4c76",
    "redblack-0822": "#FF2945",
}


def painted_icon(size=64, theme="blue-neon"):
    """Opaque, high contrast chip mark with a diagonal energy bolt."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 128, size / 128)
    accent = QColor(COLORS.get(theme, COLORS["blue-neon"]))
    redblack=theme=="redblack-0822"
    p.setPen(QPen(QColor("#D0193A" if redblack else "#175067"),3))
    p.setBrush(QColor("#090508" if redblack else "#041324"))
    p.drawRoundedRect(QRectF(7, 7, 114, 114), 24, 24)
    p.setPen(QPen(QColor("#E5344F" if redblack else "#12869b"),4))
    for x in (40, 64, 88):
        p.drawLine(x, 4, x, 17)
        p.drawLine(x, 111, x, 124)
    for y in (40, 64, 88):
        p.drawLine(4, y, 17, y)
        p.drawLine(111, y, 124, y)
    body = QPainterPath()
    pts = [(24, 52), (24, 33), (36, 21), (92, 21), (104, 33),
           (104, 95), (92, 107), (36, 107), (24, 95)]
    body.addPolygon(QPolygonF([QPointF(*xy) for xy in pts]))
    body.closeSubpath()
    p.setPen(QPen(accent, 5))
    p.setBrush(QColor("#210810" if redblack else "#08283b"))
    p.drawPath(body)
    n = QPainterPath(QPointF(40, 86))
    n.lineTo(40, 42); n.lineTo(86, 87); n.lineTo(86, 43)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(accent, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawPath(n)
    bolt = QPolygonF([QPointF(*xy) for xy in [(69,34),(51,64),(66,64),(59,94),(85,58),(69,58)]])
    p.setPen(QPen(QColor("#9A1530" if redblack else "#143d31"), 2))
    p.setBrush(QColor("#FF7C8C" if redblack else "#a3ff72"))
    p.drawPolygon(bolt)
    p.end()
    return image


def novabar_icon(theme="blue-neon"):
    """Multi-resolution icon for 16-256 px notifications and task switchers."""
    icon = QIcon()
    for size in (16, 22, 32, 48, 64, 128, 256):
        icon.addPixmap(QPixmap.fromImage(painted_icon(size, theme)))
    return icon


def save_brand_assets(destination):
    """Generate PNG and Windows ICO from the same mark using Qt and Python stdlib."""
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    png = target / "novabar-256.png"
    ico = target / "novabar.ico"
    if not painted_icon(256).save(str(png), "PNG"):
        raise OSError("Impossible de produire le logo NovaBar")
    blob = png.read_bytes()
    # Windows ICO supports PNG-compressed 256x256 entries.
    ico.write_bytes(struct.pack("<HHH", 0, 1, 1) +
                    struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(blob), 22) +
                    blob)
    return png, ico

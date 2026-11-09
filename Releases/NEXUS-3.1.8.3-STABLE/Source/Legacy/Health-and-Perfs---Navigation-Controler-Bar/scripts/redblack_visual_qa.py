"""Deterministic original-chrome snapshots: direct QImage painting (no compositor)."""
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtCore import Qt, QRectF

from healthbar.redblack_shell import paint_surface, CRIMSON, MUTED, WHITE

def snapshot(filename, width, height, kind, title, subtitle):
    image=QImage(width,height,QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect=QRectF(6,6,width-12,height-12)
    paint_surface(painter,rect,kind,.31,True)
    painter.setPen(QPen(QColor(CRIMSON),1))
    font=QFont("DejaVu Sans");font.setPixelSize(25 if width>900 else 18);font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRectF(43,40,width-88,42),Qt.AlignmentFlag.AlignLeft,title)
    painter.setPen(QColor(WHITE))
    font.setPixelSize(14);font.setBold(False);painter.setFont(font)
    painter.drawText(QRectF(43,86,width-88,45),Qt.AlignmentFlag.AlignLeft,subtitle)
    painter.end()
    assert image.pixelColor(0,0).alpha()==0,"top-left must be transparent"
    assert image.pixelColor(width-1,0).alpha()==0,"top-right must be transparent"
    assert image.pixelColor(0,height-1).alpha()==0,"bottom-left must be transparent"
    assert image.pixelColor(width-1,height-1).alpha()==0,"bottom-right must be transparent"
    assert image.pixelColor(width//2,height//2).alpha()>220,"opaque text area required"
    assert image.save(str(filename),"PNG")
    return filename

def main(folder):
    app=QApplication.instance() or QApplication(["redblack_visual_qa"])
    target=Path(folder);target.mkdir(parents=True,exist_ok=True)
    snapshot(target/"settings-chrome.png",1280,740,"settings",
       "NOVA / REDBLACK   0.8.2.2","METALLIC SHELL  /  45-DEGREE CORNERS  /  PCB ROUTING")
    snapshot(target/"holo-chrome.png",540,440,"holo",
       "◈ POWER HOLO","PHYSICAL SENSORS ONLY   /   W + V")
    snapshot(target/"notification-chrome.png",650,190,"notification",
       "◈ NOVA / NOTIFICATION","Original red neon chrome, fully transparent corners")
    snapshot(target/"dock-chrome.png",1500,115,"dock",
       "NOVA / REDBLACK","RUNNING APPLICATIONS  /  DESKTOP INTEGRATION")
    print("RedBlack original geometry rendered and alpha corner assertions passed")
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv)>1 else "redblack-qa"))

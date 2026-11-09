"""EWMH work-area reservations for NovaBar dock windows on XFCE/X11.

Reserve the configured expanded height even when the HUD is retracted.
This avoids resizing maximized windows on every hover animation. Do not
change XFCE's own panel settings, screen size or global workarea properties.
"""
import os
import sys


def reserve_edge(widget, side, height, enabled=True):
    if sys.platform!="linux" or not os.environ.get("DISPLAY"):
        return False
    from PySide6.QtWidgets import QApplication
    if QApplication.platformName()!="xcb":
        return False
    try:
        from Xlib import Xatom, display
        con=display.Display()
        try:
            win=con.create_resource_object("window",int(widget.winId()))
            root=con.screen().root.get_geometry()
            rect=widget.geometry()
            # EWMH struts apply to the physical root edges only, not a
            # monitor edge inside a multi-monitor desktop.
            top=0;bottom=0
            if enabled and side=="top" and rect.top()<=1:
                top=min(int(height),root.height)
            if enabled and side=="bottom" and rect.bottom()>=root.height-2:
                bottom=min(int(height),root.height)
            strut=con.intern_atom("_NET_WM_STRUT")
            partial=con.intern_atom("_NET_WM_STRUT_PARTIAL")
            wtype=con.intern_atom("_NET_WM_WINDOW_TYPE")
            dock=con.intern_atom("_NET_WM_WINDOW_TYPE_DOCK")
            if top or bottom:
                x0=max(0,min(root.width-1,rect.left()))
                x1=max(x0,min(root.width-1,rect.right()))
                win.change_property(wtype,Xatom.ATOM,32,[dock])
                values=[0,0,top,bottom,0,0,0,0,x0,x1,x0,x1]
                win.change_property(partial,Xatom.CARDINAL,32,values)
                win.change_property(strut,Xatom.CARDINAL,32,[0,0,top,bottom])
            else:
                # Remove only NovaBar's own reservations from its own window.
                win.delete_property(partial)
                win.delete_property(strut)
            con.flush()
            return bool(top or bottom)
        finally:
            con.close()
    except (ImportError,OSError,ValueError,RuntimeError):
        return False

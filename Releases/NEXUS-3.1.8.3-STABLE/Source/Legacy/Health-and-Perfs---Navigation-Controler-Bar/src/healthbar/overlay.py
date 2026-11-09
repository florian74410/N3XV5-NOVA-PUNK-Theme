"""Best-effort window priority, without stealing focus or bypassing the compositor."""
import os
import sys

def apply_priority(widget, enabled):
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        set_position=ctypes.windll.user32.SetWindowPos
        set_position.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
        set_position.restype=wintypes.BOOL
        if not set_position(int(widget.winId()),-1 if enabled else -2,0,0,0,0,0x0013):
            return 'Windows : priorité refusée par le système.'
        return 'Windows : TOPMOST, sans activation. Plein écran exclusif non garanti.'
    if sys.platform.startswith('linux'):
        from PySide6.QtWidgets import QApplication
        if QApplication.platformName()!='xcb' or not os.getenv('DISPLAY'):
            return 'Wayland : placement et priorité dépendent du compositeur. Overlay global non garanti.'
        try:
            from Xlib import X, display, protocol
            connection=display.Display()
            try:
                window=connection.create_resource_object('window',int(widget.winId()))
                message=protocol.event.ClientMessage(window=window,client_type=connection.intern_atom('_NET_WM_STATE'),data=(32,[1 if enabled else 0,connection.intern_atom('_NET_WM_STATE_ABOVE'),0,1,0]))
                connection.screen().root.send_event(message,event_mask=X.SubstructureRedirectMask|X.SubstructureNotifyMask)
                connection.flush()
            finally:connection.close()
            return 'X11 : ABOVE demandé au gestionnaire de fenêtres ; plein écran non garanti.'
        except Exception as error:
            return 'X11 : priorité Qt uniquement ('+str(error)+').'
    return 'macOS : priorité Qt ; Spaces et plein écran contrôlés par macOS.'


def apply_all_workspaces(widget):
    """Request 'on all desktops' from the X11 window manager after mapping.

    EWMH requires _NET_WM_DESKTOP = 0xFFFFFFFF. Set the property and send
    a client message because a window may already be mapped by the time
    Qt emits showEvent. Both paths are needed under xfwm4.
    """
    if not sys.platform.startswith("linux"):
        return False
    from PySide6.QtWidgets import QApplication
    if QApplication.platformName() != "xcb" or not os.getenv("DISPLAY"):
        return False
    try:
        from Xlib import X, Xatom, display, protocol
        connection = display.Display()
        try:
            window = connection.create_resource_object("window", int(widget.winId()))
            root = connection.screen().root
            desktop = connection.intern_atom("_NET_WM_DESKTOP", only_if_exists=False)
            sticky = connection.intern_atom("_NET_WM_STATE_STICKY", only_if_exists=False)
            state = connection.intern_atom("_NET_WM_STATE", only_if_exists=False)
            all_desktops = 0xFFFFFFFF
            window.change_property(desktop, Xatom.CARDINAL, 32, [all_desktops])
            root.send_event(
                protocol.event.ClientMessage(
                    window=window, client_type=desktop,
                    data=(32, [all_desktops, 1, 0, 0, 0])),
                event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            root.send_event(
                protocol.event.ClientMessage(
                    window=window, client_type=state,
                    data=(32, [1, sticky, 0, 1, 0])),
                event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            connection.flush()
            connection.sync()
        finally:
            connection.close()
        return True
    except (OSError, ImportError, ValueError, RuntimeError):
        return False


def schedule_all_workspaces(widget):
    """Retry when the Xfce WM has finished mapping the actual top-level XID."""
    if not sys.platform.startswith("linux") or not os.getenv("DISPLAY"):
        return
    from PySide6.QtCore import QTimer
    import weakref
    ref = weakref.ref(widget)
    def request():
        target = ref()
        if target is None:
            return
        try:
            if target.isVisible():
                apply_all_workspaces(target)
        except RuntimeError:
            # Qt window deleted before the queued request executes.
            pass
    for delay_ms in (0, 180, 750):
        QTimer.singleShot(delay_ms, request)


def is_on_all_workspaces(widget):
    """Read actual X11 _NET_WM_DESKTOP, not just Qt's requested window flags.

    This allows periodic healing when xfwm4 assigns a newly mapped window
    to the current workspace despite earlier requests.
    """
    if not sys.platform.startswith("linux") or not os.getenv("DISPLAY"):
        return False
    from PySide6.QtWidgets import QApplication
    if QApplication.platformName() != "xcb":
        return False
    try:
        from Xlib import Xatom, display
        con = display.Display()
        try:
            xid = int(widget.winId())
            window = con.create_resource_object("window", xid)
            atom = con.intern_atom("_NET_WM_DESKTOP", only_if_exists=False)
            prop = window.get_full_property(atom, Xatom.CARDINAL)
            return bool(prop is not None and prop.value is not None
                        and len(prop.value) == 1
                        and int(prop.value[0]) == 0xFFFFFFFF)
        finally:
            con.close()
    except Exception:
        return False


def maintain_all_workspaces(widget):
    """Correct workspace drift without repeatedly writing on every sensor tick."""
    if not sys.platform.startswith("linux") or not os.getenv("DISPLAY"):
        return
    try:
        if widget.isVisible() and not is_on_all_workspaces(widget):
            apply_all_workspaces(widget)
    except RuntimeError:
        pass

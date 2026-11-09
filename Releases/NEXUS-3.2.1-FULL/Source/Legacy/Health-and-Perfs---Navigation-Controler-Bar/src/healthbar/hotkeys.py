"""Global shortcuts when the OS grants access, with an explicit local fallback."""
import os
import sys
import threading
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut


def native_sequence(sequence):
    aliases={"ctrl":"<ctrl>","shift":"<shift>","alt":"<alt>","meta":"<cmd>",
             "space":"<space>","esc":"<esc>","escape":"<esc>","tab":"<tab>"}
    parts=sequence.lower().split("+")
    if not parts or any(not p for p in parts):raise ValueError("Raccourci non pris en charge")
    return "+".join(aliases.get(p,"<"+p+">" if len(p)>1 else p) for p in parts)


class X11Hotkeys:
    def __init__(self, bindings, callback):
        from Xlib import X, XK, display
        self.display = display.Display()
        self.root = self.display.screen().root
        self.bindings = {}
        self.stopped = False
        self.X = X
        errors = []
        for binding in bindings:
            parts = binding["sequence"].split("+")
            mask = 0
            for modifier in parts[:-1]:
                mask |= {"Ctrl": X.ControlMask, "Alt": X.Mod1Mask, "Shift": X.ShiftMask,
                         "Meta": X.Mod4Mask}.get(modifier, 0)
            key = parts[-1]
            symbol = XK.string_to_keysym(key.lower() if len(key) == 1 else {"Space": "space", "Esc": "Escape"}.get(key, key))
            keycode = self.display.keysym_to_keycode(symbol)
            if not keycode:
                self.stop()
                raise ValueError("Touche X11 non reconnue : " + key)
            self.bindings[(keycode, mask)] = binding["action"]
            for locks in (0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask):
                self.root.grab_key(keycode, mask | locks, False, X.GrabModeAsync, X.GrabModeAsync,
                                   onerror=lambda error, request: errors.append(error))
        self.display.sync()
        if errors:
            self.stop()
            raise RuntimeError("Une combinaison est déjà réservée par une autre application")
        self.callback = callback
        self.thread = threading.Thread(target=self.listen, daemon=True, name="novabar-shortcuts")

    def start(self):
        self.thread.start()

    def listen(self):
        try:
            while not self.stopped:
                event = self.display.next_event()
                if event.type == self.X.KeyPress:
                    action = self.bindings.get((event.detail, event.state & ~(self.X.LockMask | self.X.Mod2Mask)))
                    if action:
                        self.callback(action)
        except Exception:
            # Closing the display releases grabs and interrupts next_event during shutdown.
            return

    def stop(self):
        self.stopped = True
        try:
            self.display.close()
        except Exception:
            pass


class HotkeyController(QObject):
    triggered=Signal(str)

    def __init__(self,bar):
        super().__init__(bar);self.bar=bar;self.listener=None;self.local=[];self.status=""
        self.triggered.connect(self.dispatch)

    def stop(self):
        if self.listener:
            self.listener.stop();self.listener=None
        for shortcut in self.local:shortcut.setEnabled(False);shortcut.deleteLater()
        self.local=[]

    def configure(self,bindings):
        self.stop()
        if not bindings:return
        try:
            if os.getenv("QT_QPA_PLATFORM")=="offscreen" or os.getenv("XDG_SESSION_TYPE")=="wayland":
                raise RuntimeError("Raccourcis globaux indisponibles dans cette session")
            if sys.platform.startswith("linux"):
                self.listener=X11Hotkeys(bindings,self.triggered.emit)
            else:
                from pynput import keyboard
                mapped={native_sequence(item["sequence"]):(lambda action=item["action"]:self.triggered.emit(action)) for item in bindings}
                self.listener=keyboard.GlobalHotKeys(mapped)
            self.listener.start()
            self.status="Raccourcis globaux actifs (selon les permissions du système)"
        except Exception as error:
            if self.listener:self.listener.stop();self.listener=None
            self.status="Mode local : "+str(error)
            for item in bindings:
                shortcut=QShortcut(QKeySequence(item["sequence"]),self.bar)
                shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                shortcut.activated.connect(lambda action=item["action"]:self.triggered.emit(action))
                self.local.append(shortcut)
        self.bar.turbo.setToolTip(self.status)

    def dispatch(self,action):
        if action=="toggle":
            if self.bar.isVisible() and not self.bar.retracted:self.bar.hide()
            else:self.bar.reveal()
        elif action=="expand":self.bar.toggle_expand()
        elif action=="preferences":self.bar.preferences()

"""A system-wide hotkey (Windows RegisterHotKey), so it works while the game has focus."""

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QObject, Signal
from PySide6.QtWidgets import QApplication

WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000
VK_F10 = 0x79
HOTKEY_ID = 0xA1C2  # any id unique within this app


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, on_hotkey: "GlobalHotkey") -> None:
        super().__init__()
        self._owner = on_hotkey

    def nativeEventFilter(  # noqa: N802 - Qt API
        self, event_type: QByteArray | bytes | bytearray | memoryview, message: int
    ) -> object:
        name = event_type.data() if isinstance(event_type, QByteArray) else bytes(event_type)
        if name == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self._owner.pressed.emit()
                return True, 0
        return False, 0


class GlobalHotkey(QObject):
    pressed = Signal()

    def __init__(self, app: QApplication, virtual_key: int = VK_F10, label: str = "F10") -> None:
        super().__init__(app)
        self.label = label
        self.registered = False
        self._filter = _Filter(self)
        if sys.platform != "win32":
            return
        # Own WinDLL with declared signatures (see capture.window._api for why).
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.RegisterHotKey.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self._user32.RegisterHotKey.restype = wintypes.BOOL
        self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self._user32.UnregisterHotKey.restype = wintypes.BOOL
        self.registered = bool(
            self._user32.RegisterHotKey(None, HOTKEY_ID, MOD_NOREPEAT, virtual_key)
        )
        if self.registered:
            app.installNativeEventFilter(self._filter)
            app.aboutToQuit.connect(self.unregister)

    def unregister(self) -> None:
        if self.registered:
            self._user32.UnregisterHotKey(None, HOTKEY_ID)
            self.registered = False

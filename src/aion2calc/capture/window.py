"""Find the game window and capture its contents (Windows only, via ctypes).

Only the game window's client area is captured — never the whole desktop — and only when the
game is the active window, so other apps (browser, chat) never end up in a capture.
"""

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import PureWindowsPath

from PIL import Image, ImageGrab

GAME_PROCESS = "aion2.exe"
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _api() -> tuple[ctypes.WinDLL, ctypes.WinDLL]:
    """user32 and kernel32 with their signatures declared: without them ctypes passes handles as
    32-bit ints, which truncates them on 64-bit Windows. Own WinDLL objects, so the shared
    `ctypes.windll` isn't changed for anyone else."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClientRect.restype = wintypes.BOOL
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return user32, kernel32


@dataclass(frozen=True)
class GameWindow:
    handle: int
    process: str
    left: int
    top: int
    width: int
    height: int


class CaptureError(Exception):
    """Shown to the user as-is."""


def _process_name(kernel32: ctypes.WinDLL, pid: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return PureWindowsPath(buffer.value).name.lower()
    finally:
        kernel32.CloseHandle(handle)


def active_game_window() -> GameWindow:
    """The foreground window if it's the game; raises CaptureError otherwise."""
    if sys.platform != "win32":
        raise CaptureError("capture works on Windows only")
    user32, kernel32 = _api()
    handle = user32.GetForegroundWindow()
    if not handle:
        raise CaptureError("no active window")
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
    process = _process_name(kernel32, pid.value)
    if process != GAME_PROCESS:
        raise CaptureError("the game isn't the active window; click into AION 2, then press F10")
    rect = wintypes.RECT()
    origin = wintypes.POINT(0, 0)
    if not (
        user32.GetClientRect(handle, ctypes.byref(rect))
        and user32.ClientToScreen(handle, ctypes.byref(origin))
    ):
        raise CaptureError("couldn't read the game window's position")
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width < 200 or height < 200:
        raise CaptureError("the game window is minimised or too small")
    return GameWindow(handle, process, origin.x, origin.y, width, height)


def grab(window: GameWindow) -> Image.Image:
    box = (window.left, window.top, window.left + window.width, window.top + window.height)
    return ImageGrab.grab(bbox=box, all_screens=True)

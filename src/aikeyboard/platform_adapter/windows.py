import ctypes
import time

import win32gui
import win32con

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

PUL = ctypes.POINTER(ctypes.c_ulong)

# Define KEYBDINPUT structure
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),     # Virtual Key code (not used here)
        ("wScan", ctypes.c_ushort),   # Unicode character
        ("dwFlags", ctypes.c_ulong),  # KEYEVENTF_UNICODE
        ("time", ctypes.c_ulong),     # Timestamp
        ("dwExtraInfo", PUL)
    ]

# Define INPUT structure
class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", ctypes.c_ulong),     # INPUT_KEYBOARD
        ("_input", _INPUT)
    ]

# Constants
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002

# Function reference
SendInput = ctypes.windll.user32.SendInput

class WindowsAdapter:
    def __init__(self):
        self._prev_hwnd = None
        self._focus_candidate = None
        self._focus_candidate_since = 0
        self._start_focus_timer()

        # Improve tray icon visibility
        try:
            app_id = u"com.aikeyboard.app"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

    def _start_focus_timer(self):
        from PySide6.QtCore import QTimer
        self._focus_timer = QTimer()
        self._focus_timer.timeout.connect(self._poll_foreground_window)
        self._focus_timer.start(400)

    def _poll_foreground_window(self):
        hwnd = win32gui.GetForegroundWindow()
        now = time.monotonic()

        # Filter out useless handles (zero, or taskbar)
        if hwnd == 0:
            return

        class_name = win32gui.GetClassName(hwnd)
        if class_name in ("Shell_TrayWnd", "NotifyIconOverflowWindow"):
            return

        if hwnd != self._focus_candidate:
            self._focus_candidate = hwnd
            self._focus_candidate_since = now
        elif now - self._focus_candidate_since >= 1.5:
            self._prev_hwnd = hwnd

    def setup_tray_integration(self):
        pass  # All done in __init__

    def restore_previous_focus(self):
        if self._prev_hwnd and win32gui.IsWindow(self._prev_hwnd):
            try:
                win32gui.ShowWindow(self._prev_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self._prev_hwnd)
            except Exception as e:
                print(f"[WARN] Failed to refocus: {e}")

    def set_font(self, app):
        from PySide6.QtGui import QFont
        app.setFont(QFont("Segoe UI Emoji", 10))

    def write(self, text: str):
        for char in text:
            utf16_code = ord(char)
            down_event = INPUT(
                type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(
                    wVk=0,
                    wScan=utf16_code,
                    dwFlags=KEYEVENTF_UNICODE,
                    time=0,
                    dwExtraInfo=ctypes.pointer(ctypes.c_ulong(0))
                )
            )

            up_event = INPUT(
                type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(
                    wVk=0,
                    wScan=utf16_code,
                    dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                    time=0,
                    dwExtraInfo=ctypes.pointer(ctypes.c_ulong(0))
                )
            )

            SendInput(1, ctypes.byref(down_event), ctypes.sizeof(INPUT))
            SendInput(1, ctypes.byref(up_event), ctypes.sizeof(INPUT))
            time.sleep(0.005)  # Delay for reliability


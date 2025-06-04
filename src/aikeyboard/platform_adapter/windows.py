import ctypes
import ctypes.wintypes as wintypes
import time

import win32gui
import win32con

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from logging_config import LoggingConfig
log = LoggingConfig.get_logger('windows')

# Constants
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
EXTRAINFO_MAGIC = 0xABAD1DEA  # Magic number to identify our inputs

# Structures
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ki", KEYBDINPUT),
        ("padding", ctypes.c_ubyte * 8),
    ]

class WindowsAdapter:
    def __init__(self):
        self._prev_hwnd = None
        self._focus_candidate = None
        self._focus_candidate_since = 0

        # Improve tray icon visibility
        try:
            app_id = u"com.aikeyboard.app"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass
        log.info('WindowsAdapter(): selected')

    def setup(self):
        pass

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
        from PySide6.QtCore import QTimer
        self._focus_timer = QTimer()
        self._focus_timer.timeout.connect(self._poll_foreground_window)
        self._focus_timer.start(400)

    def restore_previous_focus(self):
        if self._prev_hwnd and win32gui.IsWindow(self._prev_hwnd):
            try:
                win32gui.ShowWindow(self._prev_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self._prev_hwnd)
            except Exception as e:
                logging.warn(f"Failed to refocus: {e}")

    def set_font(self, app):
        from PySide6.QtGui import QFont
        app.setFont(QFont("Segoe UI Emoji", 10))

    def write(self, text: str):
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        log.debug(f'Foreground Window before SendInput: {hwnd} "{title}"')

        def is_window_focused(hwnd):
            """Check if the specified window is focused"""
            return ctypes.windll.user32.GetForegroundWindow() == hwnd

        def inject(text, char_delay=0.02, retry_delay=0.1, max_retries=3):
            """Robust Unicode text injection with focus protection"""
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            extra_info = ctypes.pointer(wintypes.ULONG(EXTRAINFO_MAGIC))
    
            for char in text:
                retries = 0
                while retries < max_retries:
                    if not is_window_focused(hwnd):
                        log.warn("Focus lost! Waiting for window to regain focus...")
                        time.sleep(retry_delay)
                        retries += 1
                        continue
                
                    # Prepare the key events
                    inputs = (INPUT * 2)()
            
                    # Key down
                    inputs[0].type = INPUT_KEYBOARD
                    inputs[0].ki = KEYBDINPUT(
                        wVk=0,
                        wScan=ord(char),
                        dwFlags=KEYEVENTF_UNICODE,
                        time=0,
                        dwExtraInfo=extra_info
                    )
            
                    # Key up
                    inputs[1].type = INPUT_KEYBOARD
                    inputs[1].ki = KEYBDINPUT(
                        wVk=0,
                        wScan=ord(char),
                        dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                        time=0,
                        dwExtraInfo=extra_info
                    )
            
                    # Send the events
                    ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
            
                    # Small delay between characters
                    time.sleep(char_delay)
                    break
                else:
                    log.error(f"\nFailed to send character '{char}' after {max_retries} retries")
        inject(text)


if __name__ == "__main__":
    LoggingConfig.configure()
    log.info("Focus your target window (you have 5 seconds)...")
    time.sleep(5)  # Time to switch to your target app
    
    samples = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "È già ora di pranzo! L'acqua è fredda.",
        "Ciò che non ti uccide, ti rende più forte.",
        "Nel mezzo del cammin di nostra vita..."
    ]
    win = WindowsAdapter()
    for text in samples:
        win.write(text)
        win.write("\n")  # New line after each sample
        time.sleep(0.5)  # Pause between injections
        

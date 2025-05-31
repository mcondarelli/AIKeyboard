import ctypes
import time

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

class WindowsInput:
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

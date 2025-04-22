# src/aikeyboard/keyboard/input_manager.py
import platform
from src.aikeyboard.keyboard.windows import WindowsInput
from src.aikeyboard.keyboard.linux import LinuxInput
from src.aikeyboard.keyboard.macos import MacInput

class InputManager:
    def __init__(self):
        system = platform.system()
        if system == "Windows":
            self.impl = WindowsInput()
        elif system == "Linux":
            self.impl = LinuxInput()
        elif system == "Darwin":
            self.impl = MacInput()
        else:
            raise OSError(f"Unsupported system: {system}")
            
    def write(self, text):
        self.impl.write(text)

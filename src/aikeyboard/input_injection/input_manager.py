# src/aikeyboard/keyboard/input_manager.py
import platform



class InputManager:
    def __init__(self):
        system = platform.system()
        if system == "Windows":
            from aikeyboard.input_injection.windows import WindowsInput
            self.impl = WindowsInput()
        elif system == "Linux":
            from aikeyboard.input_injection.linux import LinuxInput
            self.impl = LinuxInput()
        elif system == "Darwin":
            from aikeyboard.input_injection.macos import MacInput
            self.impl = MacInput()
        else:
            raise OSError(f"Unsupported system: {system}")
            
    def write(self, text):
        self.impl.write(text)

# src/aikeyboard/keyboard/macos.py
import subprocess

class MacInput:
    def write(self, text):
        subprocess.run(["osascript", "-e", f'tell application "System Events" to keystroke "{text}"'])
        
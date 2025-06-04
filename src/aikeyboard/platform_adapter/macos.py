# src/aikeyboard/keyboard/macos.py
import subprocess

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


class MacAdapter:
    def setup(self):
        pass

    def set_font(self, app: QApplication):
        app.setFont(QFont("Apple Color Emoji", 11))

    def write(self, text):
        subprocess.run(["osascript", "-e", f'tell application "System Events" to keystroke "{text}"'])

    def setup_tray_integration(self):
        pass

    def restore_previous_focus(self):
        pass

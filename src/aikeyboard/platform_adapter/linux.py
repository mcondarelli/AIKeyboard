# src/aikeyboard/keyboard/linux.py
import subprocess
import logging

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


class LinuxAdapter:
    def __init__(self):
        self.xdotool_available = self._check_xdotool()

    def setup(self):
        pass

    def set_font(self, app: QApplication):
        app.setFont(QFont("Segoe UI Emoji", 10))

    def _check_xdotool(self):
        try:
            subprocess.run(['xdotool', '--version'], check=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logging.warning("xdotool not available - keyboard input will not work")
            return False

    def write(self, text):
        if not self.xdotool_available:
            return
            
        try:
            subprocess.run(['xdotool', 'type', '--delay', '50', '--', text],
                         check=True)
            logging.debug(f"Injected text: {text}")
        except Exception as e:
            logging.error(f"Input error: {e}")

    def setup_tray_integration(self):
        pass

    def restore_previous_focus(self):
        pass


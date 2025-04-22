# src/aikeyboard/keyboard/linux.py
import subprocess
import logging

class LinuxInput:
    def __init__(self):
        self.xdotool_available = self._check_xdotool()
        
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

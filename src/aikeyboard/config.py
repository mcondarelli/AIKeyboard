# src/aikeyboard/config.py
from PySide6.QtCore import QSettings
from typing import Optional
from aikeyboard.ui.device_manager import DeviceManager

class AppConfig:
    def __init__(self):
        self.settings = QSettings("AIKeyboard", "SpeechToText")
        
    @property
    def audio_device(self) -> Optional[str]:
        device = self.settings.value("audio_device")
        if any(device == n for _, n in DeviceManager().get_physical_devices()):
            return device
        return None
        
    @audio_device.setter
    def audio_device(self, name: str):
        self.settings.setValue("audio_device", name)

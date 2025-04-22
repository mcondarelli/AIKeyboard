# src/aikeyboard/config.py
from PySide6.QtCore import QSettings

class AppConfig:
    def __init__(self):
        self.settings = QSettings("AIKeyboard", "SpeechToText")
        
    @property
    def audio_device(self):
        return self.settings.value("audio_device", -1, type=int)
        
    @audio_device.setter
    def audio_device(self, index):
        self.settings.setValue("audio_device", index)

# src/aikeyboard/config.py
from PySide6.QtCore import QObject, Property, QSettings, Signal
from typing import Optional
from aikeyboard.device_manager import device_manager

class _AppConfig(QObject):
    deviceChanged = Signal(str)
    modelChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self._settings = QSettings("AIKeyboard", "SpeechToText")
        self._device = self._settings.value("audio_device")
        self._model = self._settings.value("model")
        
    def get_device(self) -> Optional[str]:
        if not any(self._device == n for _, n in device_manager.get_physical_devices()):
            self._device = None
        return self._device
    def set_device(self, name: str):
        if self._device != name:
            self._device = name
            self._settings.setValue("audio_device", self._device)
            self.deviceChanged.emit(self._device)
    audio_device = Property(str, get_device, set_device, None, '', notify=deviceChanged)

    def get_model(self):
        return self._model
    def set_model(self, model: str):
        if self._model != model:
            self._model = model
            self._settings.setValue("model", self._model)
            self.modelChanged.emit(self._model)

    model = Property(str, get_model, set_model, None, '', notify=modelChanged)

app_config = _AppConfig()

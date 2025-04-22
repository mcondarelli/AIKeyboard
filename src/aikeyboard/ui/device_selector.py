# src/aikeyboard/ui/device_selector.py
import pyaudio
from PySide6.QtGui import QAction

class DeviceSelector:
    def __init__(self, parent_menu, callback):
        self.pa = pyaudio.PyAudio()
        self._add_to_menu(parent_menu)
        self.callback = callback

    def _get_physical_devices(self):
        devices = []
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            if (int(info["maxInputChannels"]) > 0 and 
                self._is_hardware_device(info["name"])):
                devices.append((i, info["name"]))
        return devices

    def _is_hardware_device(self, name):
        # Platform-specific hardware detection
        import platform
        system = platform.system()
        
        if system == "Linux":
            return "hw:" in name.lower()
        elif system == "Windows":
            return not ("virtual" in name.lower() or "mme" in name.lower())
        elif system == "Darwin":
            return "built-in" in name.lower()
        return True

    def _add_to_menu(self, parent_menu):
        submenu = parent_menu.addMenu("Select Device")
        for idx, name in self._get_physical_devices():
            action = QAction(f"{idx}: {name[:40]}", submenu)
            action.triggered.connect(lambda _, i=idx: self._on_select(i))
            submenu.addAction(action)

    def _on_select(self, index):
        print(f"Selected device: {index}")  # Replace with your logic
        self.callback(index)
        
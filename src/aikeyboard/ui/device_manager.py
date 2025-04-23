# src/aikeyboard/ui/device_selector.py
import pyaudio
#from PySide6.QtGui import QAction
from PySide6.QtCore import QObject, Signal

class DeviceManager(QObject):
    device_selected = Signal(int)  # Signal when device is chosen

    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.current_device = None

    def get_physical_devices(self):
        devices = []
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            if (int(info["maxInputChannels"]) > 0 and self._is_hardware_device(info["name"])):
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

    #def populate_device_menu(self, menu, callback):
    #    """Add devices to provided menu"""
    #    menu.clear()
    #    for idx, name in self.get_physical_devices():
    #        action = QAction(self.tr(f"{idx}: {name[:40]}"), menu)
    #        action.triggered.connect(lambda _, i=idx: callback(i))
    #        menu.addAction(action)
    
    def get_device_name(self, index):
        """Get display name for a device index"""
        try:
            return self.pa.get_device_info_by_index(index)["name"]
        except:
            return "Unknown Device"
        
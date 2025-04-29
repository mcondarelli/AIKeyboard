# src/aikeyboard/ui/device_selector.py
import pyaudio

#from PySide6.QtGui import QAction
from PySide6.QtCore import QObject


class DeviceManager(QObject):
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

    def get_device_name(self, index):
        """Get display name for a device index"""
        try:
            return self.pa.get_device_info_by_index(index)["name"]
        except:  # noqa: E722
            return "Unknown Device"
        
    def get_device_index(self, name):
        """Get index for a given device name"""
        return next(
            (i for i in range(self.pa.get_device_count())
            if self.pa.get_device_info_by_index(i)["name"] == name),
            -1)  # Default if no match found
    
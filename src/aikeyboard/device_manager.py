# src/aikeyboard/device_manager.py
import pyaudio

#from PySide6.QtGui import QAction
from PySide6.QtCore import QObject


class _DeviceManager(QObject):
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.current_device = None
        self.devices = None

    def shutdown(self):
        self.pa.terminate()
        #global device_manager
        #device_manager = None

    def get_physical_devices(self):
        if self.devices is None:
            self.devices = []
            for i in range(self.pa.get_device_count()):
                info = self.pa.get_device_info_by_index(i)
                name = info.get("name", "")
                if self._is_valid_input_device(name, i):
                    self.devices.append((i, name))
        return self.devices

    def _is_valid_input_device(self, name, index=None):
        """Return True if the device is likely to be a usable microphone."""
        if index is None:
            index = self.get_device_index(name)
        name = name.lower()

        # Platform-specific name heuristics
        import platform
        system = platform.system()
        if system == "Linux":
            if "monitor" in name or "loopback" in name:
                return False
        elif system == "Windows":
            if "virtual" in name or "mme" in name or "mixaggio" in name or "stereo" in name:
                return False
        elif system == "Darwin":
            if "built-in output" in name:
                return False

        # Try to open the device and check usability
        try:
            info = self.pa.get_device_info_by_index(index)
            rate = int(info['defaultSampleRate'])
            if info.get('maxInputChannels', 0) < 1: # type: ignore
                return False
            # Try opening the device to ensure it's actually usable
            stream = self.get_stream(rate, index, 512)
            stream.close()
            return True
        except Exception:
            return False
            

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
    
    def get_pa(self):
        return self.pa
    
    def get_stream(self, rate, index, frames_per_buffer, **kwargs):
        stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=rate,
            input=True,
            input_device_index=index,
            frames_per_buffer=frames_per_buffer,
            **kwargs
        )
        return stream

    
device_manager = _DeviceManager()

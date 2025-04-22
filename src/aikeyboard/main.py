# src/aikeyboard/main.py
import sys
import logging
from typing import Optional
from PySide6.QtWidgets import QApplication
from aikeyboard.config import AppConfig
from src.aikeyboard.tray import SystemTray
from src.aikeyboard.ui.device_selector import DeviceSelector
from src.aikeyboard.keyboard.input_manager import InputManager
from src.aikeyboard.speech import SpeechRecognizer

logging.basicConfig(level=logging.INFO)

class AIKeyboardApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.config = AppConfig()
        self.tray = SystemTray()
        self.input = InputManager()
        self.speech: Optional[SpeechRecognizer] = None
        self._setup_ui()
        self._load_config() 

    def _setup_ui(self):
        # Device selection
        DeviceSelector(self.tray.menu, self._on_device_selected)
        
        # Toggle listening
        self.listen_action = self.tray.add_menu_item("Start Listening", self._toggle_listening)
        
        # Test input
        #self.tray.add_menu_item("Test Input", lambda: self.input.write("TEST"))
 
        # Test input
        self.tray.add_menu_item("Test Italian", lambda: self.input.write("àèéìòù"))

        # Quit
        self.tray.add_menu_item("Quit", self.app.quit)

    def _load_config(self):
        """Load saved device index"""
        device_index = self.config.audio_device
        if device_index != -1:
            self._on_device_selected(device_index)
            
    def _on_device_selected(self, index):
        logging.info(f"Selected audio device: {index}")
        self.config.audio_device = index  # Save selection
        if self.speech:
            self.speech.stop_listening()
        self.speech = SpeechRecognizer(device_index=index)

    def _toggle_listening(self):
        if not hasattr(self, 'is_listening') or not self.is_listening:
            if self.speech:
                # Clean up any previous connections
                if hasattr(self, '_worker_connections'):
                    for connection in self._worker_connections:
                        try:
                            self.worker.signal.disconnect(connection)
                        except (RuntimeError, AttributeError):
                            pass
                    del self._worker_connections
                
                self.speech.worker_created.connect(self._connect_worker_signals)
                self.speech.start_listening(self._on_speech_recognized)
                self.listen_action.setText("Stop Listening")
                self.is_listening = True
        else:
            if self.speech:
                self.speech.stop_listening()
                self.listen_action.setText("Start Listening")
                self.is_listening = False
    
    def _connect_worker_signals(self, worker):
        """Connect signals with automatic cleanup"""
        # Store connections so we can disconnect them later
        self._worker_connections = [
            worker.state_changed.connect(self.tray.update_state),
            worker.partial_result.connect(lambda text: self.tray.setToolTip(f"Listening: {text}...")),
            worker.destroyed.connect(lambda: self.tray.update_state('idle'))
        ]
        self.worker = worker

    def _on_speech_recognized(self, text):
        logging.info(f"Recognized: {text}")
        self.input.write(text + " ")  # Add space after each phrase

    def run(self):
        self.tray.show()
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = AIKeyboardApp()
    app.run()
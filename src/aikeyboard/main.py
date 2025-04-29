# src/aikeyboard/main.py
import logging
import sys
from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

from aikeyboard.config import AppConfig
from aikeyboard.ui.device_manager import DeviceManager
from src.aikeyboard.keyboard.input_manager import InputManager
from src.aikeyboard.speech import SpeechRecognizer, SpeechWorker
from src.aikeyboard.tray import SystemTray

logging.basicConfig(level=logging.INFO)

class AIKeyboardApp(QObject):
    def __init__(self):
        self.is_listening = False
        self._current_worker: Optional[SpeechWorker] = None
        self.app = QApplication(sys.argv)
        self.config = AppConfig()

        # Initialize components
        self.tray = SystemTray()
        self.device_manager = DeviceManager()
        self.input = InputManager()
        self.speech: Optional[SpeechRecognizer] = None
        self._setup_state_handling()
        self.tray.update_state('uninitialized')

        # Connect components
        self._setup_menu()
        self._load_config()

    def _setup_state_handling(self):
        """Connect all state-related signals"""
        self.state_connections = []

    def _setup_menu(self):
        # Device selection
        # Populate device menu
        for idx, name in self.device_manager.get_physical_devices():
            action = QAction(f"{idx}: {name[:40]}", self.tray.device_menu)
            action.triggered.connect(lambda: self._on_device_selected(name))
            self.tray.device_menu.addAction(action)
            
        # Connect listening toggle
        self.tray.activated.connect(self._toggle_listening)
        
    def _load_config(self):
        """Load saved device index"""
        device = self.config.audio_device
        if device is not None:
            self._on_device_selected(device)
            
    def _on_device_selected(self, name):
        logging.info(f"Selected audio device: {name}")
        self.config.audio_device = name
        index = self.device_manager.get_device_index(name)
        if not name or index < 0:
            logging.warning(f'Inconsistent selected device {index}: "{name}", ignoring.')
            self.tray.update_state('uninitialized')
            self.tray.device = None
            return

        # Update UI
        self.tray.update_state('idle')
        self.tray.device_info.setText(self.tr("Using: %1").replace('%1', name))
        self.tray.device = name

        # Reinitialize speech
        if self.speech:
            self.speech.stop_listening()
        self.speech = SpeechRecognizer(device_index=index)
        if self.speech:
            # Connect new speech instance
            self.state_connections.append(
                self.speech.worker_created.connect(self._connect_worker_signals)
            )

    def _toggle_listening(self):
        logging.info(f'AIKeyboardApp._togglelistening({self.is_listening}): called')
        if not self.speech or not self.tray.device:
            return
            
        if not getattr(self, 'is_listening', False):
            self.speech.start_listening()
            self.is_listening = True
        else:
            self.speech.stop_listening()
            self.is_listening = False
            
        self.tray.listen_action.setText(self.tr("Stop listening") if self.is_listening else self.tr("Start listening"))
        self.tray.update_state('listening' if self.is_listening else 'idle')
        logging.info(f'AIKeyboardApp._togglelistening({self.is_listening}): at exit')
    
    def _connect_worker_signals(self, worker):
        """Minimal working version with proper disconnections"""
        # Disconnect previous
        if self._current_worker:
            try: 
                self._current_worker.state_changed.disconnect()
            except:  # noqa: E722
                pass
            try: 
                self._current_worker.recognized.disconnect()
            except:  # noqa: E722
                pass
            try: 
                self._current_worker.partial_result.disconnect()
            except:  # noqa: E722
                pass
            try: 
                self._current_worker.error.disconnect()
            except:  # noqa: E722
                pass
        
        # Connect new
        self._current_worker = worker
        worker.state_changed.connect(self._handle_state_change)
        worker.recognized.connect(self._on_speech_recognized)
        worker.partial_result.connect(self._on_partial_result)
        worker.error.connect(self._on_speech_error)        

    def _handle_state_change(self, state):
        """Update UI based on state"""
        self.tray.update_state(state)
        logging.debug(f"State changed to: {state}")
        
    def _on_partial_result(self, text):
        """Handle partial recognition results"""
        self.tray.setToolTip(f"Listening: {text}...")
        
    def _on_speech_error(self, error):
        logging.error(f"Speech recognition error: {error}")
        self.tray.show_notification(f"Error: {error}")
        
    def _on_speech_recognized(self, text):
        logging.info(f"Recognized: {text}")
        self.input.write(text + " ")  # Add space after each phrase

    def run(self):
        self.tray.show()
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = AIKeyboardApp()
    app.run()
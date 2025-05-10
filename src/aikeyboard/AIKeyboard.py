# src/aikeyboard/AIKeyboard.py
import logging
import sys
from typing import Optional

from PySide6.QtCore import QCoreApplication, QLocale, QTimer, QTranslator, Slot
from PySide6.QtGui import QAction, QColorConstants, QIcon, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from aikeyboard import resources  # noqa: F401
from aikeyboard.config import app_config
from aikeyboard.input_injection import InputManager
from aikeyboard.speech import SpeechRecognizer, SpeechWorker
from aikeyboard.device_manager import device_manager

logging.basicConfig(level=logging.DEBUG)

class AIKeyboardApp(QSystemTrayIcon):
    LANG_FLAGS = {
        "all": "🇺🇳", "ar": "🇸🇦", "ar-tn": "🇹🇳", "br": "🇫🇷",
        "ca": "🇪🇸", "cn": "🇨🇳", "cs": "🇨🇿", "de": "🇩🇪", 
        "el-gr": "🇬🇷", "en": "🇬🇧", "en-gb": "🇬🇧", "en-in": "🇮🇳",
        "en-us": "🇺🇸", "eo": "🏳", "es": "🇪🇸", "fa": "🏳", "fr": "🇫🇷",
        "gu": "🏳", "hi": "🇮🇳", "it": "🇮🇹", "ja": "🇯🇵","ko": "🇰🇷",
        "kz": "🇰🇿", "nl": "🇳🇱", "pl": "🇵🇱", "pt": "🇵🇹", "sv": "🇸🇪", 
        "ru": "🇷🇺", "te": "🏳", "tg": "🇹🇯", "tl-ph": "🇵🇭", "tr": "🇹🇷",
        "ua": "🇺🇦", "uz": "🇺🇿", "vn": "🇻🇳", "zh": "🇨🇳",
    }
    VERSION_ICONS = {
        "small": "🔹", "spk": "🔸", "big-lgraph": "💠", "big": "🧊"
    }

    def __init__(self):
        super().__init__()
        self.device = None
        # Initialize components
        self.input = InputManager()
        self.speech: Optional[SpeechRecognizer] = None
        self.menu = self._create_menu()
        logging.debug('AIKeyboard.__init__(): menu initialization complete')
        self.setContextMenu(self.menu)
        self.is_listening = False
        self._current_worker: Optional[SpeechWorker] = None
        self.activated.connect(self._toggle_listening)

        self._init_icon()
        self._init_i18n()
        self._setup_state_handling()
        self.update_state('uninitialized')
        logging.debug('AIKeyboard.__init__(): state initialization complete')
        QTimer.singleShot(0, self._load_config)
        logging.debug('AIKeyboard.__init__(): all done')

    def _init_icon(self):
        icon_path = ":icons/tray_icon.svg"

        # Load base icon
        self.base_icon = QIcon(icon_path)
        if self.base_icon.isNull():
            raise ValueError("Failed to load base icon")

        # Create state icons
        self.state_icons = {
            'uninitialized': self._create_state_icon(QColorConstants.Svg.orangered),
            'idle': self._create_state_icon(QColorConstants.Transparent),
            'listening': self._create_state_icon(QColorConstants.Svg.green),
            'processing': self._create_state_icon(QColorConstants.Svg.yellow)
        }
        self.setIcon(self.state_icons['idle'])

    def _create_menu(self):
        menu = QMenu()
        # Device info (read-only)
        self.device_info = menu.addAction(self.tr("No device selected"))
        self.device_info.setEnabled(True)  # Shows as normal text
        
        # Device selection submenu will be added by main.py
        self.device_menu = menu.addMenu(self.tr("Select Device"))
        # Populate device menu
        for idx, name in device_manager.get_physical_devices():
            action = QAction(f"{idx}: {name[:40]}", self.device_menu)
            action.triggered.connect(lambda _, n=name: self._on_device_selected(n))
            self.device_menu.addAction(action)
        
        menu.addMenu(self._create_model_menu())

        menu.addSeparator()
        menu.addAction(self.tr("Quit"), QCoreApplication.quit)
        return menu

    def _create_model_menu(self):
        try:
            from aikeyboard.model_cache import model_cache
            langs = model_cache.get_languages()
        except Exception as e:
            print(f"Failed to fetch model list: {e}")
            return QMenu(self.tr("Select Model (unavailable)"))

        model_menu = QMenu(self.tr("Select Model"))

        for lang in langs:
            flag = self.LANG_FLAGS.get(lang, "🏳")
            models = model_cache.get_models_for_language(lang)
            if models:
                sub = QMenu(f"{flag} {lang}")
                for model in models:
                    size = model.size
                    icon = self.VERSION_ICONS.get(size, "📦")
                    label = f'{icon} {model.name}'
                    action = QAction(label, sub)
                    action.triggered.connect(lambda _, m=model.name: self._on_model_selected(m))
                    sub.addAction(action)
                model_menu.addMenu(sub)
        return model_menu


    def _init_i18n(self, locale="it_IT"):
        """Initialize translations only for user-facing text"""
        locale = locale or QLocale.system().name()  # e.g., 'it_IT'
        language_code = locale.split("_")[0]        # e.g., 'it'
        self.translator = QTranslator()
        # Load from either:
        # A) File system path (during development)
        # translation_path = QFileInfo(__file__).absoluteDir().filePath("../../i18n/aikeyboard_it.qm")
        
        # OR B) Qt Resources (for deployed apps)
        translation_path = f":i18n/aikeyboard_{language_code}.qm"
        
        if self.translator.load(translation_path):
            QCoreApplication.installTranslator(self.translator)
            print(f"Loaded translation: {language_code}")
        else:
            print(f"Translation not found for {language_code}")

    @Slot(QSystemTrayIcon.ActivationReason)
    def _toggle_listening(self, reason):
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return
        logging.info(f'AIKeyboardApp._togglelistening({self.is_listening}): called')
        if not self.speech or not self.device:
            return

        if not getattr(self, 'is_listening', False):
            self.speech.listen()
            self.is_listening = True
        else:
            self.speech.pause()
            self.is_listening = False

        # self.listen_action.setText(self.tr("Stop listening") if self.is_listening else self.tr("Start listening"))
        self.update_state('listening' if self.is_listening else 'idle')
        logging.info(f'AIKeyboardApp._togglelistening({self.is_listening}): at exit')



    def show_notification(self, message):
        """Show translated notification"""
        self.showMessage(
            self.tr("AI Keyboard"),
            message,
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _create_state_icon(self, bg_color):
        """Create icon with colored background"""
        # Get base pixmap (64x64 is standard for tray icons)
        pixmap = self.base_icon.pixmap(64, 64)
        
        # Only paint if we have a color
        if bg_color != QColorConstants.Transparent:
            painter = QPainter(pixmap)
            if painter.isActive():
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOver)
                painter.fillRect(pixmap.rect(), bg_color)
                painter.end()
            else:
                logging.error("Failed to activate painter")
                
        return QIcon(pixmap)
        
    def update_state(self, state):
        """Update icon and translated tooltip"""
        self.setIcon(self.state_icons.get(state, self.state_icons['idle']))
        self.setToolTip(self.tr("AI Keyboard (%1)").replace('%1', state.capitalize()))
        logging.debug(f'update_state({state}):')


    def _setup_state_handling(self):
        """Connect all state-related signals"""
        self.state_connections = []

    def _load_config(self):
        """Load saved device index"""
        device = app_config.audio_device
        logging.debug(f'AIKeyboard._load_config(): device is "{device}"')
        if device is not None:
            self._on_device_selected(device)
            
    def _on_device_selected(self, name):
        logging.info(f"Selected audio device: {name}")
        app_config.audio_device = name
        index = device_manager.get_device_index(name)
        if not name or index < 0:
            logging.warning(f'Inconsistent selected device {index}: "{name}", ignoring.')
            self.update_state('uninitialized')
            self.device = None
            return

        # Update UI
        self.update_state('idle')
        self.device_info.setText(self.tr("Using: %1").replace('%1', name))
        self.device = name

        # Reinitialize speech
        if self.speech:
            self.speech.stop()
        self.speech = SpeechRecognizer(device_index=index)
        if self.speech:
            # Connect new speech instance
            self.state_connections.append(
                self.speech.worker_created.connect(self._connect_worker_signals)
            )

    def _on_model_selected(self, model_name: str):
        print(f"Selected Vosk model: {model_name}")
        app_config.model = model_name # type: ignore

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
        self.update_state(state)
        logging.debug(f"State changed to: {state}")
        
    def _on_partial_result(self, text):
        """Handle partial recognition results"""
        self.setToolTip(f"Listening: {text}...")
        
    def _on_speech_error(self, error):
        logging.error(f"Speech recognition error: {error}")
        self.show_notification(f"Error: {error}")
        
    def _on_speech_recognized(self, text):
        logging.info(f"Recognized: {text}")
        self.input.write(text + " ")  # Add space after each phrase


if __name__ == "__main__":
    app = QApplication(sys.argv)
    aik = AIKeyboardApp()
    aik.show()
    sys.exit(app.exec())

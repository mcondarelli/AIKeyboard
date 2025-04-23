# src/aikeyboard/tray.py
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPainter, QColorConstants
from PySide6.QtCore import QCoreApplication, QDir, QFileInfo, QTranslator

import logging


class SystemTray(QSystemTrayIcon):
    def __init__(self, icon_loc = 'assets/icons/tray_icon.svg'):
        super().__init__()
        self.device = None
        self._init_icon(icon_loc)
        self._init_i18n()
        self.menu = self._create_menu()
        self.setContextMenu(self.menu)

    def _init_icon(self, icon_loc):
        file_info = QFileInfo(__file__)
        app_dir = file_info.absoluteDir()  # QDir of tray.py's directory
        icon_path = app_dir.filePath("../" + icon_loc)  # QDir handles ".." correctly
        logging.info(f'SystemTray.__init__(): {app_dir} -> {icon_path}')

        # Verify the path exists (optional but recommended)
        if not QFileInfo(icon_path).exists():
            # try loading from application path:
            app_dir = QDir(QCoreApplication.applicationDirPath())  # Root of the executable
            icon_path = app_dir.absoluteFilePath("src/aikeyboard/"+icon_loc)
            if not QFileInfo(icon_path).exists():
                raise FileNotFoundError(f"Icon not found at: {icon_path}")
        logging.info(f'SystemTray.__init__(): Loading icon from {icon_path}')


        # Load base icon
        self.base_icon = QIcon(icon_path)
        if self.base_icon.isNull():
            raise ValueError("Failed to load base icon")

        # Create state icons
        self.state_icons = {
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
        
        menu.addSeparator()
        # Listening toggle will be managed by main.py
        self.listen_action = menu.addAction(self.tr("Start listening"))
        
        menu.addSeparator()
        menu.addAction(self.tr("Quit"), QCoreApplication.quit)
        return menu

    def _init_i18n(self):
        """Initialize translations only for user-facing text"""
        self.translator = QTranslator()
        # Load from either:
        # A) File system path (during development)
        translation_path = QFileInfo(__file__).absoluteDir().filePath("../../i18n/aikeyboard_it.qm")
        
        # OR B) Qt Resources (for deployed apps)
        # translation_path = ":/i18n/aikeyboard_it.qm"
        
        if self.translator.load(translation_path):
            QCoreApplication.installTranslator(self.translator)
        else:
            logging.warning("Failed to load translation")
            
    def _find_icon_path(self, icon_loc):
        """Existing working implementation"""
        file_info = QFileInfo(__file__)
        app_dir = file_info.absoluteDir()
        icon_path = app_dir.filePath("../" + icon_loc)
        
        if not QFileInfo(icon_path).exists():
            app_dir = QDir(QCoreApplication.applicationDirPath())
            icon_path = app_dir.absoluteFilePath("src/aikeyboard/"+icon_loc)
            if not QFileInfo(icon_path).exists():
                raise FileNotFoundError(f"Icon not found at: {icon_path}")
        return icon_path
        
    def _setup_menu(self):
        """Initialize menu with i18n strings"""
        # Device status (non-clickable)
        self.device_status = self.menu.addAction(self.tr("No device selected"))
        self.device_status.setEnabled(False)
        
        # Start/Stop listening (initially disabled)
        self.listen_action = self.menu.addAction(self.tr("Start listening"))
        self.listen_action.setEnabled(self._has_input_device())
        
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Quit"), QCoreApplication.quit)

    def _has_input_device(self):
        """Check settings for valid device"""
        return bool(self.device)
        
    def add_menu_item(self, text, callback):
        action = self.menu.addAction(text)
        action.triggered.connect(callback)
        return action
        
    def add_submenu(self, text):
        submenu = QMenu(text)
        self.menu.addMenu(submenu)
        return submenu

    def update_device_status(self, device_name=None):
        """Update device status with i18n"""
        self.device = device_name
        if self.device:
            self.device_status.setText(self.tr("Using: %1", str(self.device)))
            self.listen_action.setEnabled(True)
        else:
            self.device_status.setText(self.tr("No device selected"))
            self.listen_action.setEnabled(False)
            
    def set_listening_state(self, listening):
        """Toggle listening text with i18n"""
        self.listen_action.setText(self.tr("Stop listening") if listening else self.tr("Start listening"))
    
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
        self.setToolTip(self.tr("AI Keyboard (%1)", state.capitalize()))

# src/aikeyboard/tray.py
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPainter, QColorConstants
from PySide6.QtCore import QCoreApplication, QDir, QFileInfo

import logging


class SystemTray(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        icon_loc = 'assets/icons/tray_icon.svg'

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

        # Create state icons
        self.state_icons = {
            'idle': self._create_state_icon(QColorConstants.Transparent),
            'listening': self._create_state_icon(QColorConstants.Svg.green),
            'processing': self._create_state_icon(QColorConstants.Svg.yellow)
        }
        self.setIcon(self.state_icons['idle'])        
        self.menu = QMenu()
        self.setContextMenu(self.menu)
        
    def add_menu_item(self, text, callback):
        action = self.menu.addAction(text)
        action.triggered.connect(callback)
        return action
        
    def add_submenu(self, text):
        submenu = QMenu(text)
        self.menu.addMenu(submenu)
        return submenu

    def _create_state_icon(self, bg_color):
        """Create icon with colored background"""
        pixmap = self.icon().pixmap(64, 64)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOver)
        painter.fillRect(pixmap.rect(), bg_color)
        painter.end()
        return QIcon(pixmap)
        
    def update_state(self, state):
        """Update icon based on state"""
        self.setIcon(self.state_icons.get(state, self.state_icons['idle']))
        self.setToolTip(f"AI Keyboard ({state.capitalize()})")
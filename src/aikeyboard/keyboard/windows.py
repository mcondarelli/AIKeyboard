# src/aikeyboard/keyboard/windows.py
import keyboard  # pip install keyboard

class WindowsInput:
    def write(self, text):
        keyboard.write(text)
        
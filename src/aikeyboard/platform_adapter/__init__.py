import platform


class PlatformManager:
    def __init__(self):
        system = platform.system()
        if system == "Windows":
            from aikeyboard.platform_adapter.windows import WindowsAdapter
            self.impl = WindowsAdapter()
        elif system == "Linux":
            from aikeyboard.platform_adapter.linux import LinuxAdapter
            self.impl = LinuxAdapter()
        elif system == "Darwin":
            from aikeyboard.platform_adapter.macos import MacAdapter
            self.impl = MacAdapter()
        else:
            raise OSError(f"Unsupported system: {system}")

    def set_font(self, app):
        self.impl.set_font(app)

    def write(self, text):
        self.impl.write(text)

platform_adapter = PlatformManager()

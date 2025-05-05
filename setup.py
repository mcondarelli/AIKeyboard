# setup.py
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py as _build_py
import subprocess
import os


class build_py(_build_py):
    def run(self):
        # Compile resources before the normal build
        print("Generating Qt resources...")
        rcc_cmd = [
            os.path.join(os.getcwd(), ".venv/bin/pyside6-rcc"),
            "resources/resources.qrc",
            "-o", "src/aikeyboard/resources.py"
        ]
        subprocess.check_call(rcc_cmd)
        super().run()


setup(
    name="aikeyboard",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    cmdclass={
        'build_py': build_py,
    },
)

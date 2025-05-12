# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Linux-specific setup
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt install libevdev2
    sudo usermod -a -G input $USER
    echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-input.rules
    sudo udevadm control --reload-rules
    echo "Please log out and back in for changes to take effect"
fi

# Run the application
python -m src.aikeyboard.main

#!/bin/bash
echo "🔧 Installing GUI dependencies for Translation Monitor..."

# Update package list
echo "📦 Updating package list..."
apt-get update

# Install tkinter and GUI dependencies
echo "🖥️ Installing tkinter and GUI libraries..."
apt-get install -y python3-tk python3-dev

# Install Python packages
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Test tkinter installation
echo "🧪 Testing tkinter installation..."
python3 -c "import tkinter; print('✅ tkinter is available')" || {
    echo "❌ tkinter installation failed"
    exit 1
}

echo "🎉 GUI dependencies installed successfully!"
echo ""
echo "📋 You can now run:"
echo "   python3 demo_gui.py        # Run demo with sample data"
echo "   python3 translation_monitor_gui.py  # Run GUI directly"
#!/bin/bash

# Script để copy các files đã update vào project thực
TARGET_DIR="/home/datdang/working/ai-translation-with-style"

echo "🔄 Copying updated files to $TARGET_DIR..."

# Copy service files
echo "📁 Copying service files..."
cp -v /workspace/services/config/preset_loader.py "$TARGET_DIR/services/config/"
cp -v /workspace/services/config/configuration_manager.py "$TARGET_DIR/services/config/"
cp -v /workspace/services/providers/openrouter_client.py "$TARGET_DIR/services/providers/"
cp -v /workspace/services/config/service_factory.py "$TARGET_DIR/services/config/"
cp -v /workspace/services/config/__init__.py "$TARGET_DIR/services/config/"

# Copy config files
echo "📁 Copying config files..."
cp -v /workspace/config/translation.yaml "$TARGET_DIR/config/"
cp -v /workspace/config/preset_translation.json "$TARGET_DIR/config/"

# Copy updated script
echo "📁 Copying run script..."
cp -v /workspace/run_batch.py "$TARGET_DIR/"

# Copy cache service if missing
if [ ! -f "$TARGET_DIR/services/infrastructure/cache_service.py" ]; then
    echo "📁 Copying missing cache_service.py..."
    cp -v /workspace/services/infrastructure/cache_service.py "$TARGET_DIR/services/infrastructure/"
fi

echo "✅ All files copied successfully!"
echo ""
echo "📋 Summary of changes:"
echo "  - Updated ConfigurationManager to support preset loading"
echo "  - Added PresetLoader for JSON preset management"
echo "  - Updated OpenRouterClient to use preset configurations"
echo "  - Updated ServiceFactory to inject presets into providers"
echo "  - Updated run_batch.py to use YAML config instead of JSON"
echo "  - Added cache_service.py if missing"
echo ""
echo "🚀 You can now run: python3 run_batch.py"
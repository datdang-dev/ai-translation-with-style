# 🔄 Update Guide - Cấu trúc mới với Preset JSON

## ❌ Vấn đề hiện tại:
Script `run_batch.py` đang load file JSON cũ thiếu providers config thay vì file YAML đầy đủ.

## ✅ Solution: Copy các files sau

### 1. Service Files (Updated)
```bash
# Copy vào ~/working/ai-translation-with-style/services/config/
```
- **preset_loader.py** (MỚI) - Quản lý preset JSON
- **configuration_manager.py** (UPDATED) - Thêm preset support  
- **service_factory.py** (UPDATED) - Inject preset vào providers
- **__init__.py** (UPDATED) - Export PresetLoader

```bash
# Copy vào ~/working/ai-translation-with-style/services/providers/
```
- **openrouter_client.py** (UPDATED) - Sử dụng preset config

```bash
# Copy vào ~/working/ai-translation-with-style/services/infrastructure/
```
- **cache_service.py** (MỚI nếu thiếu) - Cache service implementation

### 2. Config Files
```bash
# Copy vào ~/working/ai-translation-with-style/config/
```
- **translation.yaml** (UPDATED) - Main config với provider settings
- **preset_translation.json** (MỚI) - Preset với messages & parameters

### 3. Script File
```bash
# Copy vào ~/working/ai-translation-with-style/
```
- **run_batch.py** (UPDATED) - Đổi từ JSON sang YAML config

## 🚀 Commands để copy:

```bash
# Change to your project directory
cd ~/working/ai-translation-with-style

# Copy service files
cp /workspace/services/config/preset_loader.py services/config/
cp /workspace/services/config/configuration_manager.py services/config/
cp /workspace/services/config/service_factory.py services/config/
cp /workspace/services/config/__init__.py services/config/
cp /workspace/services/providers/openrouter_client.py services/providers/
cp /workspace/services/infrastructure/cache_service.py services/infrastructure/

# Copy config files
cp /workspace/config/translation.yaml config/
cp /workspace/config/preset_translation.json config/

# Copy updated script
cp /workspace/run_batch.py .
```

## 📋 Kiểm tra sau khi copy:

1. **Check files exist:**
```bash
ls -la services/config/preset_loader.py
ls -la config/translation.yaml  
ls -la config/preset_translation.json
```

2. **Test load config:**
```bash
python3 -c "
from services.config.configuration_manager import ConfigurationManager
config = ConfigurationManager('config/translation.yaml')
print('✅ Config loaded:', config.validate_config())
print('✅ Presets:', config.list_available_presets())
"
```

3. **Run batch:**
```bash
python3 run_batch.py
```

## 📊 Expected Results:
- ✅ Config loads from YAML (not JSON)
- ✅ Preset loaded: "preset_translation"  
- ✅ Providers registered: 2 providers
- ✅ No "Missing required configuration section" errors

## 🔧 Troubleshooting:

**If you see "Missing required configuration section":**
- ❌ Script vẫn đang load JSON cũ 
- ✅ Đảm bảo `run_batch.py` đã được update để dùng `translation.yaml`

**If you see "No providers available":**
- ❌ OpenRouter thiếu API key
- ✅ Thêm API key vào `config/api_keys.json` hoặc disable OpenRouter

**If you see import errors:**
- ❌ Thiếu files
- ✅ Đảm bảo tất cả files đã được copy đúng vị trí
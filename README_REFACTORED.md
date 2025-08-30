# 🏗️ Refactored Translation Framework

## Overview

This is a **refactored version** of the translation framework that implements a clean, modular architecture following SOLID principles and design patterns. The new architecture provides better separation of concerns, improved maintainability, and enhanced extensibility.

## 🎯 Architecture Goals

### ✅ **Modularity & Clean Separation of Concerns**
- Isolated core translation logic from presentation layers
- Minimal layer boundaries to avoid over-engineering
- Clear separation between Applet, Middleware, and Services

### ✅ **Robust Extensibility Framework**
- Plugin/adapter pattern for translation providers
- Simple standardized interfaces
- Runtime provider selection with minimal boilerplate

### ✅ **Centralized Configuration Management**
- YAML configuration files
- Lightweight validation & fallback
- Zero hardcoded values in core logic

### ✅ **High-Performance Asynchronous Processing**
- Async/await for translation operations
- Timer-based job scheduling (not dependent on completion)
- Adaptive concurrency control

### ✅ **Production-Ready Observability**
- Structured logging throughout the system
- Comprehensive error handling
- System health monitoring

### ✅ **Enterprise-Grade Testability**
- Testable core components
- Simple dependency injection
- Mock-friendly interfaces

### ✅ **SOLID Principles & Design Excellence**
- Applied pragmatically, not dogmatically
- Strategy/Factory patterns where they reduce complexity

## 🏛️ Architecture Structure

```
Application (start_refactored.py)
    ↓
Applet (TranslationApplet)
    ↓
Middleware (CoreManager)
    ↓
Services (Grouped by Function)
```

### **Application Layer**
- **`start_refactored.py`** - Entry point and configuration loading
- Job scheduling orchestration
- User interface and result display

### **Applet Layer**
- **`TranslationApplet`** - Single component handling all translation logic
- Batch and single file translation
- Integration with middleware services

### **Middleware Layer**
- **`CoreManager`** - Single entry point for all middleware operations
- Orchestrates infrastructure and translation services
- Provides clean API for applets

### **Services Layer**

#### **Infrastructure Services** (`services/infrastructure/`)
- **`ConfigManager`** - YAML configuration management
- **`KeyManager`** - API key rotation and rate limiting
- **`JobScheduler`** - Timer-based job scheduling

#### **Translation Services** (`services/translation/`)
- **`RequestManager`** - API request orchestration
- **`Validator`** - Response validation with strategy pattern
- **`Standardizer`** - Input format conversion interface

#### **Common Services** (`services/common/`)
- **`APIClient`** - HTTP client abstraction
- **`Logger`** - Structured logging
- **`ErrorCodes`** - Error definitions

## 🚀 Key Features

### **1. Timer-Based Job Scheduling**
- Jobs run every 10 seconds regardless of completion
- Independent execution (not waiting for previous job)
- Configurable intervals per job

### **2. Input Standardization**
- **JSON Standardizer** - Handles JSON input files
- **Text Standardizer** - Handles plain text input
- **File Standardizer** - Auto-detects format from files
- Configurable auto-conversion

### **3. Response Validation**
- **Strategy Pattern** for different validation types
- **JSON Validation Strategy** with strict mode
- Extensible validation framework
- Clean error messages

### **4. Configuration Management**
- **YAML configuration** for system settings
- **JSON prompts** for AI instructions
- Environment-specific configurations
- Hot-reload capability

## 📁 File Structure

```
├── applet/
│   ├── __init__.py
│   └── translation_applet.py          # Single translation component
├── middleware/
│   ├── __init__.py
│   └── core_manager.py                # Single entry point
├── services/
│   ├── __init__.py
│   ├── infrastructure/                # System-level services
│   │   ├── __init__.py
│   │   ├── config_manager.py
│   │   ├── key_manager.py
│   │   └── job_scheduler.py
│   ├── translation/                   # Translation-specific services
│   │   ├── __init__.py
│   │   ├── request_manager.py
│   │   ├── validator.py
│   │   └── standardizer.py
│   └── common/                        # Shared utilities
│       ├── __init__.py
│       ├── api_client.py
│       ├── logger.py
│       └── error_codes.py
├── config/
│   ├── config.yaml                    # YAML configuration
│   ├── prompts.json                   # AI prompts
│   └── api_keys.json                  # API keys
├── start_refactored.py                # New refactored application
└── requirements.txt                    # Dependencies
```

## 🛠️ Installation & Setup

### **1. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **2. Configure API Keys**
Create `config/api_keys.json`:
```json
{
  "api_keys": [
    "your-api-key-1",
    "your-api-key-2"
  ]
}
```

### **3. Customize Configuration**
Edit `config/config.yaml`:
```yaml
api:
  url: "https://openrouter.ai/api/v1/chat/completions"
  max_retries: 3
  backoff_base: 2.0
  max_requests_per_minute: 20

translation:
  model: "google/gemini-2.0-flash-exp:free"
  temperature: 1

scheduling:
  job_delay: 10.0
  max_concurrent: 100
```

### **4. Customize Prompts**
Edit `config/prompts.json`:
```json
{
  "system_message": "You are a specialized translator...",
  "format_rules": "## FORMAT RULES...",
  "style_rules": "## STYLE RULES...",
  "translation_flow": "## TRANSLATION FLOW..."
}
```

## 🚀 Usage

### **Run the Refactored Application**
```bash
python start_refactored.py
```

### **Programmatic Usage**
```python
from applet import TranslationApplet

# Initialize applet
applet = TranslationApplet("config/config.yaml")

# Batch translation
summary = await applet.translate_batch_from_directory(
    input_dir="playground",
    output_dir="playground/batch_output",
    pattern="chunk_*.json"
)

# Single file translation
result = await applet.translate_single_file(
    input_path="input.json",
    output_path="output.json"
)

# Direct text translation
translated = await applet.translate_text({"0": "Hello world"})
```

## 🔧 Configuration Options

### **API Configuration**
- `url`: API endpoint URL
- `max_retries`: Maximum retry attempts
- `backoff_base`: Exponential backoff base
- `max_requests_per_minute`: Rate limit per key

### **Translation Configuration**
- `model`: AI model to use
- `temperature`: Response randomness
- `presence_penalty`: Penalty for repetition
- `frequency_penalty`: Penalty for frequency

### **Scheduling Configuration**
- `job_delay`: Default interval between jobs (seconds)
- `max_concurrent`: Maximum concurrent jobs

### **Validation Configuration**
- `strict_json`: Enforce strict JSON validation
- `allow_partial`: Allow partial responses

### **Standardization Configuration**
- `default_format`: Default input format
- `auto_convert`: Automatically convert input formats

## 🧪 Testing

### **Run Tests**
```bash
pytest services/ -v
```

### **Test Coverage**
```bash
pytest services/ --cov=services --cov-report=html
```

## 🔍 Monitoring & Debugging

### **System Status**
```python
# Get comprehensive system status
status = applet.get_system_status()
print(f"Active API keys: {status['key_manager']['active_keys']}")
print(f"Scheduler running: {status['scheduler']['is_running']}")
```

### **Health Check**
```python
# Perform system health check
healthy = await applet.health_check()
if healthy:
    print("✅ System is healthy")
else:
    print("❌ System has issues")
```

### **Logging**
The system uses structured logging throughout:
- **INFO**: Normal operations
- **WARNING**: Non-critical issues
- **ERROR**: Critical errors
- **DEBUG**: Detailed debugging information

## 🚀 Migration from Old Architecture

### **Key Changes**
1. **Configuration**: JSON → YAML + JSON prompts
2. **Architecture**: Monolithic → Layered with middleware
3. **Scheduling**: Completion-based → Timer-based
4. **Validation**: Basic → Strategy pattern
5. **Standardization**: Fixed → Extensible interface

### **Benefits**
- **Better separation of concerns**
- **Easier to test and maintain**
- **More extensible and configurable**
- **Cleaner error handling**
- **Better logging and monitoring**

## 🤝 Contributing

### **Adding New Standardizers**
```python
from services.translation import StandardizationInterface

class CustomStandardizer(StandardizationInterface):
    def can_handle(self, input_data):
        # Your logic here
        pass
    
    def standardize(self, input_data):
        # Your logic here
        pass
    
    def get_format_name(self):
        return "Custom"
```

### **Adding New Validation Strategies**
```python
from services.translation import ValidationStrategy

class CustomValidationStrategy(ValidationStrategy):
    def validate(self, response):
        # Your validation logic here
        pass
```

## 📊 Performance Characteristics

- **Timer-based scheduling**: Predictable execution intervals
- **Async/await**: Non-blocking operations
- **Key rotation**: Automatic API key management
- **Rate limiting**: Built-in protection against API limits
- **Concurrent processing**: Multiple jobs can run simultaneously

## 🔒 Security Features

- **API key rotation**: Automatic key switching
- **Rate limiting**: Protection against API abuse
- **Error handling**: Secure error reporting
- **Configuration validation**: Input sanitization

## 🎯 Future Enhancements

- **Plugin system** for custom standardizers
- **Web dashboard** for monitoring
- **Metrics collection** and analytics
- **Distributed processing** support
- **Custom validation rules** engine

---

## 📝 License

This project is licensed under the same terms as the original framework.

## 🆘 Support

For issues and questions:
1. Check the configuration files
2. Review the logs for error details
3. Verify API keys are valid
4. Ensure input files are in the correct format
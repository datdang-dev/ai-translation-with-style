# 🚀 Getting Started with Your API Keys

## TL;DR - Quick Setup

```bash
# 1. Install dependencies
pip install aiohttp

# 2. Setup API keys
python3 setup_api_keys.py

# 3. Run production translation
python3 production_orchestrator.py
```

---

## 📋 Step-by-Step Setup

### 1. Install Required Dependencies

```bash
# Option A: Regular pip
pip install aiohttp

# Option B: User install (if pip restricted)
python3 -m pip install --user aiohttp

# Option C: With system packages (Ubuntu/Debian)
sudo apt install python3-aiohttp
```

### 2. Get OpenRouter API Keys

1. **Visit**: https://openrouter.ai/keys
2. **Sign up** for an account (free)
3. **Generate API keys** (starts with `sk-or-v1-`)
4. **Add credits** to your account for API usage

### 3. Configure API Keys

#### Option A: Interactive Setup (Recommended)
```bash
python3 setup_api_keys.py
```

This will:
- ✅ Guide you through entering API keys
- ✅ Validate key format
- ✅ Save securely to `config/api_keys.json`
- ✅ Add to `.gitignore` automatically

#### Option B: Manual Setup
```bash
# Copy template
cp config/api_keys.json.template config/api_keys.json

# Edit with your keys
nano config/api_keys.json
```

**Example content:**
```json
{
  "api_keys": [
    "sk-or-v1-your-actual-api-key-here"
  ]
}
```

### 4. Test Your Setup

#### Single Translation Test
```bash
python3 production_orchestrator.py
```

Expected output:
```
🚀 Production Translation Service
✅ Using real OpenRouter API client
📝 Testing with 3 sample texts...
1. Translating: 'Hello, how are you today?'
   ✅ Result: Xin chào, hôm nay bạn thế nào?
   📊 Tokens: 150 total
```

#### Batch Translation Test
```bash
python3 batch_production.py
```

---

## 🎯 Usage Examples

### Single Text Translation

```python
import asyncio
from production_orchestrator import ProductionTranslationOrchestrator

async def translate_example():
    orchestrator = ProductionTranslationOrchestrator("config/production_config.json")
    
    result = await orchestrator.translate_text("Hello world!")
    
    if result.success:
        print(f"Translation: {result.data['translated_text']}")
        print(f"Tokens used: {result.data['usage']['total_tokens']}")
    else:
        print(f"Error: {result.error_message}")

# Run it
asyncio.run(translate_example())
```

### Batch File Translation

Place your JSON files in the `playground/` directory:

**File: `playground/my_text.json`**
```json
{
  "id": "text_001",
  "text": "Hello, this is a test message for translation.",
  "metadata": {
    "source": "user_input"
  }
}
```

Run batch translation:
```bash
python3 batch_production.py
```

Results will be saved to `playground/production_output/`

---

## ⚙️ Configuration Options

### Model Selection

Edit `config/production_config.json`:

```json
{
  "model": "anthropic/claude-3.5-sonnet"
}
```

**Available models:**
- `anthropic/claude-3.5-sonnet` - High quality (recommended)
- `anthropic/claude-3-haiku` - Fast and cheap
- `openai/gpt-4o` - OpenAI alternative
- `meta-llama/llama-3.1-70b-instruct` - Open source option

### Rate Limiting

```json
{
  "max_requests_per_minute": 20,
  "batch": {
    "max_concurrent": 2,
    "job_delay": 2.0
  }
}
```

- `max_requests_per_minute`: Requests per API key
- `max_concurrent`: Parallel requests
- `job_delay`: Seconds between requests

---

## 💰 Cost Management

### Token Usage
- **Haiku**: ~$0.25 per 1M input tokens
- **Sonnet**: ~$3.00 per 1M input tokens
- **Typical translation**: 100-300 tokens

### Monitor Costs
```bash
# Check token usage after batch processing
python3 -c "
import json
with open('playground/production_output/batch_summary.json') as f:
    data = json.load(f)
    print(f'Total tokens: {data[\"total_tokens_used\"]:,}')
    print(f'Estimated cost: \${data[\"estimated_cost_usd\"]:.4f}')
"
```

---

## 🛡️ Built-in Resilience Features

Your refactored architecture includes:

✅ **API Key Rotation** - Automatically switches when rate limited  
✅ **Circuit Breaker** - Prevents cascade failures  
✅ **Exponential Backoff** - Smart retry with jitter  
✅ **Quota Tracking** - Respects rate limits  
✅ **Health Monitoring** - Real-time system status  
✅ **Comprehensive Metrics** - Request success rates, token usage  

---

## 🔧 Troubleshooting

### "aiohttp not found"
```bash
pip install aiohttp
```

### "No valid API keys"
```bash
python3 setup_api_keys.py
```

### Rate limiting issues
1. Reduce `max_concurrent` in config
2. Increase `job_delay`
3. Add more API keys

### Check API key balance
Visit: https://openrouter.ai/account

---

## 📊 Monitoring Your Usage

### Real-time Status
```python
status = await orchestrator.get_detailed_status()
print(f"Success rate: {status['performance']['success_rate_percent']}%")
print(f"Active keys: {status['key_management']['summary']['active_keys']}")
```

### View Metrics
```bash
# Run with detailed logging
python3 production_orchestrator.py 2>&1 | grep -E "(SUCCESS|ERROR|TOKEN)"
```

---

## 🎉 You're Ready!

Your refactored translation service now provides:

- **Production-ready** API integration
- **Automatic resilience** and error handling  
- **Real-time monitoring** and metrics
- **Cost optimization** features
- **Scalable architecture** for future growth

Start translating with confidence! 🌟

---

## 📞 Need Help?

1. **Check logs** for error details
2. **Verify API keys** at OpenRouter
3. **Test configuration** with mock client first
4. **Monitor token usage** to control costs

Happy translating! 🚀
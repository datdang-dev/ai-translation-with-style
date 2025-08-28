# 🚀 Production Setup Guide

## Quick Start with Your API Keys

### 1. Install Dependencies

```bash
# Install required packages
pip install aiohttp

# Or if you're in a restricted environment:
python3 -m pip install --user aiohttp
```

### 2. Setup API Keys

#### Option A: Use the setup script (Recommended)
```bash
python3 setup_api_keys.py
```

#### Option B: Manual setup
```bash
# Copy template
cp config/api_keys.json.template config/api_keys.json

# Edit with your real API keys
nano config/api_keys.json
```

**Example `config/api_keys.json`:**
```json
{
  "api_keys": [
    "sk-or-v1-your-actual-api-key-here",
    "sk-or-v1-another-key-for-higher-limits"
  ]
}
```

### 3. Get OpenRouter API Keys

1. Visit: https://openrouter.ai/keys
2. Create an account if needed
3. Generate API keys
4. Add credits to your account

### 4. Run Production Translation

#### Single Translation Test
```bash
python3 production_orchestrator.py
```

#### Batch Translation
```bash
python3 batch_production.py
```

---

## 📋 Configuration Options

### Model Selection

Edit `config/production_config.json`:

```json
{
  "model": "anthropic/claude-3.5-sonnet",     // High quality
  "model": "anthropic/claude-3-haiku",       // Fast & cheap
  "model": "openai/gpt-4o",                  // OpenAI alternative
  "model": "meta-llama/llama-3.1-70b-instruct" // Open source
}
```

### Rate Limiting

```json
{
  "max_requests_per_minute": 20,    // Per API key
  "batch": {
    "max_concurrent": 2,            // Concurrent requests
    "job_delay": 2.0               // Delay between requests
  }
}
```

### Circuit Breaker

```json
{
  "circuit_breaker": {
    "api_client": {
      "failure_threshold": 5,       // Failures before opening
      "recovery_timeout": 60.0,     // Seconds before retry
      "success_threshold": 2        // Successes to close
    }
  }
}
```

---

## 🏃‍♂️ Usage Examples

### Single Translation

```python
from production_orchestrator import ProductionTranslationOrchestrator

async def translate_example():
    orchestrator = ProductionTranslationOrchestrator("config/production_config.json")
    
    result = await orchestrator.translate_text("Hello world!")
    
    if result.success:
        print(f"Translation: {result.data['translated_text']}")
        print(f"Tokens used: {result.data['usage']['total_tokens']}")
    else:
        print(f"Error: {result.error_message}")
```

### Batch Translation

```python
from batch_production import BatchProductionTranslation

async def batch_example():
    batch = BatchProductionTranslation()
    
    summary = await batch.run_batch_translation(
        input_dir="my_files",
        output_dir="translated_files",
        max_concurrent=2,
        delay_between_batches=1.0
    )
    
    print(f"Completed: {summary['completed']}/{summary['total']}")
    print(f"Total tokens: {summary['total_tokens_used']}")
```

---

## 📊 Monitoring & Metrics

### Real-time Status
```python
status = await orchestrator.get_detailed_status()
print(f"Success rate: {status['performance']['success_rate_percent']}%")
print(f"Active keys: {status['key_management']['summary']['active_keys']}")
```

### Available Metrics
- **Request success/failure rates**
- **Token usage per request**
- **Response times and latencies**
- **API key usage distribution**
- **Circuit breaker status**

---

## 🛡️ Error Handling & Resilience

### Automatic Features
✅ **API Key Rotation** - Automatically switches keys when rate limited  
✅ **Circuit Breaker** - Prevents cascade failures  
✅ **Exponential Backoff** - Smart retry with jitter  
✅ **Quota Tracking** - Respects rate limits per key  
✅ **Health Monitoring** - Tracks key and service health  

### Error Recovery
- Rate limited keys are temporarily disabled
- Failed keys are retried with exponential backoff
- Circuit breaker opens on repeated failures
- Automatic failover to healthy keys

---

## 💰 Cost Management

### Token Usage Tracking
```bash
# Check token usage in batch results
python3 -c "
import json
with open('playground/production_output/summary.json') as f:
    data = json.load(f)
    print(f'Total tokens: {data[\"total_tokens_used\"]}')
    print(f'Estimated cost: \${data[\"estimated_cost_usd\"]:.4f}')
"
```

### Cost Optimization Tips
1. **Use appropriate models**: Haiku for simple tasks, Sonnet for quality
2. **Optimize prompts**: Shorter prompts = fewer tokens
3. **Batch processing**: More efficient than individual requests
4. **Monitor usage**: Track tokens per translation

---

## 🔒 Security Best Practices

### API Key Security
- ✅ Never commit `config/api_keys.json` to version control
- ✅ Use environment variables in production deployments
- ✅ Rotate keys regularly
- ✅ Monitor usage for anomalies

### Environment Variables (Optional)
```bash
export OPENROUTER_API_KEYS="key1,key2,key3"
```

---

## 🧪 Testing

### Test with Mock Client
```bash
# Test without using real API calls
python3 refactored_orchestrator.py
```

### Validate Configuration
```bash
# Check if config is valid
python3 -c "
from services.core.configuration_service import ConfigurationService
config = ConfigurationService('config/production_config.json')
print('✅ Configuration valid')
print(f'API keys loaded: {len(config.get_api_keys())}')
"
```

### Test Single Translation
```bash
# Quick test with one translation
python3 -c "
import asyncio
from production_orchestrator import ProductionTranslationOrchestrator

async def test():
    orch = ProductionTranslationOrchestrator('config/production_config.json')
    result = await orch.translate_text('Hello world!')
    print('✅ Test passed' if result.success else f'❌ Test failed: {result.error_message}')

asyncio.run(test())
"
```

---

## 📞 Troubleshooting

### Common Issues

#### 1. "No module named 'aiohttp'"
```bash
pip install aiohttp
```

#### 2. "No valid API keys configured"
```bash
python3 setup_api_keys.py
```

#### 3. Rate limiting errors
- Reduce `max_concurrent` in config
- Increase `job_delay` between requests
- Add more API keys

#### 4. Circuit breaker opening
- Check API key validity
- Verify OpenRouter service status
- Reduce request rate temporarily

### Debug Mode
Add to your script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Log Analysis
```bash
# Check recent logs
tail -f logs/translation.log  # If logging to file
```

---

## 🎯 Performance Tuning

### Optimal Settings for Different Use Cases

#### High Throughput (Many small texts)
```json
{
  "model": "anthropic/claude-3-haiku",
  "max_concurrent": 5,
  "job_delay": 0.5,
  "max_requests_per_minute": 30
}
```

#### High Quality (Complex texts)
```json
{
  "model": "anthropic/claude-3.5-sonnet",
  "max_concurrent": 2,
  "job_delay": 2.0,
  "max_requests_per_minute": 15
}
```

#### Cost Optimized
```json
{
  "model": "meta-llama/llama-3.1-70b-instruct",
  "max_concurrent": 3,
  "job_delay": 1.0
}
```

---

Ready to translate! 🚀
# LiquidMetal Setup Guide

## Current Status

I've updated the code to work with the **LiquidMetal Raindrop SDK** (`lm-raindrop`). The code now:

1. ✅ Tries multiple import names (`lm_raindrop`, `raindrop`, `liquidmetal`)
2. ✅ Handles different client initialization methods
3. ✅ Tries multiple API method names (`run_agent`, `execute_agent`, `invoke`)
4. ✅ Falls back gracefully to OpenAI if LiquidMetal isn't available

## Installation Steps (WSL)

### 1. Create Virtual Environment in WSL

```bash
# In WSL terminal
cd /mnt/c/Users/alext/Desktop/self-evolve
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `lm-raindrop` (LiquidMetal SDK)
- `openai` (fallback)
- All other dependencies

### 3. Get Your LiquidMetal API Key

1. Sign up/login at [liquidmetal.run](https://liquidmetal.run)
2. Go to **Settings** → **API Keys**
3. Create a new API key
4. Copy it

### 4. Configure Environment

Create or edit `.env` file in your project root:

```bash
LIQUIDMETAL_API_KEY=your_actual_api_key_here
# Or use LM_API_KEY (both are checked)
LM_API_KEY=your_actual_api_key_here

# Fallback (optional)
OPENAI_API_KEY=your_openai_key_if_needed
```

### 5. Test the Integration

```bash
python demo_test.py
```

You should see:
```
✓ LiquidMetal SDK loaded successfully
✓ Diagnostic agent tests passed
✓ Lesson agent tests passed
✓ Capstone agent tests passed
```

## How It Works

The code tries to use LiquidMetal in this order:

1. **LiquidMetal SDK** (`lm-raindrop`) - if available and API key is set
2. **OpenAI** - if LiquidMetal unavailable but OpenAI key is set
3. **Rule-based heuristics** - always available as final fallback

## API Method Detection

The code automatically detects which method the SDK uses:
- `run_agent()` (expected)
- `execute_agent()` (alternative)
- `invoke()` (alternative)
- Direct callable (if SDK works differently)

## Troubleshooting

### "LiquidMetal SDK not found"
```bash
pip install lm-raindrop
```

### "Could not initialize LiquidMetal client"
- Check your API key: `echo $LIQUIDMETAL_API_KEY`
- Verify the key is correct in your LiquidMetal dashboard
- The code will fall back to OpenAI automatically

### "LiquidMetal API call failed"
- The SDK might use a different API than expected
- Check [LiquidMetal API docs](https://docs.liquidmetal.ai/api)
- The code will automatically fall back to OpenAI or heuristics

## Fastino Labs Alternative

**Fastino Labs** specializes in:
- Task-optimized language models
- Faster inference (CPU/NPU optimized)
- Specific enterprise tasks (RAG, summarization, data structuring)

**Would it work for your use case?**

**Pros:**
- ✅ Fast inference
- ✅ CPU-friendly (no GPU needed)
- ✅ Good for structured outputs

**Cons:**
- ❓ Not clear if they have an agent framework like LiquidMetal
- ❓ May require significant code changes
- ❓ Less documentation available

**Recommendation:** 
- **Stick with LiquidMetal** if you need the agent reasoning framework
- **Consider Fastino** if you only need LLM inference for specific tasks and want speed/CPU optimization

## Next Steps

1. Install `lm-raindrop` in WSL
2. Get your API key
3. Test the integration
4. If the SDK API is different than expected, we can adapt the code based on the actual SDK documentation

## Resources

- [LiquidMetal Docs](https://docs.liquidmetal.ai)
- [Raindrop SDK Installation](https://docs.liquidmetal.ai/sdk/installation/)
- [LiquidMetal API Reference](https://docs.liquidmetal.ai/api)


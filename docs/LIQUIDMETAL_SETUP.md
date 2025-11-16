# LiquidMetal AI Integration Guide

This document explains how LearnAI uses LiquidMetal AI for intelligent agent reasoning.

## Overview

LiquidMetal AI is the **primary reasoning engine** for all three intelligent agents in LearnAI:

1. **Diagnostic Agent** - Assesses user knowledge level
2. **Lesson Agent** - Selects and adapts content delivery
3. **Capstone Agent** - Generates custom AI agent code

## Architecture

```
User Input
    ↓
LiquidMetal Agent (Primary)
    ├─ Diagnostic Agent → Assess level
    ├─ Lesson Agent → Select content
    └─ Capstone Agent → Generate code
    ↓
Fallback Chain:
    1. LiquidMetal SDK (if API key provided)
    2. OpenAI (if LiquidMetal unavailable)
    3. Rule-based heuristics (always available)
```

## Setup

### 1. Install LiquidMetal SDK

```bash
pip install liquidmetal
```

This is included in `requirements.txt`.

### 2. Get API Key

Obtain your LiquidMetal API key from:
- [LiquidMetal Dashboard](https://liquidmetal.ai/dashboard)
- Or your LiquidMetal account settings

### 3. Configure Environment

Copy the example env file:
```bash
cp .env.example .env
```

Edit `.env` and add your key:
```bash
LIQUIDMETAL_API_KEY=your_actual_api_key_here
```

### 4. Verify Integration

Run the test suite:
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

## Agent Definitions

LiquidMetal agents are defined in `/agent/*.liquidmetal.md` files:

### Diagnostic Agent (`/agent/diagnostic_agent.liquidmetal.md`)
- Analyzes user responses
- Detects hesitation patterns
- Switches between question modes
- Classifies knowledge level (0-3)

### Lesson Agent (`/agent/lesson_agent.liquidmetal.md`)
- Selects appropriate content module
- Adjusts difficulty based on performance
- Recommends learning style (text/visual/examples)
- Generates check questions

### Capstone Agent (`/agent/capstone_agent.liquidmetal.md`)
- Generates custom Python agent code
- Creates task-specific implementations
- Provides next steps guidance

## How It Works

### 1. Agent Execution Flow

```python
# Example: Diagnostic Agent
runner = LiquidMetalRunner()

result = runner.run_diagnostic_agent({
    "raw_input": "AI learns patterns from data",
    "hesitation_seconds": 5.0
})

# LiquidMetal processes:
# - Loads agent definition from diagnostic_agent.liquidmetal.md
# - Analyzes input using AI reasoning
# - Returns structured output
```

### 2. LiquidMetal API Calls

```python
result = liquidmetal_client.run_agent(
    agent_definition=agent_def,  # From .liquidmetal.md file
    context={                     # Input data
        "user_input": "...",
        "hesitation_seconds": 5.0
    },
    output_schema={               # Expected output format
        "next_mode": str,
        "assessed_level": int,
        "reasoning": str
    }
)
```

### 3. Fallback Behavior

If LiquidMetal is unavailable:

1. **First Fallback**: OpenAI GPT-4
   - Uses similar reasoning approach
   - Requires OPENAI_API_KEY

2. **Second Fallback**: Rule-based heuristics
   - Simple pattern matching
   - No API key required
   - Always available

## Output Schemas

### Diagnostic Agent Output
```python
{
    "next_mode": "open_ended" | "multiple_choice" | "examples_first",
    "assessed_level": 0-3,  # 0=beginner, 3=expert
    "reasoning": "explanation of assessment",
    "question_payload": {...}  # Optional next question
}
```

### Lesson Agent Output
```python
{
    "module_file": "fundamentals.md",
    "difficulty_tag": 0-3,
    "freepik_search": "AI concept diagram",
    "check_questions": ["Q1", "Q2"],
    "suggested_style": "text" | "visual" | "examples",
    "next_module": "transformers_llms"
}
```

### Capstone Agent Output
```python
{
    "agent_code": "# Python code...",
    "agent_description": "A todo agent for...",
    "next_steps": ["Step 1", "Step 2", ...]
}
```

## Self-Evolving Features

LiquidMetal enables self-evolving behavior by:

1. **Analyzing Performance Patterns**
   - Tracks quiz accuracy over time
   - Monitors hesitation patterns
   - Identifies learning style preferences

2. **Adaptive Decision Making**
   - Adjusts difficulty dynamically
   - Switches teaching approaches
   - Personalizes content delivery

3. **Continuous Learning**
   - Stores learning signals in Daft
   - Uses historical data for better decisions
   - Improves recommendations over time

## Troubleshooting

### "LiquidMetal SDK not found"
```bash
pip install liquidmetal
```

### "Authentication failed"
Check your API key:
```bash
echo $LIQUIDMETAL_API_KEY
# Or on Windows:
echo %LIQUIDMETAL_API_KEY%
```

### "Agent execution failed"
The system automatically falls back to OpenAI or heuristics. Check logs:
```
LiquidMetal error: [error message]. Falling back...
```

### Testing Without LiquidMetal
The system works without LiquidMetal using fallbacks:
```bash
# Unset API key to test fallback
unset LIQUIDMETAL_API_KEY
python main.py
```

## Best Practices

1. **Always Define Clear Schemas**
   - Specify expected output types
   - Document all fields

2. **Handle Errors Gracefully**
   - LiquidMetal errors trigger fallbacks
   - System continues working

3. **Monitor Performance**
   - Check `/data/` for learning signals
   - Analyze agent decisions

4. **Update Agent Definitions**
   - Edit `.liquidmetal.md` files as needed
   - Agents automatically load new definitions

## API Rate Limits

Be aware of LiquidMetal API limits:
- Free tier: 100 requests/day
- Pro tier: 10,000 requests/day

The system caches results where possible to minimize API calls.

## Further Reading

- [LiquidMetal Documentation](https://docs.liquidmetal.ai)
- [Agent Definition Format](https://docs.liquidmetal.ai/agents)
- [API Reference](https://docs.liquidmetal.ai/api)

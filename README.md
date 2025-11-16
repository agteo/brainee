# Brainee – Adaptive AI Learning Agent

This project is a working prototype for a self-evolving adaptive learning agent that:
- Diagnoses a learner's understanding of AI through dynamic assessment
- Adapts lessons on Transformers, LLMs, and Agents based on performance
- Automatically adjusts difficulty, pacing, and teaching style
- Guides learners to build their own AI agent as a capstone project
- **Uses LiquidMetal AI for intelligent agent reasoning**
- Uses Daft for structured data storage and learning signals
- Includes visual aids and adaptive content delivery

## Features

### Self-Evolving Adaptive Learning
- **Dynamic Difficulty**: Automatically increases or decreases based on quiz performance
- **Learning Style Adaptation**: Switches between text, examples, and visual approaches
- **Hesitation Detection**: Identifies when learners are stuck and adjusts accordingly
- **Performance Tracking**: Monitors accuracy, response times, and learning patterns

### Modular Content
- AI Fundamentals
- Transformers & Large Language Models
- AI Agents & Reasoning
- Hands-on Capstone: Build Your Own Agent

### Smart Agent System
- **Diagnostic Agent**: Assesses knowledge level and learning preferences
- **Lesson Agent**: Selects and adapts content delivery
- **Capstone Agent**: Generates personalized AI agent code

### Enhanced Personalization (Optional)
- **Fastino Labs Integration**: User memory and context across sessions
- **RAG-Based Retrieval**: Personalized lesson context from learning history
- **Learning Pattern Insights**: Adapts based on user's strengths and struggles

## Quick Start

### Installation

1. Clone or download this repository
2. Install dependencies (includes LiquidMetal AI SDK):

```bash
pip install -r requirements.txt
```

3. Set up API keys:

```bash
cp .env.example .env
# Edit .env and add your API keys:
# - LIQUIDMETAL_API_KEY (required) - Primary agent reasoning engine
# - OPENAI_API_KEY (optional) - Enhanced answer evaluation
# - FREEPIK_API_KEY (optional) - Visual learning aids
# - FASTINO_API_KEY (optional) - Enhanced personalization
```

**Important**: 
- **LiquidMetal AI** is the primary reasoning engine (required). See [LIQUIDMETAL_SETUP.md](LIQUIDMETAL_SETUP.md) for detailed setup instructions.
- **Fastino Labs** provides enhanced personalization with user memory and RAG retrieval (optional). See [FASTINO_SETUP.md](FASTINO_SETUP.md) for details.

**Running on Windows?** If LiquidMetal requires Linux, see [WSL_SETUP.md](WSL_SETUP.md) for running in Windows Subsystem for Linux. The code works without any modifications!

### Running Brainee

**Start the full learning experience:**
```bash
python main.py
```

**Run with a specific user ID:**
```bash
python main.py --user alice
```

**View your progress:**
```bash
python main.py --progress
```

**Reset and start over:**
```bash
python main.py --reset
```

**Run a single lesson:**
```bash
python main.py --lesson-only
```

**Start the web frontend:**
```bash
python app.py
```
Then open `http://localhost:5000` in your browser.

### Testing

**Run the test suite to verify everything works:**
```bash
python demo_test.py
```

This will test all components and confirm your setup is correct.

## How It Works

### Adaptive Learning Flow

1. **Diagnostic Phase**: Assesses your current knowledge level
   - Open-ended questions
   - Automatic fallback to multiple-choice if needed
   - Hesitation detection triggers simplified approaches

2. **Lesson Phase**: Delivers personalized content
   - Adapts difficulty based on quiz performance
   - Switches to examples when you struggle
   - Increases pace when you're doing well

3. **Self-Evolution**: Learns from your learning
   - 2 correct + fast → difficulty increases
   - 2 incorrect or slow → difficulty decreases, more examples
   - Tracks what teaching methods work best for you

4. **Capstone Project**: Build your own AI agent
   - Generate custom agent code based on your goals
   - Save and run your personalized agent

### Architecture

```
main.py              → CLI entry point
learning_engine.py   → Core orchestration logic
cli_interface.py     → Rich terminal UI
integrations/
  ├── state_manager.py         → User progress & adaptation logic
  ├── liquidmetal_runner.py    → Agent reasoning engine
  ├── daft_client.py           → Structured data storage
  ├── freepik_client.py        → Visual assets (Freepik API)
  └── fastino_client.py        → Enhanced personalization (Fastino Labs)
content/
  ├── syllabus/                → Learning modules (markdown)
  └── prompts/                 → Agent prompts & questions
data/                          → User progress & quiz data (JSON)
```

## Project Structure

```
/learning-agent/
  /agent/                      # Agent definitions
    diagnostic_agent.liquidmetal.md
    lesson_agent.liquidmetal.md
    capstone_agent.liquidmetal.md

  /content/
    /syllabus/                 # Learning content (swappable)
      fundamentals.md
      transformers_llms.md
      agents.md
      build_todo_agent.md
    /prompts/                  # Question banks
    /images/                   # Visual assets

  /data/                       # User data (auto-generated)
    user_progress.json
    quiz_attempts.json
    lesson_log.json

  /integrations/               # Core components
    state_manager.py           # Self-evolving logic
    liquidmetal_runner.py      # Agent reasoning
    daft_client.py             # Data storage
    freepik_client.py          # Visual assets
    fastino_client.py          # Enhanced personalization

  main.py                      # Application entry
  learning_engine.py           # Orchestration
  cli_interface.py             # User interface
  demo_test.py                 # Test suite
  requirements.txt             # Dependencies
  README.md                    # This file
  PRD.md                       # Product requirements
```

## Self-Evolving Features

The system implements true adaptive learning:

- **Difficulty Adaptation**: Automatically adjusts from 0 (beginner) to 3 (expert)
- **Style Preferences**: Learns if you prefer text, examples, or visual explanations
- **Pace Adjustment**: Speeds up or slows down based on hesitation patterns
- **Content Selection**: Chooses next module based on mastery signals

All learning signals are stored in `/data/` for analysis and continuous improvement.

## Configuration

### API Keys

**Required:**
- **LiquidMetal AI**: Primary agent reasoning engine (required for core functionality)

**Optional (for enhanced features):**
- **OpenAI**: Enables smarter semantic answer evaluation and diagnostic classification
- **Freepik**: Provides relevant visual learning aids for lessons
- **Fastino Labs**: Enhanced personalization with user memory, RAG retrieval, and learning insights

Set keys in `.env` file (copy from `.env.example`) or as environment variables.

**Note**: The system works with just LiquidMetal API key. Other keys enhance specific features but are not required.

### Custom Content

To add or modify learning modules:

1. Edit files in `/content/syllabus/`
2. Update agent definitions in `/agent/`
3. Restart the application

The system automatically loads new content.

## Troubleshooting

**Import errors:**
```bash
pip install -r requirements.txt
```

**"Module not found" errors:**
Make sure you're running from the project root directory.

**Want to start over:**
```bash
python main.py --reset --user yourname
```

**Check if everything is working:**
```bash
python demo_test.py
```

## Tech Stack

### Backend
- **Python 3.8+** - Core language
- **Flask** - Web framework and REST API
- **LiquidMetal AI SDK** (lm-raindrop) - Primary agent reasoning engine for diagnostic, lesson, and capstone agents
- **Daft** (getdaft) - Structured data storage in Parquet format
- **Pandas** - Data manipulation and analysis
- **Rich** - Beautiful terminal UI for CLI
- **Click** - CLI command interface
- **OpenAI API** (optional) - Semantic answer evaluation and enhanced diagnostics
- **Google Gemini API** (optional) - Image and video generation for visual learning aids
- **Fastino Labs** (optional) - Enhanced personalization with user memory and RAG retrieval

### Frontend
- **HTML/CSS/JavaScript** - Vanilla web frontend
- **Marked.js** - Markdown rendering for lesson content
- **RESTful API** - Communication with Flask backend

### Data Storage
- **JSON** - User progress, quiz attempts, lesson logs
- **Parquet** (via Daft) - Efficient columnar storage for analytics

### External APIs
- **LiquidMetal AI** (required) - Agent reasoning
- **OpenAI** (optional) - Answer evaluation
- **Freepik API** (optional) - Visual learning assets
- **Fastino Labs** (optional) - Personalization and memory
- **Google Gemini** (optional) - Image/video generation

### Architecture
- Modular design with separate integrations for each service
- Self-evolving adaptive learning logic
- State management with JSON persistence
- RESTful API architecture

### Web Frontend

The project includes a modern web frontend! See [WEB_FRONTEND.md](WEB_FRONTEND.md) for details on running the web interface.

## License

This is a hackathon prototype. Feel free to extend and modify!

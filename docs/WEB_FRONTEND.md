# Web Frontend Setup Guide

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the web server:**
   ```bash
   python app.py
   ```

3. **Open your browser:**
   Navigate to `http://localhost:5000`

## Features

### ✅ What's Included

- **Modern Web UI**: Beautiful, responsive interface with dark theme
- **REST API Backend**: Flask-based API that wraps your existing `learning_engine.py`
- **Freepik Image Integration**: 
  - Uses Freepik API if you have an API key (set `FREEPIK_API_KEY` in `.env`)
  - Falls back to Unsplash for placeholder images if no API key
- **Full Learning Flow**:
  - Diagnostic assessment
  - Adaptive lessons with markdown rendering
  - Interactive quiz questions
  - Capstone project generation
  - Progress tracking

### 🎨 Frontend Structure

```
templates/
  └── index.html          # Main frontend page
static/
  ├── css/
  │   └── style.css      # Modern styling
  └── js/
      └── app.js         # Frontend logic
```

### 🔧 Backend API Endpoints

- `GET /` - Serve the frontend
- `POST /api/diagnostic` - Run diagnostic assessment
- `GET /api/lesson` - Get next lesson
- `POST /api/quiz` - Submit quiz answer
- `POST /api/capstone` - Generate capstone project
- `GET /api/progress` - Get user progress
- `POST /api/advance` - Advance to next module
- `POST /api/reset` - Reset user progress
- `GET /api/freepik-image` - Get image for concept

### 🖼️ Freepik Integration

The Freepik client (`integrations/freepik_client.py`) will:

1. **With API Key**: Search Freepik API and return actual image URLs
2. **Without API Key**: Use Unsplash Source API as a free fallback

To use Freepik API:
1. Get a Freepik API key from https://www.freepik.com/api
2. Add to your `.env` file:
   ```
   FREEPIK_API_KEY=your_api_key_here
   ```

### 🚀 Running Both CLI and Web

You can run both interfaces:

- **CLI**: `python main.py` (original terminal interface)
- **Web**: `python app.py` (new web interface)

Both use the same `learning_engine.py` backend, so progress is shared per user ID.

### 📝 Notes

- The web app uses session-based user tracking (defaults to 'web_user')
- All your existing learning engine logic remains unchanged
- The frontend uses modern JavaScript (no build step required)
- Markdown rendering is handled client-side with marked.js
- Code syntax highlighting uses highlight.js


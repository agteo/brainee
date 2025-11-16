# Fastino Labs Integration Guide

Fastino Labs has been integrated into LearnAI to provide enhanced personalization capabilities. This integration works alongside your existing personalization system.

## Features Added

### 1. **User Memory & Context**
- Persistent user memory across sessions
- Automatic registration of new users
- Event ingestion for all learning activities

### 2. **RAG-Based Retrieval**
- Retrieve relevant memories based on queries
- Personalized context for lesson generation
- Learning pattern insights

### 3. **Enhanced Personalization**
- Learning style recommendations from user history
- Struggle detection and personalized responses
- Capstone project personalization

## Setup

### 1. Add API Key

Add your Fastino API key to your `.env` file:

```bash
FASTINO_API_KEY=your_api_key_here
```

Optionally, you can also set a custom API base URL:

```bash
FASTINO_API_BASE=https://api.fastino.ai/v1
```

### 2. Install Dependencies

All required dependencies are already in `requirements.txt`. The integration uses the existing `requests` library.

### 3. Verify Integration

The integration is **optional** - your system works perfectly without it. To verify it's working:

1. Check that `FASTINO_API_KEY` is set in your environment
2. Start using the learning platform
3. Check console logs for any Fastino-related errors (they won't break the system)

## How It Works

### Automatic Event Ingestion

The following events are automatically sent to Fastino:

- **Diagnostic Response**: User's initial assessment
- **Quiz Attempts**: Every quiz answer with performance data
- **Module Completion**: When a user completes a module
- **Capstone Requests**: When generating personalized agents

### Enhanced Features

1. **Learning Style Detection**
   - Fastino queries user history to recommend learning styles
   - Falls back to existing logic if Fastino is unavailable

2. **Personalized Lessons**
   - Retrieves memories about user struggles
   - Provides context to lesson agents for better adaptation

3. **Capstone Personalization**
   - Uses learning profile insights
   - Generates agents tailored to user's strengths

## API Endpoints Used

The integration uses these Fastino API endpoints:

- `PUT /register` - Register new users
- `POST /ingest` - Ingest learning events
- `GET /summary` - Get user summary
- `POST /query` - Query user profile
- `POST /retrieve` - RAG memory retrieval
- `POST /predict` - Decision prediction (available but not yet used)

## Graceful Degradation

The integration is designed to **never break** if Fastino is unavailable:

- ✅ Works without API key (uses existing personalization)
- ✅ Handles API errors gracefully
- ✅ Falls back to existing logic
- ✅ No frontend changes required

## Testing

To test the integration:

1. Set `FASTINO_API_KEY` in your `.env`
2. Run the learning platform
3. Complete a diagnostic and lesson
4. Check Fastino dashboard to see ingested events

## Troubleshooting

**No events appearing in Fastino?**
- Verify API key is correct
- Check network connectivity
- Look for error messages in console (they're logged but don't break the app)

**Integration not working?**
- The system works fine without Fastino
- All existing features continue to work
- Fastino is purely an enhancement layer

## Next Steps

You can extend the integration by:

1. Using `predict_decision()` for learning path recommendations
2. Adding custom event types for specific learning activities
3. Querying user profile for admin dashboards
4. Using summaries for progress reports

## Support

For Fastino API documentation, visit: https://fastino.ai/docs


# Brainee Demo Pitch

## Overview

**Brainee** is a self-evolving adaptive learning agent that teaches AI fundamentals through personalized, dynamically-adjusted lessons. The system diagnoses learner understanding, adapts in real-time, and guides users to build their own AI agent as a capstone project.

## Key Innovation

Unlike static online courses, Brainee **learns from how you learn**—automatically adjusting difficulty, pacing, and teaching style based on your performance patterns, hesitation signals, and learning preferences.

## Technology Stack

### 🧠 **LiquidMetal AI** — Intelligent Agent Reasoning Engine
- **Powers three specialized agents:**
  - **Diagnostic Agent**: Assesses knowledge level through dynamic questioning
  - **Lesson Agent**: Selects content modules and adapts difficulty in real-time
  - **Capstone Agent**: Generates personalized AI agent code based on user goals
- **Real-time decision-making**: Determines when to simplify, speed up, or change teaching approaches
- **Adaptive reasoning**: Analyzes hesitation patterns, error rates, and learning signals to optimize the experience

### 📊 **Daft** — Structured Data Storage & Learning Analytics
- **Efficient columnar storage**: Stores all learning signals in Parquet format for fast querying
- **Tracks comprehensive learning data:**
  - Quiz attempts with correctness, hesitation times, and answer types
  - Lesson progression and difficulty adjustments
  - User progress state and learning patterns
  - Capstone completion metrics
- **Enables data-driven adaptation**: Learning signals feed back into the adaptive engine for continuous improvement

### 🎯 **Fastino Labs** — Enhanced Personalization & Memory
- **Persistent user memory**: Maintains context across learning sessions
- **RAG-based retrieval**: Pulls relevant memories to personalize lesson content
- **Learning pattern insights**: Identifies user strengths, struggles, and preferred learning styles
- **Contextual personalization**: Enhances lesson delivery with historical learning data

## Demo Flow

1. **Dynamic Diagnostic** → LiquidMetal assesses your AI knowledge level through adaptive questioning
2. **Personalized Lessons** → Content adapts in real-time based on performance (powered by LiquidMetal + Fastino Labs)
3. **Learning Signal Capture** → Every interaction stored in Daft for analytics and adaptation
4. **Capstone Project** → LiquidMetal generates custom AI agent code tailored to your goals

## What Makes It Special

- **True self-evolution**: The system improves its teaching strategy based on what works for each learner
- **Multi-tool integration**: Seamlessly combines agent reasoning (LiquidMetal), structured storage (Daft), and personalization (Fastino Labs)
- **Real-time adaptation**: Adjusts difficulty, style, and pacing within a single session
- **End-to-end learning**: From assessment to capstone project, all powered by intelligent agents

## Technical Highlights

- **Modular architecture**: Easy to swap content, add modules, or extend functionality
- **Graceful fallbacks**: System works even if optional services are unavailable
- **Web + CLI interfaces**: Accessible through both modern web UI and terminal interface
- **Production-ready data layer**: Daft provides scalable, queryable storage for learning analytics

---

*Built for hackathon demonstration. Showcasing the power of combining intelligent agent reasoning, structured data storage, and personalized learning systems.*


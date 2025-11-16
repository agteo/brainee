#!/usr/bin/env python3
"""
Flask Web Application for LearnAI
Provides REST API endpoints and serves the web frontend.
"""

import time
import uuid
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from learning_engine import LearningEngine
from integrations.daft_client import log_quiz_attempt

app = Flask(__name__)
app.secret_key = 'learnai-secret-key-change-in-production'  # Change in production!
CORS(app)

# Store learning engines per session
engines = {}


def get_engine(user_id: str = None) -> LearningEngine:
    """Get or create a learning engine for the current session."""
    if user_id is None:
        # Generate unique user_id for anonymous users (per session)
        if 'user_id' not in session:
            # Use UUID to ensure uniqueness across all anonymous users
            session['user_id'] = f'anonymous_{uuid.uuid4().hex[:12]}'
        user_id = session['user_id']
    
    if user_id not in engines:
        engines[user_id] = LearningEngine(user_id)
    
    session['user_id'] = user_id
    return engines[user_id]


@app.route('/')
def index():
    """Serve the main frontend page."""
    return render_template('index.html')


@app.route('/api/diagnostic', methods=['POST'])
def api_diagnostic():
    """Run diagnostic assessment with multiple questions."""
    data = request.json or {}
    # Support both old format (text answer) and new format (MCQ selection)
    user_input = data.get('answer', '')
    selected_option = data.get('selected_option', None)  # For MCQ: index of selected option
    question_index = data.get('question_index', 0)  # Current question index (0-based)
    previous_answers = data.get('previous_answers', [])  # Array of previous answers
    hesitation = data.get('hesitation_seconds', 0)
    
    engine = get_engine()
    
    # If no answer provided and no selection, return the diagnostic MCQ question
    if not user_input and selected_option is None:
        result = engine.run_diagnostic("", 0, question_index=question_index)
        # Always return MCQ format now
        return jsonify({
            'success': True,
            'result': result
        })
    
    # If it's an MCQ answer, store it and get next question or finalize assessment
    if selected_option is not None:
        # Store the selected option index for evaluation
        user_input = f"Selected option {selected_option}"
        
        # Get the correct answer index for this question from the diagnostic result
        # We need to store it when the question is first loaded
        # For now, get it from the diagnostic result if available
        correct_answer_index = data.get('correct_answer_index', None)
        
        # Add current answer to previous answers (include correct_answer_index for evaluation)
        current_answer = {
            'question_index': question_index,
            'selected_option': selected_option,
            'hesitation_seconds': hesitation,
            'correct_answer_index': correct_answer_index
        }
        all_answers = previous_answers + [current_answer]
        
        # Check if we've answered all questions (5 questions total, indices 0-4)
        if question_index >= 4:  # Last question (index 4 = 5th question)
            # Calculate overall level based on all answers
            diagnostic_result = engine.calculate_diagnostic_level(all_answers)
            assessed_level = diagnostic_result['level']
            all_correct = diagnostic_result.get('all_correct', False)
            all_unsure = diagnostic_result.get('all_unsure', False)
            
            # Log all diagnostic attempts
            for i, answer in enumerate(all_answers):
                log_quiz_attempt({
                    "user_id": engine.user_id,
                    "question_id": f"diagnostic_q{i}",
                    "answer": f"Selected option {answer['selected_option']}",
                    "hesitation_seconds": answer['hesitation_seconds'],
                    "timestamp": time.time()
                })
            
            # Update state with final assessed level
            engine.state_manager.state["difficulty_level"] = assessed_level
            
            # Acceleration logic: if all answers are correct, skip to a more advanced module
            accelerated_module = None
            reasoning = f'Diagnostic complete. Assessed level: {assessed_level}'
            
            if all_correct:
                # User answered all questions correctly - accelerate them
                # Skip fundamentals, go to transformers_llms or even agents depending on level
                current_module = engine.state_manager.get_current_module()
                module_sequence = ["fundamentals", "transformers_llms", "agents", "build_todo_agent"]
                
                if current_module == "diagnostic" or current_module == "fundamentals":
                    # Skip fundamentals, go to transformers_llms
                    accelerated_module = "transformers_llms"
                    engine.state_manager.update_module(accelerated_module)
                    reasoning = f'Excellent! You answered all questions correctly. Accelerating to {accelerated_module.replace("_", " ").title()} module.'
                elif current_module in module_sequence:
                    # Already in a module, advance to next
                    current_idx = module_sequence.index(current_module)
                    if current_idx < len(module_sequence) - 1:
                        accelerated_module = module_sequence[current_idx + 1]
                        engine.state_manager.update_module(accelerated_module)
                        reasoning = f'Perfect score! Advancing to {accelerated_module.replace("_", " ").title()} module.'
            
            engine.state_manager.save_state()
            
            return jsonify({
                'success': True,
                'result': {
                    'next_mode': 'complete',
                    'assessed_level': assessed_level,
                    'total_questions': 5,
                    'answers': all_answers,
                    'all_correct': all_correct,
                    'all_unsure': all_unsure,
                    'accelerated_module': accelerated_module,
                    'reasoning': reasoning
                }
            })
        else:
            # Get next question
            next_index = question_index + 1
            result = engine.run_diagnostic("", 0, question_index=next_index)
            result['previous_answers'] = all_answers
            return jsonify({
                'success': True,
                'result': result
            })
    else:
        # Text answer (fallback)
        result = engine.run_diagnostic(user_input, hesitation)
        return jsonify({
            'success': True,
            'result': result
        })


@app.route('/api/lesson', methods=['GET'])
def api_get_lesson():
    """Get the current lesson page."""
    engine = get_engine()
    lesson_data = engine.get_next_lesson()
    
    # Markdown will be rendered on the frontend using marked.js
    # We keep the raw markdown content for the frontend
    
    return jsonify({
        'success': True,
        'lesson': lesson_data
    })

@app.route('/api/lesson/next-page', methods=['POST'])
def api_next_page():
    """Advance to the next page within the current module."""
    engine = get_engine()
    
    # Get current state before advancing (for comparison)
    current_module = engine.state_manager.get_current_module()
    current_page = engine.state_manager.state.get("current_page", 0)
    
    # Advance to next page (or module if on last page)
    result = engine.advance_to_next_page()
    
    # Check if next modules are coming soon
    if result.get("coming_soon", False):
        return jsonify({
            'success': True,
            'coming_soon': True,
            'message': result.get("message", "AI Agents and Capstone modules are coming soon!")
        })
    
    if result.get("advanced", False):
        # Get the next page/module
        lesson_data = engine.get_next_lesson()
        
        # Check if we advanced to a new module
        new_module = engine.state_manager.get_current_module()
        module_advanced = (new_module != current_module)
        
        # Check if there are more pages in the new module
        new_total_pages = engine.get_module_page_count(new_module)
        new_current_page = engine.state_manager.state.get("current_page", 0)
        has_more_pages = (new_current_page + 1 < new_total_pages)
        
        return jsonify({
            'success': True,
            'lesson': lesson_data,
            'has_more_pages': has_more_pages,
            'module_advanced': module_advanced,
            'coming_soon': False
        })
    else:
        # All modules completed
        return jsonify({
            'success': False,
            'has_more_pages': False,
            'module_advanced': False,
            'coming_soon': False,
            'message': 'All modules completed!'
        })


@app.route('/api/quiz', methods=['POST'])
def api_submit_quiz():
    """Submit a quiz answer (supports both text and MCQ)."""
    data = request.json
    question_id = data.get('question_id')
    question_text = data.get('question', '')  # Question text for clarification generation
    user_answer = data.get('answer', '')
    selected_option = data.get('selected_option', None)  # For MCQ: index of selected option
    correct_answer_index = data.get('correct_answer_index', None)  # For MCQ: correct option index
    hesitation = data.get('hesitation_seconds', 0)
    
    engine = get_engine()
    
    # Handle MCQ answers
    if selected_option is not None and correct_answer_index is not None:
        is_correct = int(selected_option) == int(correct_answer_index)
        user_answer = f"Selected option {selected_option}"
        actual_correct = f"Option {correct_answer_index}"
        is_correct_override = is_correct  # For MCQ, we know the correct answer
    else:
        # For text answers, let semantic evaluation determine correctness
        actual_correct = ""  # Not needed for semantic evaluation
        is_correct_override = None  # Let evaluate_answer() handle it
    
    # Pass question text for clarification generation
    # For MCQ, pass the is_correct result so semantic evaluation doesn't override it
    feedback = engine.submit_quiz_answer(
        question_id, 
        user_answer, 
        actual_correct, 
        hesitation,
        question=question_text,  # Pass question text for clarification
        is_correct_override=is_correct_override  # Override only for MCQ
    )
    
    # Add MCQ-specific feedback
    if selected_option is not None:
        feedback['is_correct'] = is_correct
        feedback['selected_option'] = selected_option
        feedback['correct_option'] = correct_answer_index
    
    # Check if a clarification was generated
    pending_clarifications = engine.state_manager.state.get("pending_clarifications", [])
    if pending_clarifications and not feedback.get('is_correct', False):
        feedback['clarification_generated'] = True
        feedback['clarification_id'] = pending_clarifications[-1].get("module_id")
    
    return jsonify({
        'success': True,
        'feedback': feedback
    })


@app.route('/api/clarification/complete', methods=['POST'])
def api_complete_clarification():
    """Mark a clarification module as complete."""
    data = request.json
    clarification_id = data.get('clarification_id')
    
    if not clarification_id:
        return jsonify({
            'success': False,
            'error': 'clarification_id is required'
        }), 400
    
    engine = get_engine()
    completed = engine.complete_clarification(clarification_id)
    
    return jsonify({
        'success': completed,
        'message': 'Clarification completed' if completed else 'Clarification not found'
    })


@app.route('/api/clarification', methods=['GET'])
def api_get_clarification():
    """Get a specific clarification by ID, or get the first pending clarification."""
    clarification_id = request.args.get('clarification_id')
    engine = get_engine()
    
    pending_clarifications = engine.state_manager.state.get("pending_clarifications", [])
    
    if not pending_clarifications:
        return jsonify({
            'success': False,
            'error': 'No pending clarifications'
        }), 404
    
    # If ID provided, find that specific clarification
    if clarification_id:
        clarification = next((c for c in pending_clarifications if c.get("module_id") == clarification_id), None)
        if not clarification:
            return jsonify({
                'success': False,
                'error': 'Clarification not found'
            }), 404
    else:
        # Return first pending clarification
        clarification = pending_clarifications[0]
    
    return jsonify({
        'success': True,
        'clarification': {
            "module": "clarification",
            "content": clarification["content"],
            "difficulty": max(0, engine.state_manager.get_current_difficulty() - 1),
            "is_clarification": True,
            "clarification_id": clarification["module_id"],
            "question_id": clarification.get("question_id", ""),
            "source_module": clarification.get("source_module", ""),
            "image_reference": "",
            "check_questions": [],
            "current_page": 0,
            "total_pages": 1,
            "is_paginated": False
        }
    })


@app.route('/api/clarifications/pending', methods=['GET'])
def api_get_pending_clarifications():
    """Get list of pending clarifications."""
    engine = get_engine()
    pending_clarifications = engine.state_manager.state.get("pending_clarifications", [])
    
    return jsonify({
        'success': True,
        'count': len(pending_clarifications),
        'clarifications': [
            {
                'clarification_id': c.get("module_id"),
                'question_id': c.get("question_id", ""),
                'source_module': c.get("source_module", "")
            }
            for c in pending_clarifications
        ]
    })


@app.route('/api/capstone', methods=['POST'])
def api_capstone():
    """Generate capstone project."""
    data = request.json
    task_description = data.get('task_description', '')
    
    engine = get_engine()
    result = engine.run_capstone(task_description)
    
    return jsonify({
        'success': True,
        'result': result
    })


@app.route('/api/progress', methods=['GET'])
def api_progress():
    """Get user progress summary."""
    engine = get_engine()
    progress = engine.get_progress_summary()
    
    return jsonify({
        'success': True,
        'progress': progress
    })


@app.route('/api/advance', methods=['POST'])
def api_advance():
    """Advance to the next module."""
    engine = get_engine()
    result = engine.advance_to_next_module()
    
    return jsonify({
        'success': True,
        'advanced': result.get("advanced", False),
        'coming_soon': result.get("coming_soon", False),
        'message': result.get("message", "")
    })


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset user progress."""
    engine = get_engine()
    engine.reset_user_state()
    
    return jsonify({
        'success': True,
        'message': 'Progress reset successfully'
    })


@app.route('/api/freepik-image', methods=['GET'])
def api_freepik_image():
    """Get Freepik image for a concept."""
    concept = request.args.get('concept', 'AI concept')
    
    from integrations.freepik_client import get_image_for_concept
    image_ref = get_image_for_concept(concept)
    
    return jsonify({
        'success': True,
        'image_url': image_ref,
        'concept': concept
    })


@app.route('/api/admin/dashboard', methods=['GET'])
def api_admin_dashboard():
    """Get admin dashboard data - system-wide statistics and all users."""
    # Simple admin check (in production, use proper authentication)
    admin_key = request.args.get('key', '')
    if admin_key != 'admin123':  # Change this in production!
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 403
    
    import json
    from pathlib import Path
    from datetime import datetime
    from integrations.daft_client import DaftStorage
    
    # Use DaftStorage to load data (reads from Parquet if available, falls back to JSON)
    storage = DaftStorage()
    data_dir = storage.data_dir
    
    # Load all user progress from Daft/JSON
    all_users = []
    user_progress_path = data_dir / "user_progress.json"
    if user_progress_path.exists():
        with open(user_progress_path, "r", encoding="utf-8") as f:
            all_users = json.load(f)
    
    # Try to load from Parquet if Daft is available (Parquet files are in directories)
    try:
        import daft
        parquet_path = data_dir / "user_progress.parquet"
        if parquet_path.exists() and parquet_path.is_dir():
            df = daft.read_parquet(str(parquet_path))
            # Convert to list of dicts, deserializing JSON fields
            if len(df) > 0:
                pandas_df = df.to_pandas()
                all_users = []
                for _, row in pandas_df.iterrows():
                    user_dict = {
                        "user_id": row.get("user_id", ""),
                        "current_module": row.get("current_module", "diagnostic"),
                        "difficulty_level": int(row.get("difficulty_level", 1)),
                        "completed_modules": json.loads(row.get("completed_modules", "[]")),
                        "quiz_performance": json.loads(row.get("quiz_performance", "[]")),
                        "hesitation_history": json.loads(row.get("hesitation_history", "[]")),
                        "preferred_learning_style": row.get("preferred_learning_style") or None,
                        "created_at": row.get("created_at", ""),
                        "last_active": row.get("last_active", "")
                    }
                    all_users.append(user_dict)
    except Exception as e:
        pass  # Fallback to JSON if Parquet read fails
    
    # Load quiz attempts from Daft/JSON
    all_quiz_attempts = []
    quiz_attempts_path = data_dir / "quiz_attempts.json"
    if quiz_attempts_path.exists():
        with open(quiz_attempts_path, "r", encoding="utf-8") as f:
            all_quiz_attempts = json.load(f)
    
    # Try to load from Parquet directory if Daft is available
    try:
        import daft
        parquet_path = data_dir / "quiz_attempts.parquet"
        if parquet_path.exists() and parquet_path.is_dir():
            df = daft.read_parquet(str(parquet_path))
            if len(df) > 0:
                pandas_df = df.to_pandas()
                all_quiz_attempts = pandas_df.to_dict('records')
    except Exception:
        pass  # Fallback to JSON if Parquet read fails
    
    # Load lesson logs from Daft/JSON
    lesson_log_path = data_dir / "lesson_log.json"
    all_lesson_logs = []
    if lesson_log_path.exists():
        with open(lesson_log_path, "r", encoding="utf-8") as f:
            all_lesson_logs = json.load(f)
    
    # Try to load from Parquet directory if Daft is available
    try:
        import daft
        parquet_path = data_dir / "lesson_log.parquet"
        if parquet_path.exists() and parquet_path.is_dir():
            df = daft.read_parquet(str(parquet_path))
            if len(df) > 0:
                pandas_df = df.to_pandas()
                all_lesson_logs = pandas_df.to_dict('records')
    except Exception:
        pass  # Fallback to JSON if Parquet read fails
    
    # Calculate system-wide statistics
    total_users = len(all_users)
    total_questions = len(all_quiz_attempts)
    total_lessons_viewed = len(all_lesson_logs)
    
    # Aggregate performance metrics
    if all_quiz_attempts:
        correct_answers = sum(1 for q in all_quiz_attempts if q.get("correct", False))
        system_accuracy = correct_answers / len(all_quiz_attempts) if all_quiz_attempts else 0
        avg_hesitation = sum(q.get("hesitation_seconds", 0) for q in all_quiz_attempts) / len(all_quiz_attempts) if all_quiz_attempts else 0
    else:
        system_accuracy = 0
        avg_hesitation = 0
    
    # Module completion stats
    module_stats = {}
    for user in all_users:
        for module in user.get("completed_modules", []):
            module_stats[module] = module_stats.get(module, 0) + 1
    
    # Learning style distribution
    style_distribution = {}
    for user in all_users:
        style = user.get("preferred_learning_style") or "text"
        style_distribution[style] = style_distribution.get(style, 0) + 1
    
    # Difficulty level distribution
    difficulty_distribution = {0: 0, 1: 0, 2: 0, 3: 0}
    for user in all_users:
        diff = user.get("difficulty_level", 1)
        difficulty_distribution[diff] = difficulty_distribution.get(diff, 0) + 1
    
    # Recent activity (last 10 quiz attempts)
    recent_activity = sorted(all_quiz_attempts, key=lambda x: x.get("timestamp", 0), reverse=True)[:10]
    
    # User list with stats
    user_list = []
    for user in all_users:
        user_quiz_attempts = [q for q in all_quiz_attempts if q.get("user_id") == user.get("user_id")]
        user_correct = sum(1 for q in user_quiz_attempts if q.get("correct", False))
        user_accuracy = user_correct / len(user_quiz_attempts) if user_quiz_attempts else 0
        
        user_list.append({
            "user_id": user.get("user_id"),
            "current_module": user.get("current_module", "diagnostic"),
            "difficulty_level": user.get("difficulty_level", 1),
            "completed_modules": len(user.get("completed_modules", [])),
            "total_questions": len(user_quiz_attempts),
            "accuracy": user_accuracy,
            "learning_style": user.get("preferred_learning_style") or "text",
            "last_active": user.get("last_active", ""),
            "created_at": user.get("created_at", "")
        })
    
    # Performance over time (last 7 days if timestamps available)
    daily_stats = {}
    for attempt in all_quiz_attempts:
        try:
            timestamp = attempt.get("timestamp", 0)
            if isinstance(timestamp, (int, float)):
                date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            else:
                date = datetime.fromisoformat(str(timestamp)).strftime("%Y-%m-%d")
            if date not in daily_stats:
                daily_stats[date] = {"total": 0, "correct": 0}
            daily_stats[date]["total"] += 1
            if attempt.get("correct", False):
                daily_stats[date]["correct"] += 1
        except:
            pass
    
    # Get Fastino usage statistics
    fastino_stats = {
        'enabled': False,
        'usage': {}
    }
    try:
        from integrations.fastino_client import get_fastino_client
        fastino = get_fastino_client()
        if fastino.is_available():
            fastino_stats['enabled'] = True
            fastino_stats['usage'] = fastino.get_usage_stats()
    except Exception as e:
        pass  # Fastino not available or error
    
    # Get LiquidMetal usage statistics
    liquidmetal_stats = {
        'available': False,
        'usage': {}
    }
    try:
        from integrations.liquidmetal_runner import LiquidMetalRunner, LIQUIDMETAL_AVAILABLE
        liquidmetal_stats['available'] = LIQUIDMETAL_AVAILABLE
        liquidmetal_stats['usage'] = LiquidMetalRunner.get_usage_stats()
    except Exception as e:
        pass
    
    # Get Daft usage statistics
    daft_stats = {
        'available': False,
        'usage': {}
    }
    try:
        from integrations.daft_client import DaftStorage, DAFT_AVAILABLE
        daft_stats['available'] = DAFT_AVAILABLE
        from integrations.daft_client import _storage
        daft_stats['usage'] = _storage.get_usage_stats()
    except Exception as e:
        pass
    
    return jsonify({
        'success': True,
        'dashboard': {
            'system_stats': {
                'total_users': total_users,
                'total_questions': total_questions,
                'total_lessons_viewed': total_lessons_viewed,
                'system_accuracy': system_accuracy,
                'avg_hesitation_seconds': avg_hesitation
            },
            'fastino_stats': fastino_stats,
            'liquidmetal_stats': liquidmetal_stats,
            'daft_stats': daft_stats,
            'module_stats': module_stats,
            'style_distribution': style_distribution,
            'difficulty_distribution': difficulty_distribution,
            'recent_activity': recent_activity,
            'users': sorted(user_list, key=lambda x: x.get("last_active", ""), reverse=True),
            'daily_stats': daily_stats
        }
    })


@app.route('/api/learning-insights', methods=['GET'])
def api_learning_insights():
    """Get real-time learning insights and adaptation data for demo purposes."""
    engine = get_engine()
    progress = engine.get_progress_summary()
    state = engine.state_manager.state
    
    # Calculate recent performance trends
    recent_performance = state.get("quiz_performance", [])[-5:]
    recent_hesitation = state.get("hesitation_history", [])[-5:]
    
    # Build adaptation log
    adaptations = []
    if len(state.get("quiz_performance", [])) > 0:
        prev_diff = None
        for i, attempt in enumerate(state.get("quiz_performance", [])):
            current_diff = attempt.get("difficulty_level", state.get("difficulty_level", 1))
            if prev_diff is not None and current_diff != prev_diff:
                direction = "increased" if current_diff > prev_diff else "decreased"
                reason = "Strong performance" if current_diff > prev_diff else "Struggling with content"
                adaptations.append({
                    "timestamp": attempt.get("timestamp", ""),
                    "type": "difficulty_change",
                    "direction": direction,
                    "from": prev_diff,
                    "to": current_diff,
                    "reason": reason
                })
            prev_diff = current_diff
    
    # Generate AI insights
    insights = []
    if len(recent_performance) >= 2:
        accuracy = sum(1 for a in recent_performance if a.get("correct", False)) / len(recent_performance)
        avg_hesitation = sum(recent_hesitation) / len(recent_hesitation) if recent_hesitation else 0
        
        if accuracy >= 0.8 and avg_hesitation < 10:
            insights.append({
                "type": "success",
                "message": "You're mastering the content quickly! I'm increasing the challenge level.",
                "icon": "📈"
            })
        elif accuracy < 0.5 or avg_hesitation > 15:
            insights.append({
                "type": "adaptation",
                "message": "I notice you're taking more time. I'll simplify the next lesson and add more examples.",
                "icon": "🔄"
            })
        
        if state.get("preferred_learning_style") == "examples":
            insights.append({
                "type": "style",
                "message": "Switched to examples-first mode based on your learning pattern.",
                "icon": "💡"
            })
    
    # Calculate performance metrics
    performance_metrics = {
        "recent_accuracy": sum(1 for a in recent_performance if a.get("correct", False)) / len(recent_performance) if recent_performance else 0,
        "avg_hesitation": sum(recent_hesitation) / len(recent_hesitation) if recent_hesitation else 0,
        "total_attempts": len(state.get("quiz_performance", [])),
        "difficulty_trend": "increasing" if len(adaptations) > 0 and adaptations[-1].get("direction") == "increased" else "stable" if len(adaptations) == 0 else "decreasing"
    }
    
    # Get all quiz history for chart (not just recent)
    all_quiz_history = state.get("quiz_performance", [])
    
    return jsonify({
        'success': True,
        'insights': {
            'current_difficulty': state.get("difficulty_level", 1),
            'learning_style': state.get("preferred_learning_style") or progress.get("adaptations", {}).get("recommended_style", "text"),
            'ai_insights': insights,
            'adaptations': adaptations[-5:],  # Last 5 adaptations
            'performance_metrics': performance_metrics,
            'quiz_history': all_quiz_history,  # All history for chart
            'hesitation_history': state.get("hesitation_history", [])  # All hesitation history
        }
    })


@app.route('/api/test/liquidmetal', methods=['GET'])
def api_test_liquidmetal():
    """Test if LiquidMetal is working."""
    try:
        from integrations.liquidmetal_runner import LiquidMetalRunner, LIQUIDMETAL_AVAILABLE
        import os
        
        status = {
            'sdk_available': LIQUIDMETAL_AVAILABLE,
            'api_key_configured': bool(
                os.getenv("RAINDROP_API_KEY") or 
                os.getenv("LIQUIDMETAL_API_KEY") or 
                os.getenv("LM_API_KEY")
            ),
            'client_initialized': False,
            'test_result': None,
            'error': None
        }
        
        if LIQUIDMETAL_AVAILABLE:
            try:
                runner = LiquidMetalRunner()
                status['client_initialized'] = runner.liquidmetal_client is not None
                
                # Try a simple test call
                if runner.liquidmetal_client:
                    # Test with a simple question generation
                    test_result = runner.run_lesson_agent({
                        "current_module": "fundamentals",
                        "difficulty": 1,
                        "recent_performance": []
                    })
                    status['test_result'] = {
                        'success': test_result is not None,
                        'has_questions': bool(test_result and test_result.get('check_questions')),
                        'module_file': test_result.get('module_file') if test_result else None
                    }
            except Exception as e:
                status['error'] = str(e)
        
        return jsonify({
            'success': True,
            'status': status,
            'usage_stats': LiquidMetalRunner.get_usage_stats() if LIQUIDMETAL_AVAILABLE else {}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


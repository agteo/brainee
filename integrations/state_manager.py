"""User State Manager for LearnAI.

Tracks user progress, difficulty levels, and learning patterns.
Implements the self-evolving logic by analyzing performance over time.
Enhanced with Fastino Labs for deeper personalization.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Try to import Fastino client
try:
    from integrations.fastino_client import get_fastino_client
    FASTINO_AVAILABLE = True
except ImportError:
    FASTINO_AVAILABLE = False


class UserStateManager:
    """Manages user state and learning progression."""

    def __init__(self, user_id: str, data_dir: Optional[Path] = None):
        self.user_id = user_id
        self.data_dir = data_dir or Path(__file__).resolve().parents[1] / "data"
        self.data_dir.mkdir(exist_ok=True)

        # Initialize Fastino client if available
        self.fastino = None
        if FASTINO_AVAILABLE:
            self.fastino = get_fastino_client()
            # Register user with Fastino on first initialization
            if self.fastino.is_available():
                self.fastino.register_user(user_id, {
                    "platform": "learnai",
                    "created_at": datetime.now().isoformat()
                })

        self.state = self._load_or_initialize_state()

    def _load_or_initialize_state(self) -> Dict:
        """Load existing state or create new one."""
        path = self.data_dir / "user_progress.json"

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                all_users = json.load(f)
                for user_data in all_users:
                    if user_data.get("user_id") == self.user_id:
                        return user_data

        # Initialize new user
        return {
            "user_id": self.user_id,
            "current_module": "diagnostic",
            "current_page": 0,  # Page index within current module (0-based)
            "difficulty_level": 1,  # 0-3 scale
            "completed_modules": [],
            "quiz_performance": [],
            "hesitation_history": [],
            "preferred_learning_style": None,  # "visual", "text", "examples"
            "pending_clarifications": [],  # List of clarification modules to show
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }

    def save_state(self):
        """Persist current state to disk."""
        path = self.data_dir / "user_progress.json"

        # Load all users
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                all_users = json.load(f)
        else:
            all_users = []

        # Update or append this user's state
        self.state["last_active"] = datetime.now().isoformat()
        all_users = [u for u in all_users if u.get("user_id") != self.user_id]
        all_users.append(self.state)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(all_users, f, indent=2)

    def update_module(self, module_name: str):
        """Update current module."""
        previous_module = self.state["current_module"]
        if previous_module not in self.state["completed_modules"]:
            self.state["completed_modules"].append(previous_module)
            
            # Ingest module completion into Fastino
            if self.fastino and self.fastino.is_available():
                self.fastino.ingest_event(
                    self.user_id,
                    "module_completed",
                    {
                        "module": previous_module,
                        "difficulty_level": self.state["difficulty_level"],
                        "total_questions": len(self.state["quiz_performance"])
                    },
                    {"timestamp": datetime.now().isoformat()}
                )
        
        self.state["current_module"] = module_name
        self.save_state()

    def record_quiz_attempt(self, question_id: str, correct: bool,
                           hesitation_seconds: float):
        """Record a quiz attempt and update difficulty."""
        attempt = {
            "timestamp": datetime.now().isoformat(),
            "question_id": question_id,
            "correct": correct,
            "hesitation_seconds": hesitation_seconds,
            "difficulty_level": self.state["difficulty_level"]
        }

        self.state["quiz_performance"].append(attempt)
        self.state["hesitation_history"].append(hesitation_seconds)

        # Ingest event into Fastino for enhanced memory
        if self.fastino and self.fastino.is_available():
            self.fastino.ingest_event(
                self.user_id,
                "quiz_attempt",
                {
                    "question_id": question_id,
                    "correct": correct,
                    "hesitation_seconds": hesitation_seconds,
                    "difficulty_level": self.state["difficulty_level"],
                    "current_module": self.state["current_module"]
                },
                {"timestamp": datetime.now().isoformat()}
            )

        # Self-evolving logic: adjust difficulty based on performance
        self._adjust_difficulty()
        self.save_state()

    def _adjust_difficulty(self):
        """Self-evolving difficulty adjustment based on recent performance.

        Enhanced with Fastino for more intelligent adaptation decisions.

        Implements the adaptive learning logic from PRD:
        - 2 correct + low hesitation → increase difficulty
        - 2 incorrect or high hesitation → decrease difficulty
        """
        if len(self.state["quiz_performance"]) < 2:
            return

        recent = self.state["quiz_performance"][-2:]
        current_difficulty = self.state["difficulty_level"]

        # Try Fastino prediction for difficulty adjustment (more active usage)
        if self.fastino and self.fastino.is_available():
            try:
                prediction_context = {
                    "recent_performance": recent,
                    "current_difficulty": current_difficulty,
                    "hesitation_history": self.state["hesitation_history"][-5:],
                    "module": self.state["current_module"],
                    "total_questions": len(self.state["quiz_performance"])
                }
                
                prediction = self.fastino.predict_decision(
                    self.user_id,
                    {
                        "decision_type": "difficulty_adjustment",
                        "context": prediction_context
                    }
                )
                
                if prediction and prediction.get("recommended_difficulty") is not None:
                    recommended = int(prediction.get("recommended_difficulty", current_difficulty))
                    # Clamp to valid range
                    recommended = max(0, min(3, recommended))
                    if recommended != current_difficulty:
                        self.state["difficulty_level"] = recommended
                        print(f"Fastino recommended difficulty change: {current_difficulty} → {recommended}")
                        return
            except Exception as e:
                print(f"Fastino difficulty prediction error: {e}")
                # Fall through to heuristic logic

        # Fallback to heuristic logic if Fastino unavailable or failed
        # Check for success pattern (2 correct with low hesitation)
        if all(a["correct"] for a in recent) and \
           all(a["hesitation_seconds"] < 10 for a in recent):
            self.state["difficulty_level"] = min(3, self.state["difficulty_level"] + 1)
            return

        # Check for struggle pattern (2 incorrect or high hesitation)
        if sum(1 for a in recent if not a["correct"]) >= 2 or \
           sum(1 for a in recent if a["hesitation_seconds"] > 10) >= 2:
            self.state["difficulty_level"] = max(0, self.state["difficulty_level"] - 1)

    def should_switch_to_examples(self) -> bool:
        """Determine if we should switch to examples-first mode.
        
        Enhanced with Fastino for more intelligent detection.
        """
        if len(self.state["quiz_performance"]) < 2:
            return False

        recent = self.state["quiz_performance"][-2:]
        
        # Try Fastino query for learning style recommendation
        if self.fastino and self.fastino.is_available():
            try:
                query_result = self.fastino.query_user_profile(
                    self.user_id,
                    "Should this user switch to examples-first learning mode based on recent struggles?"
                )
                if query_result and query_result.get("answer"):
                    answer_lower = query_result["answer"].lower()
                    if "yes" in answer_lower or "should" in answer_lower or "recommend" in answer_lower:
                        return True
            except Exception as e:
                print(f"Fastino examples query error: {e}")
        
        # Fallback to heuristic
        return sum(1 for a in recent if not a["correct"]) >= 2

    def should_simplify(self) -> bool:
        """Determine if we should simplify explanations.
        
        Enhanced with Fastino for struggle detection.
        """
        if len(self.state["hesitation_history"]) < 2:
            return False

        recent_hesitation = self.state["hesitation_history"][-2:]
        
        # Try Fastino for struggle detection
        if self.fastino and self.fastino.is_available():
            try:
                # Query Fastino about user struggles
                memories = self.fastino.retrieve_memories(
                    self.user_id,
                    "What concepts or topics has this user struggled with recently?",
                    top_k=3
                )
                if memories and len(memories) > 0:
                    # If Fastino found struggle memories, likely should simplify
                    return True
            except Exception as e:
                print(f"Fastino simplify query error: {e}")
        
        # Fallback to heuristic
        return all(h > 10 for h in recent_hesitation)

    def get_recommended_content_style(self) -> str:
        """Recommend content style based on user history.
        
        Enhanced with Fastino insights if available.
        """
        # Try to get Fastino insights for better personalization
        if self.fastino and self.fastino.is_available():
            try:
                # Query Fastino for learning style preferences
                query_result = self.fastino.query_user_profile(
                    self.user_id,
                    "What learning style does this user prefer? text, visual, or examples?"
                )
                if query_result and query_result.get("answer"):
                    # Parse Fastino response for style preference
                    answer_lower = query_result["answer"].lower()
                    if "visual" in answer_lower:
                        return "visual"
                    elif "example" in answer_lower:
                        return "examples"
                    elif "text" in answer_lower:
                        return "text"
            except Exception as e:
                print(f"Fastino style query error: {e}")
        
        # Fallback to existing logic
        # If preference is set, use it
        if self.state["preferred_learning_style"]:
            return self.state["preferred_learning_style"]

        # Otherwise, adapt based on performance
        if self.should_switch_to_examples():
            return "examples"
        elif self.should_simplify():
            return "visual"
        else:
            return "text"

    def get_current_difficulty(self) -> int:
        """Get current difficulty level (0-3)."""
        return self.state["difficulty_level"]

    def get_current_module(self) -> str:
        """Get current module name."""
        return self.state["current_module"]

    def set_learning_style(self, style: str):
        """Set preferred learning style."""
        if style in ["visual", "text", "examples"]:
            self.state["preferred_learning_style"] = style
            self.save_state()

    def get_progress_summary(self) -> Dict:
        """Get a summary of user progress.
        
        Enhanced with Fastino insights if available.
        """
        total_questions = len(self.state["quiz_performance"])
        correct_answers = sum(1 for a in self.state["quiz_performance"] if a["correct"])

        summary = {
            "user_id": self.user_id,
            "current_module": self.state["current_module"],
            "completed_modules": self.state["completed_modules"],
            "difficulty_level": self.state["difficulty_level"],
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "accuracy": correct_answers / total_questions if total_questions > 0 else 0,
            "preferred_style": self.state["preferred_learning_style"]
        }
        
        # Add Fastino insights if available
        if self.fastino and self.fastino.is_available():
            try:
                fastino_summary = self.fastino.get_user_summary(self.user_id)
                if fastino_summary:
                    summary["fastino_insights"] = fastino_summary
            except Exception as e:
                print(f"Fastino summary error: {e}")
        
        return summary
    
    def get_fastino_memories(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant memories from Fastino using RAG.
        
        Args:
            query: Query to find relevant memories
            top_k: Number of memories to retrieve
        
        Returns:
            List of relevant memory snippets
        """
        if self.fastino and self.fastino.is_available():
            return self.fastino.retrieve_memories(self.user_id, query, top_k)
        return []

"""Core Learning Engine for LearnAI.

Orchestrates the adaptive learning flow:
1. Diagnostic assessment
2. Adaptive lesson delivery
3. Quiz and reflection
4. Capstone project

Implements self-evolving logic by tracking and adapting to user performance.
"""

import time
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from integrations.state_manager import UserStateManager
from integrations.liquidmetal_runner import run_liquidmetal_agent
from integrations.daft_client import log_quiz_attempt, log_lesson_event
from integrations.freepik_client import get_image_for_concept
from integrations.gemini_client import GeminiClient

# Try to import OpenAI for answer evaluation
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class LearningEngine:
    """Main orchestration engine for adaptive learning."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state_manager = UserStateManager(user_id)
        self.content_dir = Path(__file__).resolve().parent / "content" / "syllabus"
        self.current_lesson_content = None
        
        # Initialize OpenAI client for answer evaluation if available
        self.openai_client = None
        if OPENAI_AVAILABLE:
            try:
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except Exception:
                pass
        
        # Initialize Gemini client for images/videos
        try:
            self.gemini_client = GeminiClient()
        except Exception as e:
            print(f"Gemini client initialization error: {e}")
            self.gemini_client = None

    def run_diagnostic(self, user_input: str = "", hesitation_seconds: float = 0, question_index: int = 0) -> Dict:
        """Run diagnostic assessment to determine user level.

        Enhanced with Fastino for better initial personalization.

        Args:
            user_input: User's response to diagnostic question
            hesitation_seconds: Time taken to respond
            question_index: Current question index (0-based) for multi-question diagnostic

        Returns:
            Dict with diagnostic results and next steps
        """
        # Ingest diagnostic response into Fastino
        if self.state_manager.fastino and self.state_manager.fastino.is_available() and user_input:
            self.state_manager.fastino.ingest_event(
                self.user_id,
                "diagnostic_response",
                {
                    "input": user_input,
                    "hesitation_seconds": hesitation_seconds,
                    "question_index": question_index
                },
                {"timestamp": time.time()}
            )
        
        # Run diagnostic agent
        agent_result = run_liquidmetal_agent("diagnostic", {
            "user_id": self.user_id,
            "raw_input": user_input,
            "hesitation_seconds": hesitation_seconds,
            "question_index": question_index
        })

        # Note: Diagnostic logging is handled in app.py for MCQ flow
        # Only log here for text-based diagnostic (fallback mode)
        # Skip logging for MCQ format (which uses "Selected option X" format)
        if user_input and user_input.strip() and not user_input.startswith("Selected option"):
            log_quiz_attempt({
                "user_id": self.user_id,
                "question_id": "diagnostic_initial",
                "user_answer": user_input,
                "answer": "",
                "correct": False,  # Text diagnostic doesn't have correct answer
                "hesitation_seconds": hesitation_seconds,
                "timestamp": time.time(),
                "difficulty_level": self.state_manager.get_current_difficulty()
            })

        # Update state if we got an assessed level (only for final assessment)
        if "assessed_level" in agent_result and agent_result.get("next_mode") == "complete":
            self.state_manager.state["difficulty_level"] = agent_result["assessed_level"]
            self.state_manager.save_state()

        return agent_result
    
    def calculate_diagnostic_level(self, answers: List[Dict]) -> Dict:
        """Calculate overall difficulty level based on all diagnostic answers.
        
        Args:
            answers: List of answer dicts with 'question_index', 'selected_option', 'hesitation_seconds', 'correct_answer_index'
            
        Returns:
            Dict with:
                - 'level': Difficulty level (0=beginner, 1=intermediate, 2=advanced, 3=expert)
                - 'all_correct': True if all answers were correct
                - 'all_unsure': True if all answers were "I'm not sure"
        """
        if not answers:
            return {'level': 1, 'all_correct': False, 'all_unsure': False}  # Default to intermediate
        
        # Question difficulty weights and scoring
        # Each question has a difficulty_weight (1=beginner, 2=intermediate, 3=advanced)
        # "I'm not sure" is always at index 4 (5th option)
        
        total_score = 0
        total_weight = 0
        unsure_count = 0
        correct_count = 0
        total_questions = len(answers)
        
        # Question weights (matching the questions in liquidmetal_runner.py)
        question_weights = [1, 1, 2, 2, 3]  # 5 questions
        
        for answer in answers:
            q_idx = answer.get('question_index', 0)
            # Convert to int to handle string/number issues, default to 4 ("I'm not sure")
            selected = int(answer.get('selected_option', 4))
            correct_answer_index = answer.get('correct_answer_index', None)
            # Convert correct_answer_index to int if it exists
            if correct_answer_index is not None:
                correct_answer_index = int(correct_answer_index)
            weight = question_weights[q_idx] if q_idx < len(question_weights) else 1
            
            if selected == 4:  # "I'm not sure" (always last option, index 4)
                unsure_count += 1
                # Don't add to total_weight or total_score for unsure answers
            elif correct_answer_index is not None and selected == correct_answer_index:
                # Correct answer (using stored correct index)
                correct_count += 1
                total_score += weight
                total_weight += weight
            else:  # Wrong answer
                # Include wrong answers in total_weight so the average reflects all attempted questions
                total_weight += weight
        
        # If user answered "I'm not sure" to all questions, they're definitely a beginner
        if unsure_count == total_questions:
            return {'level': 0, 'all_correct': False, 'all_unsure': True}
        
        # If user answered all questions correctly, they're advanced/expert
        if correct_count == total_questions:
            return {'level': 3, 'all_correct': True, 'all_unsure': False}
        
        # If user got zero correct answers (all wrong), they're definitely a beginner
        if correct_count == 0:
            return {'level': 0, 'all_correct': False, 'all_unsure': (unsure_count == total_questions)}
        
        # If user is unsure on 4+ questions (out of 5), they're definitely a beginner
        if unsure_count >= 4:
            return {'level': 0, 'all_correct': False, 'all_unsure': False}
        
        # If user is unsure on 3+ questions (majority), they're likely a beginner
        if unsure_count >= 3:
            return {'level': 0, 'all_correct': False, 'all_unsure': False}
        
        # Calculate average score based on answered questions only
        if total_weight > 0:
            avg_score = total_score / total_weight
        else:
            # This should not happen if correct_count > 0, but handle it anyway
            # If no correct answers (all wrong or unsure), default to beginner
            if unsure_count > 0:
                level = 0  # Beginner
                return {'level': level, 'all_correct': False, 'all_unsure': (unsure_count == total_questions)}
            else:
                # All wrong answers, still beginner
                level = 0
                return {'level': level, 'all_correct': False, 'all_unsure': False}
        
        # Map score to level
        if avg_score >= 0.8:
            level = 3  # Expert
        elif avg_score >= 0.6:
            level = 2  # Advanced
        elif avg_score >= 0.4:
            level = 1  # Intermediate
        else:
            level = 0  # Beginner
        
        return {'level': level, 'all_correct': False, 'all_unsure': False}

    def filter_instructional_meta_text(self, content: str) -> str:
        """Remove or convert meta-instructional text that talks about 'the learner' in third person.
        
        Args:
            content: Raw lesson content
            
        Returns:
            Content with meta-instructional text filtered out or converted
        """
        import re
        
        lines = content.split('\n')
        filtered_lines = []
        
        for line in lines:
            original_line = line
            # Pattern 1: "Help the learner [verb]..." -> "[Verb]..."
            if re.search(r'\bhelp\s+(the\s+)?learner\s+', line, re.IGNORECASE):
                # Remove "Help the learner" and capitalize the next word
                line = re.sub(r'\bhelp\s+(the\s+)?learner\s+', '', line, flags=re.IGNORECASE)
                # Capitalize first letter if it's lowercase
                if line and line[0].islower():
                    line = line[0].upper() + line[1:] if len(line) > 1 else line.upper()
            
            # Pattern 2: "Ask the learner:" -> "Consider:" or "Think about:"
            elif re.search(r'\bask\s+(the\s+)?learner\s*:', line, re.IGNORECASE):
                line = re.sub(r'\bask\s+(the\s+)?learner\s*:\s*', 'Consider: ', line, flags=re.IGNORECASE)
            
            # Pattern 3: "Tell/Show/Guide the learner..." -> Remove the meta-text
            elif re.search(r'\b(tell|show|guide)\s+(the\s+)?learner\b', line, re.IGNORECASE):
                line = re.sub(r'\b(tell|show|guide)\s+(the\s+)?learner\s+', '', line, flags=re.IGNORECASE)
                # Capitalize first letter if needed
                if line and line[0].islower():
                    line = line[0].upper() + line[1:] if len(line) > 1 else line.upper()
            
            # Pattern 4: "the learner should/will/can/must" -> "you should/will/can/must"
            elif re.search(r'\bthe\s+learner\s+(should|will|can|must)\b', line, re.IGNORECASE):
                line = re.sub(r'\bthe\s+learner\s+(should|will|can|must)\b', 'you \\1', line, flags=re.IGNORECASE)
            
            # Pattern 5: "Ask the learner" (without colon) -> Remove
            elif re.search(r'\bask\s+(the\s+)?learner\b', line, re.IGNORECASE) and ':' not in line:
                line = re.sub(r'\bask\s+(the\s+)?learner\s+', '', line, flags=re.IGNORECASE)
                if line and line[0].islower():
                    line = line[0].upper() + line[1:] if len(line) > 1 else line.upper()
            
            # Only add non-empty lines (after filtering)
            if line.strip():
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)

    def load_lesson_content(self, module_name: str, page_index: int = 0) -> str:
        """Load lesson content from markdown file.

        Args:
            module_name: Name of the module (e.g., 'fundamentals')
            page_index: Page index within the module (0-based)

        Returns:
            Lesson content as string (with meta-instructional text filtered)
        """
        # Check if module uses pagination (fundamentals has multiple pages)
        if module_name == "fundamentals":
            lesson_file = self.content_dir / f"{module_name}_page{page_index + 1}.md"
        else:
            # For other modules, use the standard file
            lesson_file = self.content_dir / f"{module_name}.md"
        
        if not lesson_file.exists():
            # Fallback to standard file if page doesn't exist
            lesson_file = self.content_dir / f"{module_name}.md"
            if not lesson_file.exists():
                return f"Error: Lesson file not found: {lesson_file}"

        with open(lesson_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Filter out meta-instructional text before storing/returning
        content = self.filter_instructional_meta_text(content)

        self.current_lesson_content = content
        return content
    
    def get_module_page_count(self, module_name: str) -> int:
        """Get the number of pages in a module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Number of pages (1 if not paginated)
        """
        if module_name == "fundamentals":
            # Count fundamentals pages
            page_count = 0
            for i in range(1, 20):  # Check up to 20 pages
                page_file = self.content_dir / f"fundamentals_page{i}.md"
                if page_file.exists():
                    page_count += 1
                else:
                    break
            return page_count if page_count > 0 else 1
        return 1  # Other modules are single-page

    def generate_clarification_module(self, question: str, question_id: str, 
                                      incorrect_answer: str, correct_answer: str,
                                      current_module: str) -> Dict:
        """Generate a dynamic clarification module to help user understand a concept they got wrong.
        
        Args:
            question: The question text that was answered incorrectly
            question_id: ID of the question
            incorrect_answer: The answer the user provided (or selected option)
            correct_answer: The correct answer
            current_module: The current module where the question was asked
            
        Returns:
            Dict with clarification module content and metadata
        """
        # Use LiquidMetal agent to generate clarification content
        agent_context = {
            "user_id": self.user_id,
            "question": question,
            "question_id": question_id,
            "incorrect_answer": incorrect_answer,
            "correct_answer": correct_answer,
            "current_module": current_module,
            "difficulty_level": self.state_manager.get_current_difficulty(),
            "learning_style": "examples"  # Clarifications should be example-focused
        }
        
        # Create a clarification prompt for the agent
        clarification_prompt = f"""Generate a clarification lesson to help the user understand a concept they got wrong.

Question: {question}
User's answer: {incorrect_answer}
Correct answer: {correct_answer}
Current module: {current_module}

Create a brief, focused clarification that:
1. Explains why the correct answer is correct
2. Addresses common misconceptions (especially the one the user had)
3. Provides clear examples
4. Uses simple, beginner-friendly language
5. Is concise (1-2 pages max)

Return the clarification content in markdown format."""
        
        # Try to use LiquidMetal to generate clarification
        try:
            agent_result = run_liquidmetal_agent("lesson", {
                **agent_context,
                "clarification_request": clarification_prompt
            })
            
            # Extract content from agent result
            clarification_content = agent_result.get("content", "")
            if not clarification_content:
                # Fallback: generate simple clarification
                clarification_content = f"""## Clarification: Understanding {question_id}

You selected: **{incorrect_answer}**

The correct answer is: **{correct_answer}**

### Why this matters:

Let me help clarify this concept for you. The key point here is understanding the difference between what you selected and the correct answer.

### Key Takeaway:

{correct_answer} is correct because...

### Example:

Here's a simple example to illustrate this concept...

### Try Again:

After reviewing this clarification, you'll be ready to continue with the main lesson."""
        except Exception as e:
            print(f"Error generating clarification with agent: {e}")
            # Fallback clarification
            clarification_content = f"""## Clarification: Understanding {question_id}

You selected: **{incorrect_answer}**

The correct answer is: **{correct_answer}**

### Why this is important:

This concept is fundamental to understanding {current_module}. Let me explain it more clearly.

### Key Concept:

{correct_answer} is the correct answer because it accurately represents the concept being tested.

### Example:

Consider this example: [The agent would generate a relevant example here]

### Moving Forward:

Once you understand this clarification, you can continue with the main lesson."""
        
        # Create clarification module metadata
        clarification_module = {
            "module_id": f"clarification_{question_id}_{int(time.time())}",
            "question_id": question_id,
            "question": question,
            "content": clarification_content,
            "source_module": current_module,
            "created_at": time.time(),
            "is_clarification": True
        }
        
        return clarification_module

    def complete_clarification(self, clarification_id: str) -> bool:
        """Mark a clarification as complete and remove it from pending list.
        
        Args:
            clarification_id: ID of the clarification module to complete
            
        Returns:
            True if clarification was found and removed, False otherwise
        """
        pending_clarifications = self.state_manager.state.get("pending_clarifications", [])
        original_count = len(pending_clarifications)
        
        # Remove the clarification with matching ID
        self.state_manager.state["pending_clarifications"] = [
            c for c in pending_clarifications if c.get("module_id") != clarification_id
        ]
        
        if len(self.state_manager.state["pending_clarifications"]) < original_count:
            self.state_manager.save_state()
            return True
        return False

    def get_next_lesson(self, skip_clarifications: bool = True) -> Dict:
        """Get the next lesson based on user state.

        Enhanced with Fastino insights for better personalization.
        By default, skips pending clarifications and shows regular lessons.
        Set skip_clarifications=False to show clarifications first.

        Returns:
            Dict with lesson info, content, and supporting materials
        """
        # Check for pending clarifications first (only if not skipping)
        if not skip_clarifications:
            pending_clarifications = self.state_manager.state.get("pending_clarifications", [])
            if pending_clarifications:
                # Return the first pending clarification
                clarification = pending_clarifications[0]
                return {
                    "module": "clarification",
                    "content": clarification["content"],
                    "difficulty": max(0, self.state_manager.get_current_difficulty() - 1),  # Easier for clarifications
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
        
        current_module = self.state_manager.get_current_module()

        # Skip diagnostic if we're past it
        if current_module == "diagnostic":
            current_module = "fundamentals"
            self.state_manager.update_module("fundamentals")

        # Get Fastino memories for personalized context (more active usage)
        fastino_context = ""
        fastino_insights = {}
        try:
            # Query multiple aspects for richer context
            struggle_memories = self.state_manager.get_fastino_memories(
                f"What topics or concepts has this user struggled with in {current_module}?",
                top_k=3
            )
            strength_memories = self.state_manager.get_fastino_memories(
                f"What topics or concepts has this user excelled at?",
                top_k=2
            )
            learning_patterns = self.state_manager.fastino.query_user_profile(
                self.user_id,
                f"What are this user's learning patterns and preferences for {current_module}?"
            )
            
            if struggle_memories:
                memory_texts = [m.get("content", "") for m in struggle_memories if m.get("content")]
                if memory_texts:
                    fastino_context += f"\nUser's past struggles: {', '.join(memory_texts[:2])}"
            
            if strength_memories:
                strength_texts = [m.get("content", "") for m in strength_memories if m.get("content")]
                if strength_texts:
                    fastino_context += f"\nUser's strengths: {', '.join(strength_texts[:1])}"
            
            if learning_patterns and learning_patterns.get("answer"):
                fastino_insights["learning_patterns"] = learning_patterns["answer"]
                fastino_context += f"\nLearning patterns: {learning_patterns['answer'][:200]}"
                
        except Exception as e:
            print(f"Fastino memory retrieval error: {e}")

        # Run lesson agent to determine content
        agent_context = {
            "user_id": self.user_id,
            "difficulty_level": self.state_manager.get_current_difficulty(),
            "current_module": current_module,
            "learning_style": self.state_manager.get_recommended_content_style(),
            "recent_performance": self.state_manager.state["quiz_performance"][-5:]
        }
        
        # Add Fastino context if available (more comprehensive)
        if fastino_context:
            agent_context["fastino_insights"] = fastino_context
        if fastino_insights:
            agent_context["fastino_insights_dict"] = fastino_insights
        
        # Use Fastino to predict optimal difficulty for this lesson
        if self.state_manager.fastino and self.state_manager.fastino.is_available():
            try:
                difficulty_prediction = self.state_manager.fastino.predict_decision(
                    self.user_id,
                    {
                        "decision_type": "lesson_difficulty",
                        "context": {
                            "module": current_module,
                            "current_difficulty": self.state_manager.get_current_difficulty(),
                            "recent_performance": agent_context["recent_performance"]
                        }
                    }
                )
                if difficulty_prediction and difficulty_prediction.get("recommended_difficulty") is not None:
                    predicted_diff = int(difficulty_prediction.get("recommended_difficulty", agent_context["difficulty_level"]))
                    agent_context["fastino_recommended_difficulty"] = max(0, min(3, predicted_diff))
            except Exception as e:
                print(f"Fastino difficulty prediction error: {e}")
        
        agent_result = run_liquidmetal_agent("lesson", agent_context)

        # Get current page index from state
        current_page = self.state_manager.state.get("current_page", 0)
        
        # Load the lesson content (with pagination support)
        module_file = agent_result.get("module_file", f"{current_module}.md")
        # Remove .md extension and handle pagination pattern (e.g., fundamentals_page1.md -> fundamentals)
        # But preserve underscores in module names (e.g., transformers_llms.md -> transformers_llms)
        module_name = module_file.replace(".md", "")
        # Remove _pageN pattern if present (for paginated files)
        module_name = re.sub(r'_page\d+$', '', module_name)
        
        # Get total pages for this module
        total_pages = self.get_module_page_count(module_name)
        
        # Load content for current page
        content = self.load_lesson_content(module_name, current_page)
        
        # Store lesson content for answer evaluation
        self.current_lesson_content = content

        # Get visual asset - try Gemini first, then Freepik
        freepik_search = agent_result.get("freepik_search", "AI concept")
        image_ref = None
        video_ref = None
        
        # Try Gemini for image/video generation
        if self.gemini_client and self.gemini_client.is_available():
            # Generate image using Gemini
            gemini_image = self.gemini_client.generate_image(
                concept=freepik_search,
                module=module_name,
                style="educational"
            )
            if gemini_image:
                image_ref = gemini_image
            
            # Generate video description/suggestion
            gemini_video = self.gemini_client.generate_video_description(
                concept=freepik_search,
                module=module_name
            )
            if gemini_video:
                video_ref = gemini_video
        
        # Fallback to Freepik if Gemini not available
        if not image_ref:
            image_ref = get_image_for_concept(freepik_search)
            if not image_ref:
                image_ref = None

        # Use the user's actual difficulty level from state (from diagnostic assessment)
        # Only override if agent explicitly returns a different difficulty_tag
        user_difficulty = self.state_manager.get_current_difficulty()
        lesson_difficulty = agent_result.get("difficulty_tag")
        # If agent didn't return a difficulty_tag, use the user's assessed level
        if lesson_difficulty is None:
            lesson_difficulty = user_difficulty

        # Log lesson event only if this is a new page/view (deduplication)
        # Check if we've already logged this exact page recently
        last_logged = self.state_manager.state.get("last_logged_lesson", {})
        last_module = last_logged.get("module")
        last_page = last_logged.get("page", -1)
        last_timestamp = last_logged.get("timestamp", 0)
        
        # Only log if:
        # 1. Different module, OR
        # 2. Different page within same module, OR  
        # 3. Same page but more than 5 minutes ago (user came back)
        should_log = (
            last_module != module_name or
            last_page != current_page or
            (time.time() - last_timestamp) > 300  # 5 minutes
        )
        
        if should_log:
            log_lesson_event({
                "user_id": self.user_id,
                "module": module_name,
                "difficulty_level": lesson_difficulty,
                "learning_style": agent_result.get("suggested_style", "text"),
                "timestamp": time.time()
            })
            
            # Update last logged lesson to prevent duplicate logging
            self.state_manager.state["last_logged_lesson"] = {
                "module": module_name,
                "page": current_page,
                "timestamp": time.time()
            }
            self.state_manager.save_state()

        # Limit check questions to 1 per page (max)
        # For fundamentals, assign questions to specific pages
        check_questions = agent_result.get("check_questions", [])
        
        # Get list of already-answered question IDs to filter them out
        answered_question_ids = set()
        for attempt in self.state_manager.state.get("quiz_performance", []):
            question_id = attempt.get("question_id", "")
            if question_id:
                answered_question_ids.add(question_id)
        
        if module_name == "fundamentals" and check_questions:
            # Map questions to pages (1 question per page)
            # Page 0: no question (intro)
            # Page 1: question about AI misconceptions
            # Page 2: question about LLMs
            # Page 3: question about tokens
            # Page 4: question about predictions
            # Page 5: no question (summary)
            question_page_map = {
                1: 0,  # First question on page 1
                2: 1 if len(check_questions) > 1 else 0,  # Second question on page 2
                3: 2 if len(check_questions) > 2 else (1 if len(check_questions) > 1 else 0),  # Third question on page 3
            }
            question_index = question_page_map.get(current_page, -1)
            if question_index >= 0 and question_index < len(check_questions):
                # Check if this question has already been answered
                potential_question_id = f"{module_name}_q{question_index}"
                if potential_question_id not in answered_question_ids:
                    # Include the global question index in the question data
                    # Create a copy to avoid mutating the original
                    original_question = check_questions[question_index]
                    if isinstance(original_question, dict):
                        question = original_question.copy()
                        question["global_index"] = question_index
                    else:
                        # Convert string question to dict format
                        question = {"question": original_question, "global_index": question_index}
                    check_questions = [question]
                else:
                    check_questions = []  # Question already answered, skip it
            else:
                check_questions = []  # No question for this page
        elif check_questions and len(check_questions) > 0:
            # For other modules, show max 1 question (filter out answered ones)
            for i, original_question in enumerate(check_questions):
                potential_question_id = f"{module_name}_q{i}"
                if potential_question_id not in answered_question_ids:
                    # Include the global question index
                    # Create a copy to avoid mutating the original
                    if isinstance(original_question, dict):
                        question = original_question.copy()
                        question["global_index"] = i
                    else:
                        question = {"question": original_question, "global_index": i}
                    check_questions = [question]
                    break
            else:
                # All questions already answered
                check_questions = []
        else:
            check_questions = []
        
        lesson_data = {
            "module": module_name,
            "content": content,
            "difficulty": lesson_difficulty,
            "check_questions": check_questions,
            "next_module": agent_result.get("next_module"),
            "learning_style": agent_result.get("suggested_style", "text"),
            "current_page": current_page,
            "total_pages": total_pages,
            "is_paginated": total_pages > 1
        }
        
        # Only include image_reference if we have a valid URL
        if image_ref:
            lesson_data["image_reference"] = image_ref
        
        # Include video reference if available
        if video_ref:
            lesson_data["video_reference"] = video_ref
        
        return lesson_data

    def evaluate_answer(self, question: str, user_answer: str, lesson_content: Optional[str] = None) -> Dict:
        """Evaluate a user's answer semantically and detect confusion signals.
        
        Args:
            question: The question that was asked
            user_answer: User's answer
            lesson_content: Optional lesson content for context
            
        Returns:
            Dict with:
                - is_correct: bool
                - is_confused: bool (detects frustration/confusion)
                - confidence: float (0-1)
                - reasoning: str
                - suggested_action: str (e.g., "simplify", "provide_examples", "continue")
        """
        user_answer_lower = user_answer.lower().strip()
        
        # Detect confusion/frustration signals
        confusion_phrases = [
            "all of it seems unclear", "i don't think you're listening", 
            "i don't understand", "i don't know", "don't know", "dunno",
            "this doesn't make sense", "confused", "unclear", "not listening", 
            "doesn't help", "still confused", "makes no sense", "i'm lost", 
            "no idea", "clueless", "have no idea", "not sure"
        ]
        
        is_confused = any(phrase in user_answer_lower for phrase in confusion_phrases)
        
        # If clearly confused, return immediately
        if is_confused:
            return {
                "is_correct": False,
                "is_confused": True,
                "confidence": 0.0,
                "reasoning": "User expressed confusion or frustration",
                "suggested_action": "simplify_and_examples"
            }
        
        # Use LLM for semantic evaluation if available
        if self.openai_client and len(user_answer.strip()) > 0:
            try:
                context = f"Lesson content: {lesson_content[:500] if lesson_content else 'N/A'}\n\n"
                prompt = f"""Evaluate this learning quiz answer. The question is: "{question}"

User's answer: "{user_answer}"

Evaluate:
1. Does the answer demonstrate understanding of the concept? (yes/no)
2. Is the user confused or frustrated? (yes/no)
3. Confidence level (0.0-1.0)
4. Brief reasoning

Respond in this exact format:
UNDERSTANDING: yes/no
CONFUSED: yes/no
CONFIDENCE: 0.0-1.0
REASONING: brief explanation
ACTION: simplify_and_examples/continue/provide_examples"""

                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an educational assessment AI. Evaluate student answers for understanding and detect confusion signals."},
                        {"role": "user", "content": context + prompt}
                    ],
                    temperature=0.3,
                    max_tokens=200
                )
                
                result_text = response.choices[0].message.content
                
                # Parse response
                is_correct = "UNDERSTANDING: yes" in result_text.lower()
                is_confused_detected = "CONFUSED: yes" in result_text.lower()
                confidence = 0.5
                reasoning = "LLM evaluation"
                action = "continue"
                
                # Extract confidence
                for line in result_text.split("\n"):
                    if "CONFIDENCE:" in line:
                        try:
                            confidence = float(line.split(":")[1].strip())
                        except:
                            pass
                    if "REASONING:" in line:
                        reasoning = line.split(":", 1)[1].strip() if ":" in line else reasoning
                    if "ACTION:" in line:
                        action = line.split(":", 1)[1].strip() if ":" in line else action
                
                return {
                    "is_correct": is_correct,
                    "is_confused": is_confused_detected or is_confused,
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "suggested_action": action
                }
            except Exception as e:
                # Fallback if LLM fails
                pass
        
        # Fallback: Simple heuristic (but better than before)
        # Check if answer is too short or contains confusion signals
        if len(user_answer.strip()) < 10:
            return {
                "is_correct": False,
                "is_confused": True,
                "confidence": 0.2,
                "reasoning": "Answer too short, likely indicates confusion",
                "suggested_action": "simplify_and_examples"
            }
        
        # Fallback: Evaluate based on answer length and content
        # This is a heuristic that works without LLM evaluation
        answer_length = len(user_answer.strip())
        answer_lower = user_answer.lower()
        
        # Check for key terms that suggest understanding (basic keyword matching)
        # This is a simple heuristic - not perfect but better than nothing
        understanding_indicators = [
            "pattern", "learn", "predict", "token", "model", "training",
            "data", "generate", "process", "input", "output", "neural",
            "algorithm", "autocomplete", "sequence", "context"
        ]
        
        has_keywords = any(indicator in answer_lower for indicator in understanding_indicators)
        
        # Mark as correct if:
        # 1. Answer is substantial (at least 20 chars) AND
        # 2. Either has relevant keywords OR is very detailed (50+ chars)
        # 3. Doesn't show confusion signals (already checked above)
        is_correct = answer_length >= 20 and (has_keywords or answer_length >= 50)
        
        return {
            "is_correct": is_correct,
            "is_confused": answer_length < 15,  # Short answers suggest confusion
            "confidence": 0.7 if (is_correct and answer_length > 40) else 0.5 if is_correct else 0.3,
            "reasoning": "Evaluated based on answer length and content" if is_correct else "Answer could be more detailed. Try to explain your understanding more fully.",
            "suggested_action": "continue"
        }

    def submit_quiz_answer(self, question_id: str, user_answer: str,
                          correct_answer: str, hesitation_seconds: float,
                          question: Optional[str] = None, is_correct_override: Optional[bool] = None) -> Dict:
        """Process a quiz answer and update user state.

        Args:
            question_id: ID of the question
            user_answer: User's answer
            correct_answer: The correct answer (for reference, may not be used if semantic eval is available)
            hesitation_seconds: Time taken to answer
            question: The question text (for semantic evaluation)

        Returns:
            Dict with feedback and adaptation decisions
        """
        # Use semantic evaluation instead of simple string matching
        # But if is_correct_override is provided (e.g., for MCQ), use that instead
        if is_correct_override is not None:
            is_correct = is_correct_override
            evaluation = {"is_correct": is_correct, "is_confused": False}
        else:
            evaluation = self.evaluate_answer(
                question or question_id,
                user_answer,
                self.current_lesson_content
            )
            is_correct = evaluation["is_correct"]
        
        is_confused = evaluation.get("is_confused", False)
        
        # If answer is incorrect, generate a clarification module
        if not is_correct:
            current_module = self.state_manager.get_current_module()
            # Only generate clarification if we're not already in a clarification module
            if current_module != "clarification":
                try:
                    clarification = self.generate_clarification_module(
                        question=question or question_id,
                        question_id=question_id,
                        incorrect_answer=user_answer,
                        correct_answer=correct_answer,
                        current_module=current_module
                    )
                    # Add to pending clarifications
                    if "pending_clarifications" not in self.state_manager.state:
                        self.state_manager.state["pending_clarifications"] = []
                    self.state_manager.state["pending_clarifications"].append(clarification)
                    self.state_manager.save_state()
                    print(f"Generated clarification module for question: {question_id}")
                except Exception as e:
                    print(f"Error generating clarification module: {e}")

        # Use Fastino for real-time struggle detection and intervention recommendations
        fastino_intervention = None
        if self.state_manager.fastino and self.state_manager.fastino.is_available():
            try:
                # Query Fastino for intervention recommendations
                intervention_query = f"""User answered question about {question_id}. 
                Answer was {'correct' if is_correct else 'incorrect'}. 
                Hesitation: {hesitation_seconds:.1f}s. 
                Should we provide additional help or intervention?"""
                
                intervention_result = self.state_manager.fastino.query_user_profile(
                    self.user_id,
                    intervention_query
                )
                
                if intervention_result and intervention_result.get("answer"):
                    fastino_intervention = intervention_result["answer"]
                    # If Fastino detects need for intervention, mark as confused
                    if "yes" in intervention_result["answer"].lower() or "help" in intervention_result["answer"].lower():
                        is_confused = True
            except Exception as e:
                print(f"Fastino intervention query error: {e}")

        # Check if this question has already been answered (deduplication)
        # Prevent duplicate logging from multiple submissions
        already_answered = False
        for attempt in self.state_manager.state.get("quiz_performance", []):
            if attempt.get("question_id") == question_id:
                already_answered = True
                break
        
        # Only process if not already answered
        if not already_answered:
            # Record in state manager (triggers self-evolving logic)
            self.state_manager.record_quiz_attempt(
                question_id, is_correct, hesitation_seconds
            )
            
            # If user is confused, trigger immediate adaptation
            if is_confused:
                # Decrease difficulty
                current_diff = self.state_manager.get_current_difficulty()
                if current_diff > 0:
                    self.state_manager.state["difficulty_level"] = max(0, current_diff - 1)
                # Switch to examples mode
                self.state_manager.set_learning_style("examples")
                self.state_manager.save_state()

            # Log to Daft (only once per question)
            log_quiz_attempt({
                "user_id": self.user_id,
                "question_id": question_id,
                "user_answer": user_answer,
                "answer": correct_answer,  # Keep for compatibility
                "correct": is_correct,
                "hesitation_seconds": hesitation_seconds,
                "timestamp": time.time(),
                "difficulty_level": self.state_manager.get_current_difficulty()
            })
        else:
            # Question already answered - just return feedback without logging
            # Still update state for confusion if needed (but don't log again)
            if is_confused:
                current_diff = self.state_manager.get_current_difficulty()
                if current_diff > 0:
                    self.state_manager.state["difficulty_level"] = max(0, current_diff - 1)
                self.state_manager.set_learning_style("examples")
                self.state_manager.save_state()

        # Get Fastino recommendations for next steps
        fastino_recommendation = None
        if self.state_manager.fastino and self.state_manager.fastino.is_available():
            try:
                recommendation = self.state_manager.fastino.query_user_profile(
                    self.user_id,
                    f"Based on this {'correct' if is_correct else 'incorrect'} answer with {hesitation_seconds:.1f}s hesitation, what should be the next learning action?"
                )
                if recommendation and recommendation.get("answer"):
                    fastino_recommendation = recommendation["answer"]
            except Exception as e:
                print(f"Fastino recommendation query error: {e}")

        # Determine feedback and adaptations
        feedback = {
            "correct": is_correct,
            "is_confused": is_confused,
            "confidence": evaluation.get("confidence", 0.5),
            "reasoning": evaluation.get("reasoning", ""),
            "previous_difficulty": self.state_manager.get_current_difficulty(),
            "new_difficulty": self.state_manager.get_current_difficulty(),
            "should_switch_to_examples": self.state_manager.should_switch_to_examples() or is_confused,
            "should_simplify": self.state_manager.should_simplify() or is_confused,
            "suggested_action": evaluation.get("suggested_action", "continue"),
            "fastino_intervention": fastino_intervention,
            "fastino_recommendation": fastino_recommendation
        }

        # Update difficulty level was already done in record_quiz_attempt
        if feedback["previous_difficulty"] != self.state_manager.get_current_difficulty():
            feedback["difficulty_changed"] = True
            feedback["change_direction"] = "increased" if self.state_manager.get_current_difficulty() > feedback["previous_difficulty"] else "decreased"

        return feedback

    def advance_to_next_page(self) -> Dict:
        """Advance to the next page within the current module, or next module if on last page.

        Returns:
            Dict with 'advanced' (bool), 'coming_soon' (bool), and optional 'message' (str) keys.
            If coming_soon is True, the next modules are not yet available.
        """
        current_module = self.state_manager.get_current_module()
        current_page = self.state_manager.state.get("current_page", 0)
        total_pages = self.get_module_page_count(current_module)
        
        # Check if there are more pages in current module
        if current_page + 1 < total_pages:
            # Advance to next page
            self.state_manager.state["current_page"] = current_page + 1
            self.state_manager.save_state()
            return {"advanced": True, "coming_soon": False}
        else:
            # On last page, advance to next module
            self.state_manager.state["current_page"] = 0  # Reset page for new module
            result = self.advance_to_next_module()
            return result

    def advance_to_next_module(self) -> Dict:
        """Advance to the next module in the sequence.

        Returns:
            Dict with 'advanced' (bool) and 'coming_soon' (bool) keys.
            If coming_soon is True, the next modules are not yet available.
        """
        module_sequence = ["fundamentals", "transformers_llms", "agents", "build_todo_agent"]
        current = self.state_manager.get_current_module()

        if current in module_sequence:
            current_idx = module_sequence.index(current)
            if current_idx < len(module_sequence) - 1:
                next_module = module_sequence[current_idx + 1]
                
                # Check if next module is "agents" or "build_todo_agent" (coming soon)
                if next_module in ["agents", "build_todo_agent"]:
                    return {
                        "advanced": False,
                        "coming_soon": True,
                        "message": "AI Agents and Capstone modules are coming soon! Stay tuned for updates."
                    }
                
                # Otherwise, advance normally
                self.state_manager.update_module(next_module)
                return {
                    "advanced": True,
                    "coming_soon": False
                }

        return {
            "advanced": False,
            "coming_soon": False
        }

    def run_capstone(self, task_description: str) -> Dict:
        """Generate and run capstone project.

        Enhanced with Fastino to personalize based on user's learning history.

        Args:
            task_description: Description of what the agent should do

        Returns:
            Dict with generated agent code and instructions
        """
        # Get Fastino insights about user's learning patterns
        fastino_insights = ""
        try:
            memories = self.state_manager.get_fastino_memories(
                "What are this user's learning preferences and strengths?",
                top_k=3
            )
            if memories:
                insights = [m.get("content", "") for m in memories if m.get("content")]
                if insights:
                    fastino_insights = f"\nUser learning profile: {', '.join(insights[:2])}"
        except Exception as e:
            print(f"Fastino insights error: {e}")
        
        # Ingest capstone request into Fastino
        if self.state_manager.fastino and self.state_manager.fastino.is_available():
            self.state_manager.fastino.ingest_event(
                self.user_id,
                "capstone_request",
                {
                    "task_description": task_description,
                    "completed_modules": self.state_manager.state["completed_modules"]
                },
                {"timestamp": time.time()}
            )
        
        # Run capstone agent with Fastino context
        capstone_context = {
            "user_id": self.user_id,
            "task_description": task_description
        }
        if fastino_insights:
            capstone_context["fastino_insights"] = fastino_insights
        
        result = run_liquidmetal_agent("capstone", capstone_context)

        # Mark capstone as completed
        self.state_manager.update_module("capstone_completed")

        # Log completion
        log_lesson_event({
            "user_id": self.user_id,
            "module": "capstone",
            "event": "completed",
            "task_description": task_description,
            "timestamp": time.time()
        })

        return result

    def get_progress_summary(self) -> Dict:
        """Get comprehensive progress summary.

        Returns:
            Dict with user progress and statistics
        """
        summary = self.state_manager.get_progress_summary()

        # Add learning insights
        summary["adaptations"] = {
            "current_difficulty": self.state_manager.get_current_difficulty(),
            "recommended_style": self.state_manager.get_recommended_content_style(),
            "should_use_examples": self.state_manager.should_switch_to_examples(),
            "should_simplify": self.state_manager.should_simplify()
        }

        # Add recent performance trend
        if len(self.state_manager.state["quiz_performance"]) >= 3:
            recent = self.state_manager.state["quiz_performance"][-3:]
            summary["recent_trend"] = {
                "accuracy": sum(1 for a in recent if a["correct"]) / len(recent),
                "avg_hesitation": sum(a["hesitation_seconds"] for a in recent) / len(recent)
            }

        return summary

    def reset_user_state(self):
        """Reset user state (for testing or restart)."""
        self.state_manager.state = {
            "user_id": self.user_id,
            "current_module": "diagnostic",
            "difficulty_level": 1,
            "completed_modules": [],
            "quiz_performance": [],
            "hesitation_history": [],
            "preferred_learning_style": None,
            "created_at": time.time(),
            "last_active": time.time()
        }
        self.state_manager.save_state()

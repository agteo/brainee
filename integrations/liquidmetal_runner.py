"""LiquidMetal Agent Runner - Primary AI Agent Reasoning Engine.

Uses LiquidMetal AI SDK to run intelligent agents defined in /agent/*.liquidmetal.md files.
Falls back to OpenAI or rule-based logic if LiquidMetal is unavailable.
"""

import os
import random
from pathlib import Path
from typing import Dict, Optional

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try to import LiquidMetal SDK (try multiple possible package names)
LIQUIDMETAL_AVAILABLE = False
liquidmetal = None

try:
    # Try lm-raindrop (official package name)
    import lm_raindrop as liquidmetal
    LIQUIDMETAL_AVAILABLE = True
except ImportError:
    try:
        # Try alternative import name
        import raindrop as liquidmetal
        LIQUIDMETAL_AVAILABLE = True
    except ImportError:
        try:
            # Try legacy name
            import liquidmetal
            LIQUIDMETAL_AVAILABLE = True
        except ImportError:
            LIQUIDMETAL_AVAILABLE = False
            print("Warning: LiquidMetal SDK not found. Install with: pip install lm-raindrop")

# Fallback to OpenAI if needed
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class LiquidMetalRunner:
    """Runs agent reasoning using LiquidMetal AI SDK."""

    # Class-level usage tracking (shared across instances)
    _usage_stats = {
        'total_agent_calls': 0,
        'diagnostic_calls': 0,
        'lesson_calls': 0,
        'capstone_calls': 0,
        'successful_calls': 0,
        'failed_calls': 0,
        'fallback_to_openai': 0,
        'fallback_to_heuristics': 0,
        'last_used': None
    }

    def __init__(self, api_key: Optional[str] = None):
        self.agent_dir = Path(__file__).resolve().parents[1] / "agent"
        self.content_dir = Path(__file__).resolve().parents[1] / "content"

        # Initialize Gemini client for MCQ generation
        try:
            from integrations.gemini_client import GeminiClient
            self.gemini_client = GeminiClient()
        except Exception as e:
            print(f"Gemini client initialization error: {e}")
            self.gemini_client = None

        # Initialize LiquidMetal client
        if LIQUIDMETAL_AVAILABLE:
            try:
                # Try different client initialization methods
                # Check multiple environment variable names for compatibility
                api_key = api_key or os.getenv("RAINDROP_API_KEY") or os.getenv("LIQUIDMETAL_API_KEY") or os.getenv("LM_API_KEY")
                
                # If we found an API key from any source, ensure it's set as RAINDROP_API_KEY
                # (the SDK expects this specific name)
                if api_key and not os.getenv("RAINDROP_API_KEY"):
                    os.environ["RAINDROP_API_KEY"] = api_key
                elif not api_key:
                    # Debug: Check what environment variables are available
                    env_vars_found = []
                    for var_name in ["RAINDROP_API_KEY", "LIQUIDMETAL_API_KEY", "LM_API_KEY"]:
                        if os.getenv(var_name):
                            env_vars_found.append(var_name)
                    if not env_vars_found:
                        print("Warning: No API key found in environment variables (RAINDROP_API_KEY, LIQUIDMETAL_API_KEY, or LM_API_KEY)")
                
                # Initialize client - SDK will read from environment if api_key is None
                if hasattr(liquidmetal, 'Client'):
                    self.liquidmetal_client = liquidmetal.Client(api_key=api_key) if api_key else liquidmetal.Client()
                elif hasattr(liquidmetal, 'RaindropClient'):
                    self.liquidmetal_client = liquidmetal.RaindropClient(api_key=api_key) if api_key else liquidmetal.RaindropClient()
                else:
                    # If no Client class, try direct initialization
                    self.liquidmetal_client = liquidmetal
            except Exception as e:
                print(f"Warning: Could not initialize LiquidMetal client: {e}")
                self.liquidmetal_client = None
        else:
            self.liquidmetal_client = None

        # Fallback OpenAI client
        if OPENAI_AVAILABLE and not LIQUIDMETAL_AVAILABLE:
            self.openai_client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        else:
            self.openai_client = None

    def _load_agent_definition(self, agent_name: str) -> str:
        """Load agent definition from .liquidmetal.md file."""
        agent_file = self.agent_dir / f"{agent_name}_agent.liquidmetal.md"
        if agent_file.exists():
            with open(agent_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _load_prompts(self, prompt_type: str) -> str:
        """Load prompts from content/prompts."""
        prompt_file = self.content_dir / "prompts" / f"{prompt_type}_prompts.md"
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _call_liquidmetal_agent(self, agent_definition: str, context: Dict, output_schema: Dict) -> Optional[Dict]:
        """Call LiquidMetal agent with different possible API methods."""
        if not self.liquidmetal_client:
            return None
        
        try:
            result = None
            # Try run_agent method (expected API)
            if hasattr(self.liquidmetal_client, 'run_agent'):
                result = self.liquidmetal_client.run_agent(
                    agent_definition=agent_definition,
                    context=context,
                    output_schema=output_schema
                )
            # Try execute_agent method
            elif hasattr(self.liquidmetal_client, 'execute_agent'):
                result = self.liquidmetal_client.execute_agent(
                    agent_definition=agent_definition,
                    context=context,
                    output_schema=output_schema
                )
            # Try invoke method
            elif hasattr(self.liquidmetal_client, 'invoke'):
                result = self.liquidmetal_client.invoke(
                    agent_definition=agent_definition,
                    context=context,
                    output_schema=output_schema
                )
            # Try direct call with agent definition
            elif callable(self.liquidmetal_client):
                result = self.liquidmetal_client(
                    agent_definition=agent_definition,
                    context=context,
                    output_schema=output_schema
                )
            
            if result:
                self._usage_stats['successful_calls'] += 1
                self._usage_stats['last_used'] = datetime.now().isoformat()
            else:
                self._usage_stats['failed_calls'] += 1
            
            return result
        except Exception as e:
            print(f"LiquidMetal API call failed: {e}")
            self._usage_stats['failed_calls'] += 1
            return None
    
    @classmethod
    def get_usage_stats(cls) -> Dict:
        """Get usage statistics for admin dashboard."""
        return cls._usage_stats.copy()

    def run_diagnostic_agent(self, inputs: Dict) -> Dict:
        """Run diagnostic agent to assess user level using LiquidMetal."""
        self._usage_stats['total_agent_calls'] += 1
        self._usage_stats['diagnostic_calls'] += 1
        
        agent_def = self._load_agent_definition("diagnostic")
        prompts = self._load_prompts("diagnostic")

        user_input = inputs.get("raw_input", "")
        hesitation = inputs.get("hesitation_seconds", 0)

        # Priority 1: Use LiquidMetal SDK
        if self.liquidmetal_client and user_input:
            result = self._call_liquidmetal_agent(
                agent_definition=agent_def,
                context={
                    "user_input": user_input,
                    "hesitation_seconds": hesitation,
                    "prompts": prompts
                },
                output_schema={
                    "next_mode": str,
                    "assessed_level": int,
                    "reasoning": str,
                    "question_payload": dict
                }
            )
            if result:
                return result

        # Get current question index from inputs (0-based)
        question_index = inputs.get("question_index", 0)
        
        # Define 5 diagnostic questions - first one is standard for fast loading
        # Questions progress from basic to more advanced concepts
        # Each question has 5 options: 4 real options (correct answer among them) + "I'm not sure" as 5th option
        diagnostic_questions = [
            {
                "question": "What is a Large Language Model (LLM)?",
                "options": [
                    "A tool that predicts the next piece of text based on patterns it has learned",
                    "A physical robot that can move and talk",
                    "A spreadsheet full of formulas",
                    "A type of computer hardware component",
                    "I'm not sure"
                ],
                "correct_answer": 0,
                "difficulty_weight": 1  # Beginner question
            },
            {
                "question": "What does 'tokenization' mean in the context of LLMs?",
                "options": [
                    "Breaking text into smaller pieces (words or subwords) that the model can process",
                    "Creating security tokens for API access",
                    "Converting text to binary code",
                    "Encrypting data for secure transmission",
                    "I'm not sure"
                ],
                "correct_answer": 0,
                "difficulty_weight": 1  # Beginner question
            },
            {
                "question": "What is the Transformer architecture?",
                "options": [
                    "A neural network design that uses self-attention to process sequences",
                    "A type of database for storing AI models",
                    "A programming language for AI development",
                    "A hardware device for processing graphics",
                    "I'm not sure"
                ],
                "correct_answer": 0,
                "difficulty_weight": 2  # Intermediate question
            },
            {
                "question": "What is 'self-attention' in Transformers?",
                "options": [
                    "A mechanism where each word can attend to all other words in the sequence",
                    "A way to make models pay attention to themselves",
                    "A debugging technique for neural networks",
                    "A method for training models faster",
                    "I'm not sure"
                ],
                "correct_answer": 0,
                "difficulty_weight": 2  # Intermediate question
            },
            {
                "question": "What are the main components of an AI agent system?",
                "options": [
                    "Reasoning engine, tools/APIs, and memory/context",
                    "Only a large language model",
                    "Just code and data files",
                    "Hardware components like GPUs and CPUs",
                    "I'm not sure"
                ],
                "correct_answer": 0,
                "difficulty_weight": 3  # Advanced question
            }
        ]
        
        # Return the question at the current index
        if question_index < len(diagnostic_questions):
            current_question = diagnostic_questions[question_index]
            
            # Randomize option order to prevent correct answer always being first
            # Keep "I'm not sure" (5th option, index 4) always at the end
            original_options = current_question["options"].copy()
            original_correct = current_question["correct_answer"]
            
            # Separate the first 4 options from "I'm not sure" (index 4)
            first_four_options = original_options[:4]
            not_sure_option = original_options[4]  # "I'm not sure" - always at index 4
            
            # Create list of (option, original_index) tuples for first 4 options only
            indexed_options = [(opt, idx) for idx, opt in enumerate(first_four_options)]
            # Shuffle only the first 4 options
            random.shuffle(indexed_options)
            
            # Find where the correct answer moved to (only among first 4 options)
            shuffled_options = []
            new_correct_index = -1
            for new_idx, (option, orig_idx) in enumerate(indexed_options):
                shuffled_options.append(option)
                if orig_idx == original_correct:
                    new_correct_index = new_idx
            
            # Ensure we found the correct answer (should always be true since correct is in first 4)
            if new_correct_index == -1:
                new_correct_index = 0  # Fallback
            
            # Always append "I'm not sure" as the 5th option (index 4)
            shuffled_options.append(not_sure_option)
            
            return {
                "next_mode": "multiple_choice",
                "question_index": question_index,
                "total_questions": len(diagnostic_questions),
                "question_payload": {
                    "question": current_question["question"],
                    "options": shuffled_options,
                    "correct_answer": new_correct_index,
                    "difficulty_weight": current_question["difficulty_weight"]
                },
                "reasoning": f"Diagnostic question {question_index + 1} of {len(diagnostic_questions)}"
            }
        else:
            # All questions answered - this shouldn't happen in normal flow
            return {
                "next_mode": "complete",
                "reasoning": "All diagnostic questions completed"
            }

    def run_lesson_agent(self, inputs: Dict) -> Dict:
        """Run lesson agent to select appropriate content using LiquidMetal."""
        self._usage_stats['total_agent_calls'] += 1
        self._usage_stats['lesson_calls'] += 1
        
        agent_def = self._load_agent_definition("lesson")

        difficulty = inputs.get("difficulty_level", 1)
        current_module = inputs.get("current_module", "fundamentals")
        recent_performance = inputs.get("recent_performance", [])
        learning_style = inputs.get("learning_style", "text")

        # Priority 1: Use LiquidMetal SDK (for demo, prioritize LiquidMetal for question generation)
        if self.liquidmetal_client:
            result = self._call_liquidmetal_agent(
                agent_definition=agent_def,
                context={
                    "difficulty_level": difficulty,
                    "current_module": current_module,
                    "recent_performance": recent_performance,
                    "learning_style": learning_style,
                    "generate_questions": True  # Explicitly request question generation
                },
                output_schema={
                    "module_file": str,
                    "difficulty_tag": int,
                    "freepik_search": str,
                    "check_questions": list,
                    "suggested_style": str,
                    "next_module": str
                }
            )
            if result and result.get("check_questions"):
                # LiquidMetal generated questions successfully
                return result
            elif result:
                # LiquidMetal worked but didn't generate questions, try to generate them separately
                # Continue to fallback logic below
                pass

        # Fallback to heuristics
        self._usage_stats['fallback_to_heuristics'] += 1
        
        # Map module progression
        module_sequence = ["fundamentals", "transformers_llms", "agents", "build_todo_agent"]

        # Determine Freepik search term based on module
        freepik_terms = {
            "fundamentals": "artificial intelligence basics",
            "transformers_llms": "neural network transformer diagram",
            "agents": "AI agent workflow illustration",
            "build_todo_agent": "task management system"
        }

        # Generate check questions - prioritize LiquidMetal for demo
        # For fundamentals: generate open-ended questions to analyze understanding
        # For other modules: generate MCQs
        # Try LiquidMetal first, then Gemini, then predefined questions
        check_questions = []
        
        # Module-specific topics for question generation
        module_topics = {
            "fundamentals": "tokens, LLMs, and basic AI concepts",
            "transformers_llms": "Transformer architecture and self-attention",
            "agents": "AI agent components and decision-making",
            "build_todo_agent": "task management agents and tools"
        }
        
        topic = module_topics.get(current_module, "AI concepts")
        
        # Priority 1: Try LiquidMetal to generate questions (for demo)
        # Generate a mix of MCQ and open-ended questions
        if self.liquidmetal_client and not check_questions:
            try:
                # Generate a mix: 1 MCQ + 1 open-ended question
                question_agent_def = f"""Generate 2 questions about: {topic}
                    
Difficulty level: {difficulty} (0=beginner, 1=intermediate, 2=advanced, 3=expert)
Module: {current_module}

Generate a MIX of question types:
1. One multiple-choice question (MCQ) with format:
   - question: The question text
   - options: List of 4 options (A, B, C, D)
   - correct_answer: Index of correct option (0-3)

2. One open-ended question with format:
   - question: The question text (should require a thoughtful explanation, not just a one-word answer)

The questions should:
- Test the learner's understanding of key concepts
- Mix recall (MCQ) with deep understanding (open-ended)
- Be clear and specific
- Cover different aspects of the topic

Return both questions in the questions list."""
                
                question_result = self._call_liquidmetal_agent(
                    agent_definition=question_agent_def,
                    context={
                        "topic": topic,
                        "difficulty": difficulty,
                        "module": current_module,
                        "recent_performance": recent_performance
                    },
                    output_schema={
                        "questions": list  # List of {question, ...} or {question, options, correct_answer}
                    }
                )
                
                if question_result and question_result.get("questions"):
                    check_questions = question_result["questions"]
                    print(f"Generated {len(check_questions)} questions using LiquidMetal")
            except Exception as e:
                print(f"LiquidMetal question generation error: {e}")
                # Fall through to Gemini
        
        # Priority 2: Generate questions using Gemini if LiquidMetal didn't work
        # Generate a mix: 1 MCQ + 1 open-ended
        if not check_questions and self.gemini_client and self.gemini_client.is_available():
            try:
                # Generate one MCQ
                mcq_question = self.gemini_client.generate_mcq_question(
                    topic=topic,
                    difficulty=difficulty,
                    context=f"Module: {current_module}"
                )
                if mcq_question:
                    check_questions.append(mcq_question)
                
                # Generate one open-ended question
                open_ended_question = self.gemini_client.generate_open_ended_question(
                    topic=topic,
                    difficulty=difficulty,
                    context=f"Module: {current_module}"
                )
                if open_ended_question:
                    check_questions.append(open_ended_question)
            except Exception as e:
                print(f"Error generating questions with Gemini: {e}")
                # Continue to fallback
        
        # Fallback to predefined questions if Gemini not available or failed
        # Use a mix of MCQ and open-ended questions for all modules
        if not check_questions:
            predefined_questions = {
                "fundamentals": [
                    {
                        "question": "What is the primary difference between AI and a simple database lookup?",
                        "options": [
                            "AI generates responses based on learned patterns, while databases retrieve stored information",
                            "AI is faster than databases",
                            "AI uses more storage space",
                            "Databases are more accurate than AI"
                        ],
                        "correct_answer": 0
                    },
                    {
                        "question": "How do Large Language Models (LLMs) actually work? Describe the process in simple terms."
                    }
                ],
                "transformers_llms": [
                    {
                        "question": "What is the key innovation of the Transformer architecture?",
                        "options": [
                            "Self-attention mechanism that processes all words simultaneously",
                            "Using more layers than previous models",
                            "Training on larger datasets",
                            "Using GPUs for computation"
                        ],
                        "correct_answer": 0
                    },
                    {
                        "question": "Explain how self-attention allows a Transformer model to understand context better than previous architectures."
                    }
                ],
                "agents": [
                    {
                        "question": "What are the main components of an AI agent?",
                        "options": [
                            "Reasoning, tools, and memory",
                            "Only neural networks",
                            "Just code and data",
                            "Only APIs"
                        ],
                        "correct_answer": 0
                    },
                    {
                        "question": "Describe how an AI agent uses reasoning, tools, and memory together to complete a task. Give an example."
                    }
                ],
                "build_todo_agent": [
                    {
                        "question": "What type of tasks would a todo agent typically handle?",
                        "options": [
                            "Managing tasks, reminders, and schedules",
                            "Playing video games",
                            "Cooking recipes",
                            "Driving cars"
                        ],
                        "correct_answer": 0
                    },
                    {
                        "question": "Explain what tools and capabilities a todo agent would need to effectively help someone manage their tasks and schedule."
                    }
                ]
            }
            check_questions = predefined_questions.get(current_module, [])

        return {
            "module_file": f"{current_module}.md",
            "difficulty_tag": difficulty,
            "freepik_search": freepik_terms.get(current_module, "AI concept"),
            "check_questions": check_questions,  # Already a list, not a dict
            "suggested_style": learning_style,
            "next_module": module_sequence[min(module_sequence.index(current_module) + 1, len(module_sequence) - 1)] if current_module in module_sequence else current_module
        }

    def run_capstone_agent(self, inputs: Dict) -> Dict:
        """Run capstone agent to generate todo agent code using LiquidMetal."""
        self._usage_stats['total_agent_calls'] += 1
        self._usage_stats['capstone_calls'] += 1
        
        task_description = inputs.get("task_description", "manage daily tasks")
        agent_def = self._load_agent_definition("capstone")

        # Priority 1: Use LiquidMetal SDK
        if self.liquidmetal_client:
            result = self._call_liquidmetal_agent(
                agent_definition=agent_def,
                context={
                    "task_description": task_description
                },
                output_schema={
                    "agent_code": str,
                    "agent_description": str,
                    "next_steps": list
                }
            )
            if result:
                return result

        # Fallback to template generation
        self._usage_stats['fallback_to_heuristics'] += 1
        
        # Generate simple agent template
        agent_code = f"""# Simple To-Do Agent
# Task: {task_description}

class TodoAgent:
    def __init__(self):
        self.tasks = []
        self.completed = []

    def add_task(self, task: str, priority: str = "medium"):
        '''Add a new task.'''
        self.tasks.append({{"task": task, "priority": priority}})
        return f"Added: {{task}}"

    def complete_task(self, task_index: int):
        '''Mark a task as completed.'''
        if 0 <= task_index < len(self.tasks):
            completed = self.tasks.pop(task_index)
            self.completed.append(completed)
            return f"Completed: {{completed['task']}}"
        return "Invalid task index"

    def list_tasks(self):
        '''List all pending tasks.'''
        if not self.tasks:
            return "No pending tasks!"
        return "\\n".join([f"{{i}}. [{{t['priority']}}] {{t['task']}}"
                          for i, t in enumerate(self.tasks)])

    def run(self):
        '''Main agent loop.'''
        print("Todo Agent initialized for: {task_description}")
        print(self.list_tasks())


# Demo usage
if __name__ == "__main__":
    agent = TodoAgent()
    agent.add_task("Learn about AI fundamentals", "high")
    agent.add_task("Build my first agent", "high")
    agent.add_task("Celebrate completion", "medium")
    agent.run()
"""

        return {
            "agent_code": agent_code,
            "agent_description": f"A simple todo agent for: {task_description}",
            "next_steps": [
                "Review the generated code",
                "Run it to see how it works",
                "Customize it for your specific needs",
                "Add more features as you learn"
            ]
        }


# Module-level function for backward compatibility
def run_liquidmetal_agent(agent_name: str, inputs: dict) -> dict:
    """Run a LiquidMetal agent.

    Args:
        agent_name: One of 'diagnostic', 'lesson', 'capstone'.
        inputs: Dict of inputs for the agent.

    Returns:
        Dict representing the agent's decision/output.
    """
    runner = LiquidMetalRunner()

    if agent_name == "diagnostic":
        return runner.run_diagnostic_agent(inputs)
    elif agent_name == "lesson":
        return runner.run_lesson_agent(inputs)
    elif agent_name == "capstone":
        return runner.run_capstone_agent(inputs)
    else:
        return {
            "error": f"Unknown agent: {agent_name}",
            "valid_agents": ["diagnostic", "lesson", "capstone"]
        }

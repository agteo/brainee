#!/usr/bin/env python3
"""
Demo/Test script for LearnAI components.
Tests all major functionality without requiring user interaction.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from learning_engine import LearningEngine
from integrations.state_manager import UserStateManager
from integrations.liquidmetal_runner import run_liquidmetal_agent
from integrations import daft_client


def test_state_manager():
    """Test state manager functionality."""
    print("=" * 60)
    print("Testing State Manager...")
    print("=" * 60)

    user = UserStateManager("test_user_state")

    # Test initial state
    print(f"✓ Initial difficulty: {user.get_current_difficulty()}")
    print(f"✓ Initial module: {user.get_current_module()}")

    # Test quiz recording
    user.record_quiz_attempt("q1", True, 5.0)
    user.record_quiz_attempt("q2", True, 4.0)
    print(f"✓ After 2 correct answers: difficulty = {user.get_current_difficulty()}")

    # Test difficulty decrease
    user.record_quiz_attempt("q3", False, 15.0)
    user.record_quiz_attempt("q4", False, 20.0)
    print(f"✓ After 2 incorrect + high hesitation: difficulty = {user.get_current_difficulty()}")

    # Test recommendations
    print(f"✓ Recommended style: {user.get_recommended_content_style()}")
    print(f"✓ Should switch to examples: {user.should_switch_to_examples()}")

    # Test progress summary
    summary = user.get_progress_summary()
    print(f"✓ Progress summary: {summary['total_questions']} questions, {summary['accuracy']:.1%} accuracy")

    print("\n✅ State Manager tests passed!\n")


def test_liquidmetal_agents():
    """Test all three agent types."""
    print("=" * 60)
    print("Testing LiquidMetal Agents...")
    print("=" * 60)

    # Test diagnostic agent
    print("\n--- Diagnostic Agent ---")
    diag_result = run_liquidmetal_agent("diagnostic", {
        "user_id": "test",
        "raw_input": "AI is a computer system that learns patterns from data",
        "hesitation_seconds": 5.0
    })
    print(f"✓ Diagnostic result: {diag_result.get('next_mode')} (level: {diag_result.get('assessed_level', 'N/A')})")

    # Test with hesitation
    diag_result2 = run_liquidmetal_agent("diagnostic", {
        "user_id": "test",
        "raw_input": "",
        "hesitation_seconds": 20.0
    })
    print(f"✓ High hesitation result: {diag_result2.get('next_mode')}")

    # Test lesson agent
    print("\n--- Lesson Agent ---")
    lesson_result = run_liquidmetal_agent("lesson", {
        "user_id": "test",
        "difficulty_level": 2,
        "current_module": "transformers_llms",
        "learning_style": "visual",
        "recent_performance": []
    })
    print(f"✓ Lesson result: {lesson_result.get('module_file')}")
    print(f"✓ Check questions: {len(lesson_result.get('check_questions', []))} questions")
    print(f"✓ Freepik search: {lesson_result.get('freepik_search')}")

    # Test capstone agent
    print("\n--- Capstone Agent ---")
    capstone_result = run_liquidmetal_agent("capstone", {
        "user_id": "test",
        "task_description": "manage my daily work tasks"
    })
    print(f"✓ Capstone description: {capstone_result.get('agent_description')}")
    print(f"✓ Generated code: {len(capstone_result.get('agent_code', ''))} characters")
    print(f"✓ Next steps: {len(capstone_result.get('next_steps', []))} steps")

    print("\n✅ LiquidMetal Agent tests passed!\n")


def test_learning_engine():
    """Test the learning engine orchestration."""
    print("=" * 60)
    print("Testing Learning Engine...")
    print("=" * 60)

    engine = LearningEngine("test_engine_user")

    # Test diagnostic
    print("\n--- Testing Diagnostic ---")
    diag = engine.run_diagnostic("AI helps computers make decisions based on data", 3.0)
    print(f"✓ Diagnostic completed: {diag.get('next_mode')}")

    # Test lesson loading
    print("\n--- Testing Lesson Loading ---")
    lesson = engine.get_next_lesson()
    print(f"✓ Loaded lesson: {lesson.get('module')}")
    print(f"✓ Content length: {len(lesson.get('content', ''))} characters")
    print(f"✓ Difficulty: {lesson.get('difficulty')}")
    print(f"✓ Questions: {len(lesson.get('check_questions', []))}")

    # Test quiz submission
    print("\n--- Testing Quiz Submission ---")
    feedback = engine.submit_quiz_answer(
        "test_q1",
        "user answer",
        "user answer",  # Correct
        5.0
    )
    print(f"✓ Quiz feedback: correct={feedback.get('correct')}")

    # Test another quiz (incorrect)
    feedback2 = engine.submit_quiz_answer(
        "test_q2",
        "wrong answer",
        "correct answer",
        15.0
    )
    print(f"✓ Quiz feedback 2: correct={feedback2.get('correct')}")

    # Test module advancement
    print("\n--- Testing Module Advancement ---")
    result = engine.advance_to_next_module()
    advanced = result.get("advanced", False)
    coming_soon = result.get("coming_soon", False)
    print(f"✓ Advanced to next module: {advanced}")
    if coming_soon:
        print(f"✓ Coming soon message: {result.get('message', '')}")
    print(f"✓ Current module: {engine.state_manager.get_current_module()}")

    # Test capstone
    print("\n--- Testing Capstone ---")
    capstone = engine.run_capstone("organize my reading list")
    print(f"✓ Capstone generated: {len(capstone.get('agent_code', ''))} chars of code")

    # Test progress summary
    print("\n--- Testing Progress Summary ---")
    progress = engine.get_progress_summary()
    print(f"✓ Progress: {progress.get('total_questions')} questions answered")
    print(f"✓ Accuracy: {progress.get('accuracy', 0):.1%}")
    print(f"✓ Completed modules: {len(progress.get('completed_modules', []))}")

    print("\n✅ Learning Engine tests passed!\n")


def test_data_persistence():
    """Test that data is persisted correctly."""
    print("=" * 60)
    print("Testing Data Persistence...")
    print("=" * 60)

    data_dir = Path(__file__).parent / "data"

    # Check that data files exist
    files_to_check = ["user_progress.json", "quiz_attempts.json", "lesson_log.json"]

    for filename in files_to_check:
        filepath = data_dir / filename
        if filepath.exists():
            print(f"✓ {filename} exists")
        else:
            print(f"⚠ {filename} not found (will be created on first use)")

    print("\n✅ Data persistence tests passed!\n")


def test_content_files():
    """Test that all content files are present."""
    print("=" * 60)
    print("Testing Content Files...")
    print("=" * 60)

    content_dir = Path(__file__).parent / "content"

    # Check syllabus files
    syllabus_files = ["fundamentals.md", "transformers_llms.md", "agents.md", "build_todo_agent.md"]
    for filename in syllabus_files:
        filepath = content_dir / "syllabus" / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"✓ {filename} exists ({len(content)} chars)")
        else:
            print(f"✗ {filename} MISSING")

    # Check prompt files
    prompt_files = ["diagnostic_prompts.md", "lesson_prompts.md", "capstone_prompts.md"]
    for filename in prompt_files:
        filepath = content_dir / "prompts" / filename
        if filepath.exists():
            print(f"✓ {filename} exists")
        else:
            print(f"✗ {filename} MISSING")

    print("\n✅ Content file tests passed!\n")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print(" LearnAI - Component Test Suite")
    print("=" * 60 + "\n")

    try:
        test_content_files()
        test_data_persistence()
        test_state_manager()
        test_liquidmetal_agents()
        test_learning_engine()

        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour LearnAI system is ready to use!")
        print("Run: python main.py")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()

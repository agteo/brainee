#!/usr/bin/env python3
"""
LearnAI - Adaptive AI Learning Agent
Main entry point for the self-evolving learning system.
"""

import sys
import argparse
from pathlib import Path

from learning_engine import LearningEngine
from cli_interface import CLIInterface


class LearnAIApp:
    """Main application class for LearnAI."""

    def __init__(self, user_id: str = "demo_user"):
        self.user_id = user_id
        self.engine = LearningEngine(user_id)
        self.cli = CLIInterface()

    def run_diagnostic_phase(self):
        """Run the initial diagnostic assessment."""
        self.cli.show_info("Let's start with a quick assessment to understand your current knowledge level.")

        # Ask the initial diagnostic question
        question = "In one or two sentences, how would you describe what AI does?"
        self.cli._print("\n" + question, style="bold yellow")
        self.cli._print("[dim](Type 'skip' if you're not sure)[/dim]")

        answer, hesitation = self.cli.ask_question(question, measure_hesitation=True)

        # Process diagnostic
        self.cli.show_thinking("Analyzing your response...")
        result = self.engine.run_diagnostic(answer, hesitation)

        # Handle different diagnostic outcomes
        if result.get("next_mode") == "multiple_choice":
            self.cli.show_info("Let's try a multiple-choice question instead.")
            payload = result.get("question_payload", {})
            mcq_answer, mcq_hesitation = self.cli.ask_question(
                payload.get("question", ""),
                payload.get("options", [])
            )
            # Re-run diagnostic with MCQ answer
            result = self.engine.run_diagnostic(mcq_answer, mcq_hesitation)

        elif result.get("next_mode") == "examples_first":
            self.cli.show_info("No problem! We'll start with examples and basics.")
            self.engine.state_manager.state["difficulty_level"] = 0
            self.engine.state_manager.set_learning_style("examples")
            self.engine.state_manager.save_state()

        self.cli._print("\n[green]✓ Assessment complete! Starting your personalized learning journey...[/green]\n")

    def run_lesson_phase(self):
        """Run a lesson phase with quiz questions."""
        # Get next lesson
        lesson_data = self.engine.get_next_lesson()
        # Note: lesson content is automatically stored in engine.current_lesson_content

        # Display lesson
        self.cli.show_lesson(lesson_data)

        # Ask check questions
        check_questions = lesson_data.get("check_questions", [])
        if check_questions:
            self.cli._print("\n[bold]Let's check your understanding:[/bold]\n")

            for i, question in enumerate(check_questions[:2]):  # Limit to 2 questions per lesson
                answer, hesitation = self.cli.ask_question(question)

                # Use semantic evaluation instead of simple heuristic
                feedback = self.engine.submit_quiz_answer(
                    f"{lesson_data['module']}_q{i}",
                    answer,
                    "",  # correct_answer not needed for semantic evaluation
                    hesitation,
                    question=question  # Pass question for context
                )

                self.cli.show_feedback(feedback)
                
                # If user is confused, provide additional help
                if feedback.get("is_confused"):
                    self.cli._print("\n[yellow]I notice you're feeling confused. Let me help![/yellow]")
                    self.cli._print("[dim]I've simplified the next content and will focus on examples.[/dim]\n")

    def run_capstone_phase(self):
        """Run the capstone project phase."""
        self.cli._print("\n[bold green]🎓 Capstone Project: Build Your First AI Agent![/bold green]\n")
        self.cli._print("You've learned the fundamentals. Now let's create something practical!\n")

        # Ask what kind of agent they want
        question = "What type of tasks would you like your agent to manage?"
        self.cli._print(question, style="bold yellow")

        task_description, _ = self.cli.ask_question(question, measure_hesitation=False)

        # Generate agent
        self.cli.show_thinking("Generating your custom AI agent...")
        capstone_result = self.engine.run_capstone(task_description)

        # Show results
        self.cli.show_capstone_result(capstone_result)

        # Optionally save the generated code
        if self.cli.confirm("\nWould you like to save this agent code to a file?"):
            output_file = Path("my_agent.py")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(capstone_result.get("agent_code", ""))
            self.cli._print(f"[green]✓ Saved to {output_file}[/green]")

    def run_full_course(self):
        """Run the complete learning experience."""
        # Welcome
        self.cli.show_welcome()

        # Phase 1: Diagnostic
        self.run_diagnostic_phase()

        # Phase 2: Lessons (3 modules before capstone)
        module_sequence = ["fundamentals", "transformers_llms", "agents"]

        for module_name in module_sequence:
            # Check if user wants to continue
            if not self.cli.confirm(f"\nReady to start the '{module_name.replace('_', ' ').title()}' module?"):
                self.cli._print("[yellow]Pausing here. Run the program again to continue![/yellow]")
                return

            # Run lesson
            self.run_lesson_phase()

            # Advance to next module
            result = self.engine.advance_to_next_module()
            if result.get("coming_soon", False):
                self.cli._print(f"\n[bold yellow]{result.get('message', 'Next modules coming soon!')}[/bold yellow]\n")
                return

        # Phase 3: Capstone
        if self.cli.confirm("\nReady for your capstone project?"):
            self.run_capstone_phase()

        # Show final progress
        self.cli._print("\n[bold cyan]═══ Final Progress Summary ═══[/bold cyan]\n")
        progress = self.engine.get_progress_summary()
        self.cli.show_progress(progress)

        self.cli._print("\n[bold green]🎉 Congratulations on completing LearnAI![/bold green]")
        self.cli._print("[cyan]You've learned about AI and built your own agent. Keep exploring![/cyan]\n")

    def show_progress_only(self):
        """Show progress summary without running lessons."""
        progress = self.engine.get_progress_summary()
        self.cli.show_progress(progress)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LearnAI - Adaptive AI Learning Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run full course
  python main.py --user john        # Run with specific user ID
  python main.py --progress         # Show progress only
  python main.py --reset            # Reset and start over
        """
    )

    parser.add_argument(
        "--user",
        type=str,
        default="demo_user",
        help="User ID for tracking progress (default: demo_user)"
    )

    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress summary and exit"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset user progress and start over"
    )

    parser.add_argument(
        "--lesson-only",
        action="store_true",
        help="Run a single lesson without full course"
    )

    args = parser.parse_args()

    # Create app instance
    app = LearnAIApp(user_id=args.user)

    try:
        if args.reset:
            app.engine.reset_user_state()
            app.cli._print("[green]✓ Progress reset. Starting fresh![/green]")
            return

        if args.progress:
            app.show_progress_only()
            return

        if args.lesson_only:
            app.run_lesson_phase()
            return

        # Run full course
        app.run_full_course()

    except KeyboardInterrupt:
        app.cli._print("\n\n[yellow]Learning paused. Your progress has been saved![/yellow]")
        app.cli._print("[dim]Run again to continue from where you left off.[/dim]\n")
        sys.exit(0)
    except Exception as e:
        app.cli.show_error(f"An unexpected error occurred: {e}")
        if "--debug" in sys.argv:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()

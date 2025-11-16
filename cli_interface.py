"""CLI Interface for LearnAI using Rich for beautiful terminal output."""

import time
from typing import List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class CLIInterface:
    """Rich CLI interface for the learning agent."""

    def __init__(self):
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

    def _print(self, text: str, style: str = ""):
        """Print with or without rich."""
        if self.console:
            self.console.print(text, style=style)
        else:
            print(text)

    def show_welcome(self):
        """Display welcome message."""
        welcome_text = """
# Welcome to LearnAI!

I'm your adaptive AI learning companion. I'll teach you about:
- AI Fundamentals
- Transformers & Large Language Models
- AI Agents
- Building Your Own Agent

The best part? I adapt to YOUR learning style and pace. Let's get started!
"""
        if self.console:
            self.console.print(Panel(Markdown(welcome_text), title="LearnAI", border_style="blue"))
        else:
            print(welcome_text)

    def show_lesson(self, lesson_data: dict):
        """Display lesson content with formatting.

        Args:
            lesson_data: Dict with module, content, difficulty, etc.
        """
        module = lesson_data.get("module", "Lesson")
        content = lesson_data.get("content", "")
        difficulty = lesson_data.get("difficulty", 1)
        image_ref = lesson_data.get("image_reference", "")

        difficulty_labels = ["Beginner", "Intermediate", "Advanced", "Expert"]
        difficulty_label = difficulty_labels[min(difficulty, 3)]

        if self.console:
            # Show module header
            self.console.print(f"\n[bold cyan]Module: {module.replace('_', ' ').title()}[/bold cyan]")
            self.console.print(f"[dim]Difficulty: {difficulty_label}[/dim]\n")

            # Show content as markdown
            self.console.print(Panel(Markdown(content), border_style="cyan"))

            # Show image reference if available
            if image_ref and not image_ref.startswith("freepik://"):
                self.console.print(f"\n[dim]Visual aid: {image_ref}[/dim]")
        else:
            print(f"\n=== {module.replace('_', ' ').title()} ===")
            print(f"Difficulty: {difficulty_label}\n")
            print(content)
            if image_ref:
                print(f"\nVisual aid: {image_ref}")

    def ask_question(self, question: str, options: Optional[List[str]] = None,
                    measure_hesitation: bool = True) -> tuple[str, float]:
        """Ask a question and optionally measure response time.

        Args:
            question: The question to ask
            options: Optional list of multiple choice options
            measure_hesitation: Whether to measure response time

        Returns:
            Tuple of (answer, hesitation_seconds)
        """
        start_time = time.time()

        if options:
            # Multiple choice
            if self.console:
                self.console.print(f"\n[bold yellow]Question:[/bold yellow] {question}\n")
                for i, option in enumerate(options, 1):
                    self.console.print(f"  {i}. {option}")
                choice = Prompt.ask("\nYour choice", choices=[str(i) for i in range(1, len(options) + 1)])
                answer = options[int(choice) - 1]
            else:
                print(f"\nQuestion: {question}\n")
                for i, option in enumerate(options, 1):
                    print(f"  {i}. {option}")
                while True:
                    choice = input("\nYour choice (number): ").strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(options):
                        answer = options[int(choice) - 1]
                        break
        else:
            # Open-ended
            if self.console:
                self.console.print(f"\n[bold yellow]Question:[/bold yellow] {question}\n")
                answer = Prompt.ask("Your answer")
            else:
                print(f"\nQuestion: {question}")
                answer = input("Your answer: ")

        hesitation = time.time() - start_time if measure_hesitation else 0
        return answer, hesitation

    def show_feedback(self, feedback: dict):
        """Show feedback on quiz answer.

        Args:
            feedback: Dict with correct, difficulty changes, etc.
        """
        # Don't show "Correct!" if user is confused - that would be misleading
        if feedback.get("is_confused"):
            emoji = "💡" if self.console else "[HELP]"
            message = f"{emoji} I understand this is challenging. Let me help clarify!"
            style = "bold yellow"
        elif feedback.get("correct"):
            emoji = "✅" if self.console else "[CORRECT]"
            message = f"{emoji} Correct! Great job!"
            style = "bold green"
        else:
            emoji = "❌" if self.console else "[INCORRECT]"
            message = f"{emoji} Not quite right. Let's keep learning!"
            style = "bold yellow"

        if self.console:
            self.console.print(f"\n{message}", style=style)
        else:
            print(f"\n{message}")

        # Show reasoning if available (for debugging/transparency)
        if feedback.get("reasoning") and feedback.get("confidence", 0) < 0.7:
            if self.console:
                self.console.print(f"[dim]{feedback['reasoning']}[/dim]")
            else:
                print(f"Note: {feedback['reasoning']}")

        # Show adaptations
        if feedback.get("difficulty_changed"):
            direction = feedback.get("change_direction", "adjusted")
            if self.console:
                self.console.print(f"[dim]I've {direction} the difficulty to match your pace.[/dim]")
            else:
                print(f"I've {direction} the difficulty to match your pace.")

        if feedback.get("should_switch_to_examples"):
            if self.console:
                self.console.print("[dim]I'll focus more on examples in the next lesson.[/dim]")
            else:
                print("I'll focus more on examples in the next lesson.")

    def show_progress(self, progress_data: dict):
        """Display progress summary.

        Args:
            progress_data: Progress summary from state manager
        """
        if self.console:
            table = Table(title="Your Learning Progress", show_header=True, header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Current Module", progress_data.get("current_module", "N/A"))
            table.add_row("Difficulty Level", f"{progress_data.get('difficulty_level', 1)}/3")
            table.add_row("Completed Modules", str(len(progress_data.get("completed_modules", []))))
            table.add_row("Questions Answered", str(progress_data.get("total_questions", 0)))

            if progress_data.get("total_questions", 0) > 0:
                accuracy = progress_data.get("accuracy", 0) * 100
                table.add_row("Accuracy", f"{accuracy:.1f}%")

            self.console.print("\n")
            self.console.print(table)
            self.console.print("\n")
        else:
            print("\n=== Your Learning Progress ===")
            print(f"Current Module: {progress_data.get('current_module', 'N/A')}")
            print(f"Difficulty Level: {progress_data.get('difficulty_level', 1)}/3")
            print(f"Completed Modules: {len(progress_data.get('completed_modules', []))}")
            print(f"Questions Answered: {progress_data.get('total_questions', 0)}")
            if progress_data.get("total_questions", 0) > 0:
                accuracy = progress_data.get("accuracy", 0) * 100
                print(f"Accuracy: {accuracy:.1f}%")
            print()

    def show_code(self, code: str, title: str = "Generated Code"):
        """Display code with syntax highlighting.

        Args:
            code: Code string to display
            title: Title for the code panel
        """
        if self.console:
            from rich.syntax import Syntax
            syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax, title=title, border_style="green"))
        else:
            print(f"\n=== {title} ===")
            print(code)
            print("=" * 50)

    def show_capstone_result(self, capstone_data: dict):
        """Display capstone project results.

        Args:
            capstone_data: Dict with agent_code, description, next_steps
        """
        if self.console:
            self.console.print("\n[bold green]🎉 Congratulations! You've completed your capstone project![/bold green]\n")
        else:
            print("\n=== Congratulations! You've completed your capstone project! ===\n")

        description = capstone_data.get("agent_description", "Your custom agent")
        if self.console:
            self.console.print(f"[cyan]{description}[/cyan]\n")
        else:
            print(f"{description}\n")

        # Show the code
        code = capstone_data.get("agent_code", "")
        if code:
            self.show_code(code, "Your AI Agent")

        # Show next steps
        next_steps = capstone_data.get("next_steps", [])
        if next_steps:
            if self.console:
                self.console.print("\n[bold]Next Steps:[/bold]")
                for step in next_steps:
                    self.console.print(f"  • {step}")
            else:
                print("\nNext Steps:")
                for step in next_steps:
                    print(f"  - {step}")

    def confirm(self, question: str) -> bool:
        """Ask for confirmation.

        Args:
            question: Question to ask

        Returns:
            True if confirmed, False otherwise
        """
        if self.console:
            return Confirm.ask(question)
        else:
            response = input(f"{question} (y/n): ").strip().lower()
            return response in ["y", "yes"]

    def show_thinking(self, message: str = "Thinking..."):
        """Show a thinking/processing indicator."""
        if self.console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                progress.add_task(description=message, total=None)
                time.sleep(1)
        else:
            print(f"{message}")

    def show_error(self, message: str):
        """Display an error message.

        Args:
            message: Error message to display
        """
        if self.console:
            self.console.print(f"[bold red]Error:[/bold red] {message}")
        else:
            print(f"Error: {message}")

    def show_info(self, message: str):
        """Display an info message.

        Args:
            message: Info message to display
        """
        if self.console:
            self.console.print(f"[cyan]ℹ {message}[/cyan]")
        else:
            print(f"Info: {message}")

"""DiffAgent using LangGraph for configuration validation."""

from langgraph.graph import StateGraph, END
from state import DiffAgentState
from nodes import (
    extract_options_node,
    extract_dependencies_node,
    analyze_changes_node,
    detect_errors_node,
    should_continue
)
from models import ValidationResult
import os
from dotenv import load_dotenv


class DiffAgent:
    """
    DiffAgent validates configuration file changes using LangGraph.

    The agent uses a multi-step workflow:
    1. Extract configuration options from git diff
    2. Analyze changes to determine if additional context is needed
    3. Detect configuration errors and inconsistencies
    4. Generate a detailed validation report
    """

    def __init__(self):
        """Initialize the DiffAgent with a LangGraph workflow."""
        load_dotenv()

        # Verify API key is available
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Build the graph
        self.workflow = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow.

        The workflow follows this structure:
        START -> extract_options -> extract_dependencies -> analyze_changes -> detect_errors -> END
        """
        # Create a new graph
        graph = StateGraph(DiffAgentState)

        # Add nodes
        graph.add_node("extract_options", extract_options_node)
        graph.add_node("extract_dependencies", extract_dependencies_node)
        graph.add_node("analyze_changes", analyze_changes_node)
        graph.add_node("detect_errors", detect_errors_node)

        # Add edges
        graph.set_entry_point("extract_options")
        graph.add_edge("extract_options", "extract_dependencies")
        graph.add_edge("extract_dependencies", "analyze_changes")

        # Conditional edge from analyze_changes
        graph.add_conditional_edges(
            "analyze_changes",
            should_continue,
            {
                "detect_errors": "detect_errors",
                "end": END
            }
        )

        # Final edge
        graph.add_edge("detect_errors", END)

        # Compile the graph
        return graph.compile()

    def validate_diff(self, commit_diff: str, commit_hash: str = None, project_root: str = ".") -> ValidationResult:
        """
        Validate a commit diff for configuration errors.

        Args:
            commit_diff: The git diff content to analyze
            commit_hash: Optional commit hash for tracking
            project_root: Root directory of the project for CfgNet analysis

        Returns:
            ValidationResult with detected errors and summary
        """
        # Initialize state
        initial_state: DiffAgentState = {
            "commit_diff": commit_diff,
            "commit_hash": commit_hash,
            "project_root": project_root,
            "changed_options": [],
            "config_dependencies": [],
            "needs_additional_info": False,
            "additional_info": None,
            "detected_errors": [],
            "validation_complete": False,
            "error_summary": None
        }

        # Run the workflow
        final_state = self.workflow.invoke(initial_state)

        # Build the result
        has_errors = len(final_state["detected_errors"]) > 0
        errors = final_state["detected_errors"]
        summary = final_state.get("error_summary", "Validation completed.")

        return ValidationResult(
            has_errors=has_errors,
            errors=errors,
            summary=summary
        )

    def validate_from_file(self, diff_file_path: str, commit_hash: str = None, project_root: str = ".") -> ValidationResult:
        """
        Validate a diff from a file.

        Args:
            diff_file_path: Path to the file containing the diff
            commit_hash: Optional commit hash for tracking
            project_root: Root directory of the project for CfgNet analysis

        Returns:
            ValidationResult with detected errors and summary
        """
        with open(diff_file_path, 'r') as f:
            commit_diff = f.read()

        return self.validate_diff(commit_diff, commit_hash, project_root)

    def print_result(self, result: ValidationResult) -> None:
        """
        Print the validation result in a human-readable format.

        Args:
            result: The ValidationResult to print
        """
        print("=" * 80)
        print("CONFIGURATION VALIDATION REPORT")
        print("=" * 80)
        print()
        print(f"Summary: {result.summary}")
        print()

        if result.has_errors:
            print(f"Found {len(result.errors)} issue(s):")
            print()

            for i, error in enumerate(result.errors, 1):
                print(f"{i}. [{error.severity.upper()}] {error.file_path}")
                print(f"   Option: {error.option_name}")
                if error.old_value:
                    print(f"   Old Value: {error.old_value}")
                if error.new_value:
                    print(f"   New Value: {error.new_value}")
                print(f"   Issue: {error.reason}")
                print(f"   Suggested Fix: {error.suggested_fix}")
                print()
        else:
            print("✓ No configuration errors detected.")
            print()

        print("=" * 80)


def main():
    """Main entry point for command-line usage."""
    import sys

    # Create the agent
    agent = DiffAgent()

    # Check if a diff file was provided
    if len(sys.argv) > 1:
        diff_file = sys.argv[1]
        result = agent.validate_from_file(diff_file)
    else:
        # Read from stdin
        print("Reading diff from stdin... (Press Ctrl+D when done)")
        commit_diff = sys.stdin.read()
        result = agent.validate_diff(commit_diff)

    # Print the result
    agent.print_result(result)

    # Exit with error code if issues found
    if result.has_errors:
        # Check if any critical errors exist
        critical_errors = [e for e in result.errors if e.severity == "critical"]
        if critical_errors:
            sys.exit(1)


if __name__ == "__main__":
    main()

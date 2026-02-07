"""DiffAgent using LangGraph for configuration validation."""

import argparse
import subprocess
import sys
import os
from typing import Optional

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
from dotenv import load_dotenv

# Default configuration file patterns
DEFAULT_CONFIG_PATTERNS = [
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "*.properties",
    "*.yaml",
    "*.yml",
    "*.json",
    "*.env",
    "*.ini",
    "*.conf",
    "*.toml",
    "*.cfg",
    "*.config",
]

# Supported LLM providers and their default models
SUPPORTED_PROVIDERS = {
    "openai": {
        "default_model": "gpt-4o-mini",
        "powerful_model": "gpt-4o",
        "env_var": "OPENAI_API_KEY",
    },
    "anthropic": {
        "default_model": "claude-3-5-haiku-latest",
        "powerful_model": "claude-sonnet-4-20250514",
        "env_var": "ANTHROPIC_API_KEY",
    },
}

DEFAULT_PROVIDER = "openai"


class DiffAgent:
    """
    DiffAgent validates configuration file changes using LangGraph.

    The agent uses a multi-step workflow:
    1. Extract configuration options from git diff
    2. Analyze changes to determine if additional context is needed
    3. Detect configuration errors and inconsistencies
    4. Generate a detailed validation report
    """

    def __init__(self, provider: str = None, model: str = None):
        """
        Initialize the DiffAgent with a LangGraph workflow.

        Args:
            provider: LLM provider to use ('openai' or 'anthropic'). Defaults to 'openai'.
            model: Model name to use. If not specified, uses provider's default model.
        """
        load_dotenv()

        # Set provider and model
        self.provider = provider or DEFAULT_PROVIDER
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {self.provider}. Supported: {list(SUPPORTED_PROVIDERS.keys())}")

        provider_config = SUPPORTED_PROVIDERS[self.provider]
        self.model = model or provider_config["default_model"]
        self.powerful_model = provider_config["powerful_model"]

        # Verify API key is available for the selected provider
        env_var = provider_config["env_var"]
        if not os.getenv(env_var):
            raise ValueError(f"{env_var} not found in environment variables")

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
            "llm_provider": self.provider,
            "llm_model": self.model,
            "llm_powerful_model": self.powerful_model,
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


def get_staged_diff(config_patterns: list[str] = None) -> str:
    """
    Get the diff of staged changes for configuration files.

    Args:
        config_patterns: List of file patterns to consider as config files.
                        If None, uses DEFAULT_CONFIG_PATTERNS.

    Returns:
        The git diff of staged configuration files.
    """
    if config_patterns is None:
        config_patterns = DEFAULT_CONFIG_PATTERNS

    try:
        # Get list of staged files
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        staged_files = result.stdout.strip().split("\n")
        staged_files = [f for f in staged_files if f]  # Remove empty strings

        if not staged_files:
            return ""

        # Filter to config files only
        config_files = []
        for file in staged_files:
            for pattern in config_patterns:
                if pattern.startswith("*"):
                    # Extension match
                    if file.endswith(pattern[1:]):
                        config_files.append(file)
                        break
                else:
                    # Exact name or ends with name
                    if file == pattern or file.endswith("/" + pattern):
                        config_files.append(file)
                        break

        if not config_files:
            return ""

        # Get the actual diff for config files
        result = subprocess.run(
            ["git", "diff", "--cached", "--"] + config_files,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        return ""
    except FileNotFoundError:
        print("Git is not installed or not in PATH.", file=sys.stderr)
        return ""


def get_unstaged_diff(config_patterns: list[str] = None) -> str:
    """
    Get the diff of unstaged changes for configuration files.

    Args:
        config_patterns: List of file patterns to consider as config files.

    Returns:
        The git diff of unstaged configuration files.
    """
    if config_patterns is None:
        config_patterns = DEFAULT_CONFIG_PATTERNS

    try:
        # Get list of modified files
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        modified_files = result.stdout.strip().split("\n")
        modified_files = [f for f in modified_files if f]

        if not modified_files:
            return ""

        # Filter to config files only
        config_files = []
        for file in modified_files:
            for pattern in config_patterns:
                if pattern.startswith("*"):
                    if file.endswith(pattern[1:]):
                        config_files.append(file)
                        break
                else:
                    if file == pattern or file.endswith("/" + pattern):
                        config_files.append(file)
                        break

        if not config_files:
            return ""

        # Get the actual diff for config files
        result = subprocess.run(
            ["git", "diff", "--"] + config_files,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        return ""
    except FileNotFoundError:
        print("Git is not installed or not in PATH.", file=sys.stderr)
        return ""


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="diffagent",
        description="Validate configuration file changes to prevent misconfigurations.",
        epilog="Examples:\n"
               "  diffagent --staged          Validate staged changes (for pre-commit hook)\n"
               "  diffagent diff.txt          Validate changes from a diff file\n"
               "  git diff | diffagent        Validate piped diff\n"
               "  diffagent --all             Validate all uncommitted changes\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "diff_file",
        nargs="?",
        help="Path to a diff file to validate. If not provided, reads from stdin or uses --staged/--all."
    )

    parser.add_argument(
        "--staged",
        action="store_true",
        help="Validate only staged changes (for pre-commit hook integration)."
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all uncommitted changes (staged + unstaged)."
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any error, not just critical ones."
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-essential output."
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output."
    )

    parser.add_argument(
        "--project-root",
        default=".",
        help="Root directory of the project for dependency analysis (default: current directory)."
    )

    parser.add_argument(
        "--provider",
        choices=list(SUPPORTED_PROVIDERS.keys()),
        default=None,
        help=f"LLM provider to use (default: {DEFAULT_PROVIDER}). Choices: {', '.join(SUPPORTED_PROVIDERS.keys())}."
    )

    parser.add_argument(
        "--model",
        default=None,
        help="Model name to use. If not specified, uses the provider's default model. "
             "Examples: gpt-4o, gpt-4o-mini, claude-sonnet-4-20250514, claude-3-5-haiku-latest."
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )

    return parser


def main():
    """Main entry point for command-line usage."""
    parser = create_parser()
    args = parser.parse_args()

    # Determine the diff source
    commit_diff = ""

    if args.diff_file:
        # Read from file
        try:
            with open(args.diff_file, 'r') as f:
                commit_diff = f.read()
        except FileNotFoundError:
            print(f"Error: File '{args.diff_file}' not found.", file=sys.stderr)
            sys.exit(2)
        except IOError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(2)
    elif args.staged:
        # Get staged changes
        commit_diff = get_staged_diff()
        if not commit_diff:
            if not args.quiet:
                print("No staged configuration files to validate.")
            sys.exit(0)
    elif args.all:
        # Get all uncommitted changes (staged + unstaged)
        staged = get_staged_diff()
        unstaged = get_unstaged_diff()
        commit_diff = staged + "\n" + unstaged if staged or unstaged else ""
        if not commit_diff.strip():
            if not args.quiet:
                print("No configuration file changes to validate.")
            sys.exit(0)
    elif not sys.stdin.isatty():
        # Read from stdin (piped input)
        commit_diff = sys.stdin.read()
    else:
        # No input provided, show help
        parser.print_help()
        sys.exit(0)

    if not commit_diff.strip():
        if not args.quiet:
            print("No diff content to validate.")
        sys.exit(0)

    # Create and run the agent
    try:
        agent = DiffAgent(provider=args.provider, model=args.model)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        provider = args.provider or DEFAULT_PROVIDER
        env_var = SUPPORTED_PROVIDERS.get(provider, {}).get("env_var", "API_KEY")
        print(f"Set the {env_var} environment variable or add it to a .env file.", file=sys.stderr)
        sys.exit(2)

    result = agent.validate_diff(commit_diff, project_root=args.project_root)

    # Print the result
    if not args.quiet:
        agent.print_result(result)

    # Determine exit code
    if result.has_errors:
        if args.strict:
            # Any error causes failure
            sys.exit(1)
        else:
            # Only critical errors cause failure
            critical_errors = [e for e in result.errors if e.severity == "critical"]
            if critical_errors:
                sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

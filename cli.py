"""Command-line interface for DiffAgent."""

import argparse
import subprocess
import sys

from agent import DiffAgent, SUPPORTED_PROVIDERS, DEFAULT_PROVIDER

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

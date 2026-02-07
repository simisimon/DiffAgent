# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DiffAgent is a CLI tool and GitHub Action that validates configuration file changes in pull requests and commits to detect potential misconfigurations before they reach production. It uses LangGraph with OpenAI's GPT models to analyze git diffs and identify configuration errors through a multi-agent workflow.

## Architecture

### Core Components

The implementation uses **LangGraph** for workflow orchestration with the following files:

- **agent.py**: DiffAgent class with LangGraph workflow definition and LLM provider configuration
- **cli.py**: Command-line interface entry point with argument parsing and git integration
- **models.py**: Pydantic data models (ChangedOption, CommitChanges, ConfigError, ValidationResult)
- **state.py**: LangGraph state schema (DiffAgentState TypedDict)
- **nodes.py**: Node functions for the LangGraph workflow
- **test_agent.py**: Test script with example diffs

### CLI Interface

The CLI is implemented in `agent.py` using `argparse`:

```
diffagent [diff_file] [--staged] [--all] [--strict] [--quiet] [--project-root DIR] [--provider PROVIDER] [--model MODEL]
```

Key CLI features:
- `--staged`: Validates only staged changes (for pre-commit hook integration)
- `--all`: Validates all uncommitted changes (staged + unstaged)
- `--strict`: Fail on any error, not just critical ones
- `--quiet`: Suppress non-essential output
- `--provider`: LLM provider (`openai` or `anthropic`)
- `--model`: Specific model name to use
- Supports reading from file, stdin, or git staged changes

Helper functions for git integration:
- `get_staged_diff()`: Gets diff of staged config files using `git diff --cached`
- `get_unstaged_diff()`: Gets diff of unstaged config files using `git diff`
- `DEFAULT_CONFIG_PATTERNS`: List of file patterns considered as config files

Exit codes:
- `0`: Success - no errors or only warnings/info
- `1`: Validation failed - critical errors detected
- `2`: Runtime error (missing API key, file not found, etc.)

### LangGraph Workflow

The agent uses a **StateGraph** with the following nodes:

1. **extract_options**: Parses git diffs using GPT-4o-mini to extract configuration changes
   - Identifies file paths, option names, old/new values
   - Supports Dockerfiles, .properties, .yaml, .json, .env, .ini files
   - Returns structured ChangedOption objects

2. **extract_dependencies**: Uses CfgNet to extract configuration dependencies
   - Analyzes project for cross-file configuration relationships
   - Returns ConfigDependency objects

3. **analyze_changes**: Evaluates if additional context is needed
   - Determines if changes are self-explanatory
   - Identifies need for related files or documentation

4. **detect_errors**: Deep analysis using GPT-4o to identify issues
   - Inconsistencies between related configs (e.g., port mismatches)
   - Invalid values or ranges
   - Security vulnerabilities
   - Best practice violations
   - Dependency violations
   - Returns ConfigError objects with severity, reason, and suggested fixes

**Workflow Flow**:
```
START -> extract_options -> extract_dependencies -> analyze_changes -> detect_errors -> END
```

The `should_continue()` function provides conditional routing between nodes.

### Data Models (models.py)

- **ChangedOption**: Single configuration change with file_path, option_name, old_value, new_value, line_number
- **CommitChanges**: Collection of changed options from a commit with optional commit_hash
- **ConfigDependency**: Cross-file configuration dependency with source/target info
- **ConfigError**: Error report with file_path, option_name, severity, reason, suggested_fix
- **ValidationResult**: Final output with has_errors, errors list, and summary

### State Schema (state.py)

- **commit_diff**: The git diff content to analyze
- **commit_hash**: Optional commit identifier
- **project_root**: Root directory for CfgNet analysis
- **llm_provider**: LLM provider name (openai, anthropic)
- **llm_model**: Default model name for extraction/analysis
- **llm_powerful_model**: Powerful model name for error detection
- **changed_options**: Extracted configuration changes (uses `add` operator for accumulation)
- **config_dependencies**: Extracted dependencies from CfgNet
- **needs_additional_info**: Flag for context requirements
- **detected_errors**: List of detected issues (uses `add` operator)
- **validation_complete**: Workflow completion flag
- **error_summary**: Summary of findings

## Pre-commit Hook Integration

DiffAgent integrates with git pre-commit hooks:

```bash
# .git/hooks/pre-commit
#!/bin/bash
python /path/to/DiffAgent/agent.py --staged --strict
if [ $? -ne 0 ]; then
    echo "Commit blocked: Configuration validation failed."
    exit 1
fi
```

Or using the pre-commit framework in `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: diffagent
        name: DiffAgent Configuration Validator
        entry: python /path/to/DiffAgent/agent.py --staged --strict
        language: system
        pass_filenames: false
        stages: [commit]
```

## GitHub Actions Integration

### Workflow File: `.github/workflows/validate-config.yml`

Runs on pull requests to `main` branch:
- Sets up Python 3.11
- Installs dependencies from requirements.txt (LangGraph, LangChain, OpenAI)
- Executes `python agent.py > results.txt` with OPENAI_API_KEY from secrets
- Uploads results as artifacts
- Fails the PR if critical errors are detected

**Required Secret**: `OPENAI_API_KEY` must be configured in repository secrets

### Action File: `.github/actions/validate-config/action.yml`

Reusable composite action that:
- Takes a `diff_file` input (default: `diff.txt`)
- Runs the DiffAgent validation
- Outputs detected errors
- Fails if any configuration errors are found

## Build System

DiffAgent uses **Poetry** for dependency management and packaging.

### Key Files
- **pyproject.toml**: Poetry configuration, dependencies, and build settings
- **requirements.txt**: Kept for backwards compatibility with pip

### CLI Entry Point
The `diffagent` command is defined in `pyproject.toml`:
```toml
[tool.poetry.scripts]
diffagent = "cli:main"
```

The CLI module (`cli.py`) handles:
- Argument parsing with `argparse`
- Git integration (`get_staged_diff`, `get_unstaged_diff`)
- Configuration file pattern matching (`DEFAULT_CONFIG_PATTERNS`)
- Exit code handling

## Development Commands

### Setup with Poetry (Recommended)

```bash
# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Create .env file with your API key
echo "OPENAI_API_KEY=your-key-here" > .env

# Run DiffAgent
poetry run diffagent --help
```

### Setup with pip

```bash
# Create virtual environment
python -m venv env

# Activate virtual environment
source env/bin/activate  # Linux/Mac
# OR
env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Or install as editable package
pip install -e .

# Create .env file with your API key
echo "OPENAI_API_KEY=your-key-here" > .env
```

### Running the Agent

```bash
# With Poetry
poetry run diffagent --staged
poetry run diffagent --all
poetry run diffagent path/to/diff.txt

# If installed as package
diffagent --staged
diffagent --all
diffagent path/to/diff.txt

# With Python directly
python agent.py --staged
python agent.py --all
python agent.py path/to/diff.txt

# Pipe a git diff
git diff | diffagent
git diff | python agent.py

# With options
diffagent --staged --strict --provider anthropic
```

### Testing Locally

```bash
# Run the test suite with example diffs
python test_agent.py

# Run tests with pytest (if tests/ directory exists)
poetry run pytest

# With coverage
poetry run pytest --cov
```

The `test_agent.py` includes three test scenarios:
1. **Inconsistent port configuration**: Port mismatch between Dockerfile and application.properties
2. **Consistent change**: Simple debug flag toggle (should pass validation)
3. **Security issue**: Wildcard in ALLOWED_HOSTS and DEBUG=true

### Development Tools

```bash
# Format code with Black
poetry run black .

# Lint with Ruff
poetry run ruff check .

# Type checking with mypy
poetry run mypy .

# Run all checks
poetry run black . && poetry run ruff check . && poetry run mypy .
```

## Environment Configuration

Required environment variables (based on selected provider):
- `OPENAI_API_KEY`: OpenAI API key (required when using `--provider openai`)
- `ANTHROPIC_API_KEY`: Anthropic API key (required when using `--provider anthropic`)

Set via `.env` file locally or GitHub Secrets in CI/CD.

**Note**: The .env file contains secrets and should never be committed. It's in `.gitignore`.

## Key Implementation Details

### Configuration File Patterns

The CLI automatically detects these file types as configuration files:
- `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`
- `*.properties`, `*.yaml`, `*.yml`, `*.json`
- `*.env`, `*.ini`, `*.conf`, `*.toml`, `*.cfg`, `*.config`

Defined in `DEFAULT_CONFIG_PATTERNS` in `agent.py`.

### LLM Provider and Model Configuration

DiffAgent supports multiple LLM providers:

**Supported Providers:**
- `openai` (default): OpenAI GPT models
- `anthropic`: Anthropic Claude models

**Default Models by Provider:**

| Provider | Default Model | Powerful Model (for error detection) |
|----------|---------------|--------------------------------------|
| openai | gpt-4o-mini | gpt-4o |
| anthropic | claude-3-5-haiku-latest | claude-sonnet-4-20250514 |

**Node Model Usage:**
- **extract_options_node**: Uses the default model (cost-effective extraction)
- **analyze_changes_node**: Uses the default model (lightweight analysis)
- **detect_errors_node**: Uses the powerful model (sophisticated error detection)

All models use `temperature=0` for deterministic outputs.

**Configuration via CLI:**
```bash
# Use Anthropic Claude
python agent.py --staged --provider anthropic

# Use specific OpenAI model
python agent.py --staged --provider openai --model gpt-4o

# Use specific Anthropic model
python agent.py --staged --provider anthropic --model claude-sonnet-4-20250514
```

### State Management

The `DiffAgentState` uses `Annotated` types with the `add` operator for list fields:
- `changed_options: Annotated[list[ChangedOption], add]`
- `config_dependencies: Annotated[list[ConfigDependency], add]`
- `detected_errors: Annotated[list[ConfigError], add]`

This allows nodes to append to lists rather than replacing them.

### Structured Output

Nodes use JSON parsing with Pydantic models for type safety. The LLMs are prompted to return specific JSON schemas that match the Pydantic models.

### Error Handling

- JSON parsing errors are caught and logged
- Empty or invalid responses result in empty lists
- Missing API key results in exit code 2
- File not found results in exit code 2
- Critical validation errors result in exit code 1

### Exit Codes

- `0`: No errors or only warnings/info
- `1`: Critical configuration errors detected (or any errors with `--strict`)
- `2`: Runtime errors (missing API key, file not found, git errors)

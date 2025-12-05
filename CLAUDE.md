# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DiffAgent is a GitHub Action that validates configuration file changes in pull requests to detect potential misconfigurations before they reach production. It uses LangGraph with OpenAI's GPT models to analyze git diffs and identify configuration errors through a multi-agent workflow.

## Architecture

### Core Components

The implementation uses **LangGraph** for workflow orchestration with the following files:

- **agent.py**: Main DiffAgent class with LangGraph workflow definition and entry point
- **models.py**: Pydantic data models (ChangedOption, CommitChanges, ConfigError, ValidationResult)
- **state.py**: LangGraph state schema (DiffAgentState TypedDict)
- **nodes.py**: Node functions for the LangGraph workflow
- **test_agent.py**: Test script with example diffs

### LangGraph Workflow

The agent uses a **StateGraph** with the following nodes:

1. **extract_options**: Parses git diffs using GPT-4o-mini to extract configuration changes
   - Identifies file paths, option names, old/new values
   - Supports Dockerfiles, .properties, .yaml, .json, .env, .ini files
   - Returns structured ChangedOption objects

2. **analyze_changes**: Evaluates if additional context is needed
   - Determines if changes are self-explanatory
   - Identifies need for related files or documentation

3. **detect_errors**: Deep analysis using GPT-4o to identify issues
   - Inconsistencies between related configs (e.g., port mismatches)
   - Invalid values or ranges
   - Security vulnerabilities
   - Best practice violations
   - Returns ConfigError objects with severity, reason, and suggested fixes

**Workflow Flow**:
```
START -> extract_options -> analyze_changes -> detect_errors -> END
```

The `should_continue()` function provides conditional routing between nodes.

### Data Models (models.py)

- **ChangedOption**: Single configuration change with file_path, option_name, old_value, new_value, line_number
- **CommitChanges**: Collection of changed options from a commit with optional commit_hash
- **ConfigError**: Error report with file_path, option_name, severity, reason, suggested_fix
- **ValidationResult**: Final output with has_errors, errors list, and summary

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

## Development Commands

### Setup

```bash
# Create virtual environment
python -m venv env

# Activate virtual environment
source env/bin/activate  # Linux/Mac
# OR
env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your-key-here" > .env
```

### Running the Agent

```bash
# Run with a diff file
python agent.py path/to/diff.txt

# Run with stdin (paste diff and press Ctrl+D)
python agent.py

# Run from git diff directly
git diff | python agent.py
```

### Testing Locally

```bash
# Run the test suite with example diffs
python test_agent.py
```

The `test_agent.py` includes three test scenarios:
1. **Inconsistent port configuration**: Port mismatch between Dockerfile and application.properties
2. **Consistent change**: Simple debug flag toggle (should pass validation)
3. **Security issue**: Wildcard in ALLOWED_HOSTS and DEBUG=true

## Environment Configuration

Required environment variable:
- `OPENAI_API_KEY`: OpenAI API key for GPT model access (required)

Set via `.env` file locally or GitHub Secrets in CI/CD.

**Note**: The .env file contains secrets and should never be committed. It's in `.gitignore`.

## Key Implementation Details

### LLM Model Selection

- **extract_options_node**: Uses `gpt-4o-mini` for cost-effective option extraction
- **analyze_changes_node**: Uses `gpt-4o-mini` for lightweight analysis
- **detect_errors_node**: Uses `gpt-4o` for more sophisticated error detection

All models use `temperature=0` for deterministic outputs.

### State Management

The `DiffAgentState` uses `Annotated` types with the `add` operator for list fields:
- `changed_options: Annotated[list[ChangedOption], add]`
- `detected_errors: Annotated[list[ConfigError], add]`

This allows nodes to append to lists rather than replacing them.

### Structured Output

Nodes use JSON parsing with Pydantic models for type safety. The LLMs are prompted to return specific JSON schemas that match the Pydantic models.

### Error Handling

- JSON parsing errors are caught and logged
- Empty or invalid responses result in empty lists
- The agent exits with code 1 if critical errors are detected

### Exit Codes

- `0`: No errors or only warnings/info
- `1`: Critical configuration errors detected

# DiffAgent

An AI-powered CLI tool that validates configuration file changes to prevent misconfigurations before they reach production. Integrates seamlessly with Git pre-commit hooks.

## Overview

DiffAgent uses LangGraph and OpenAI's GPT models to analyze git diffs and automatically detect:

- **Configuration inconsistencies** between related files (e.g., mismatched ports in Dockerfile and app config)
- **Invalid configuration values** that are out of range or incorrect
- **Security vulnerabilities** in configuration settings
- **Best practice violations** in configuration management
- **Missing dependencies** that require corresponding configuration changes

## Features

- **CLI Tool** - Easy-to-use command-line interface for validating configuration changes
- **Pre-commit Hook Integration** - Automatically validate changes before every commit
- **Multi-agent Workflow** - Powered by LangGraph for intelligent analysis
- **Deep Validation** - Supports Dockerfiles, .properties, .yaml, .json, .env, .ini, .toml, and more
- **Security-aware** - Detects risky configuration patterns
- **Detailed Reports** - Clear severity levels and actionable fix suggestions

## Installation

### Prerequisites

- Python 3.11+
- Git
- OpenAI API key

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/DiffAgent.git
cd DiffAgent

# Create virtual environment
python -m venv env
source env/bin/activate  # Linux/Mac
# OR
env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up your OpenAI API key
echo "OPENAI_API_KEY=your-key-here" > .env
```

## CLI Usage

### Basic Commands

```bash
# Validate staged changes (for pre-commit hook)
python agent.py --staged

# Validate all uncommitted changes (staged + unstaged)
python agent.py --all

# Validate a diff file
python agent.py path/to/diff.txt

# Pipe a git diff directly
git diff main | python agent.py

# Validate with strict mode (fail on any error, not just critical)
python agent.py --staged --strict

# Quiet mode (suppress non-essential output)
python agent.py --staged --quiet

# Use a different LLM provider (Anthropic Claude)
python agent.py --staged --provider anthropic

# Use a specific model
python agent.py --staged --provider openai --model gpt-4o
python agent.py --staged --provider anthropic --model claude-sonnet-4-20250514
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `diff_file` | Path to a diff file to validate |
| `--staged` | Validate only staged changes (for pre-commit hooks) |
| `--all` | Validate all uncommitted changes (staged + unstaged) |
| `--strict` | Fail on any error, not just critical ones |
| `--quiet`, `-q` | Suppress non-essential output |
| `--no-color` | Disable colored output |
| `--project-root DIR` | Root directory for dependency analysis (default: `.`) |
| `--provider` | LLM provider: `openai` (default) or `anthropic` |
| `--model` | Model name (e.g., `gpt-4o`, `claude-sonnet-4-20250514`) |
| `--version` | Show version information |
| `--help`, `-h` | Show help message |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success - no errors or only warnings/info |
| `1` | Validation failed - critical errors detected (or any errors with `--strict`) |
| `2` | Runtime error - missing API key, file not found, etc. |

## Pre-commit Hook Integration

DiffAgent can be integrated into your Git workflow to automatically validate configuration changes before each commit.

### Option 1: Manual Hook Setup

Create a pre-commit hook script in your repository:

```bash
# Create the hook file
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

# DiffAgent Pre-commit Hook
# Validates configuration file changes before committing

# Path to DiffAgent (adjust if needed)
DIFFAGENT_DIR="/path/to/DiffAgent"

# Activate virtual environment if it exists
if [ -f "$DIFFAGENT_DIR/env/bin/activate" ]; then
    source "$DIFFAGENT_DIR/env/bin/activate"
elif [ -f "$DIFFAGENT_DIR/env/Scripts/activate" ]; then
    source "$DIFFAGENT_DIR/env/Scripts/activate"
fi

# Run DiffAgent on staged changes
python "$DIFFAGENT_DIR/agent.py" --staged --strict

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "Commit blocked: Configuration validation failed."
    echo "Fix the issues above or use 'git commit --no-verify' to bypass."
    exit 1
fi

exit 0
EOF

# Make the hook executable (Linux/Mac)
chmod +x .git/hooks/pre-commit
```

**Windows (PowerShell):**

```powershell
# Create the hook file
@"
#!/bin/bash

DIFFAGENT_DIR="/path/to/DiffAgent"

if [ -f "`$DIFFAGENT_DIR/env/Scripts/activate" ]; then
    source "`$DIFFAGENT_DIR/env/Scripts/activate"
fi

python "`$DIFFAGENT_DIR/agent.py" --staged --strict

EXIT_CODE=`$?

if [ `$EXIT_CODE -ne 0 ]; then
    echo ""
    echo "Commit blocked: Configuration validation failed."
    echo "Fix the issues above or use 'git commit --no-verify' to bypass."
    exit 1
fi

exit 0
"@ | Out-File -FilePath .git\hooks\pre-commit -Encoding utf8
```

### Option 2: Using pre-commit Framework

If you use the [pre-commit](https://pre-commit.com/) framework, add this to your `.pre-commit-config.yaml`:

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

Then install the hooks:

```bash
pre-commit install
```

### Option 3: Simple Inline Hook

For a quick setup in the same repository:

```bash
# Create a simple pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
python agent.py --staged
EOF

chmod +x .git/hooks/pre-commit
```

### Bypassing the Hook

If you need to commit despite validation errors (use with caution):

```bash
git commit --no-verify -m "Your commit message"
```

## Example Output

```
================================================================================
CONFIGURATION VALIDATION REPORT
================================================================================

Summary: Found inconsistent port configuration between Docker and application settings.

Found 1 issue(s):

1. [CRITICAL] src/Dockerfile
   Option: EXPOSE
   Old Value: 8080
   New Value: 8000
   Issue: Port mismatch detected. The Dockerfile exposes port 8000, but application.properties
          configures server.port as 8080. This will cause the application to be unreachable.
   Suggested Fix: Ensure both files use the same port number. Either set EXPOSE 8000 in Dockerfile
                 and server.port=8000 in application.properties, or use 8080 for both.

================================================================================
```

## Supported Configuration Files

DiffAgent automatically detects and validates these configuration file types:

- `Dockerfile` - Docker container configuration
- `docker-compose.yml` / `docker-compose.yaml` - Docker Compose files
- `*.properties` - Java properties files
- `*.yaml` / `*.yml` - YAML configuration files
- `*.json` - JSON configuration files
- `*.env` - Environment variable files
- `*.ini` / `*.conf` - INI-style configuration files
- `*.toml` - TOML configuration files
- `*.cfg` / `*.config` - Generic configuration files

## GitHub Actions Integration

DiffAgent can also run as a GitHub Action for PR validation:

```yaml
name: Validate Configuration

on:
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Get PR diff
        run: git diff origin/main...HEAD > diff.txt

      - name: Run DiffAgent
        run: python agent.py diff.txt
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Architecture

DiffAgent uses a **LangGraph StateGraph** with the following nodes:

1. **Extract Options** - Parses git diffs to identify configuration changes
2. **Extract Dependencies** - Uses CfgNet to find configuration dependencies
3. **Analyze Changes** - Determines if additional context is needed
4. **Detect Errors** - Performs deep validation and identifies issues

## Development

See [CLAUDE.md](CLAUDE.md) for detailed development documentation.

### Running Tests

```bash
python test_agent.py
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key (required when using `--provider openai`) |
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key (required when using `--provider anthropic`) |

*Only the API key for your selected provider is required.

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

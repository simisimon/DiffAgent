# DiffAgent -- Work In Progress

An AI-powered tool that validates configuration file changes to prevent misconfigurations before they reach production.

## Overview

DiffAgent uses LangGraph and OpenAI's GPT models to analyze git diffs and automatically detect:

- **Configuration inconsistencies** between related files (e.g., mismatched ports in Dockerfile and app config)
- **Invalid configuration values** that are out of range or incorrect
- **Security vulnerabilities** in configuration settings
- **Best practice violations** in configuration management
- **Missing dependencies** that require corresponding configuration changes

## Features

- 🤖 **Multi-agent workflow** powered by LangGraph for intelligent analysis
- 🔍 **Deep validation** of configuration files (Dockerfiles, .properties, .yaml, .json, .env, .ini)
- 🛡️ **Security-aware** detection of risky configuration patterns
- 📊 **Detailed reports** with severity levels and suggested fixes
- ⚡ **Fast feedback** integrated into your PR workflow
- 🎯 **Actionable suggestions** for fixing detected issues

## Quick Start

### Local Usage

1. **Install dependencies:**
```bash
python -m venv env
source env/bin/activate  # or `env\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. **Set up your OpenAI API key:**
```bash
echo "OPENAI_API_KEY=your-key-here" > .env
```

3. **Run validation:**
```bash
# Validate a diff file
python agent.py path/to/diff.txt

# Or pipe a git diff directly
git diff main | python agent.py

# Run test suite
python test_agent.py
```

### GitHub Action Usage

Add DiffAgent to your repository's pull request workflow:

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

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run DiffAgent
        run: python agent.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

**Important:** Add your OpenAI API key to repository secrets as `OPENAI_API_KEY`.

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

## Architecture

DiffAgent uses a **LangGraph StateGraph** with three main nodes:

1. **Extract Options** - Parses git diffs to identify configuration changes
2. **Analyze Changes** - Determines if additional context is needed
3. **Detect Errors** - Performs deep validation and identifies issues

Each node uses GPT models with specialized prompts to ensure accurate detection.

## Configuration Files Supported

- Dockerfiles
- .properties files
- .yaml / .yml files
- .json files
- .env files
- .ini / .conf files

## Development

See [CLAUDE.md](CLAUDE.md) for detailed development documentation.

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
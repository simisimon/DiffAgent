"""Nodes for the DiffAgent LangGraph workflow."""

import re
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from state import DiffAgentState
from models import ChangedOption, ConfigError, ConfigDependency
from cfgnet.network.network import Network
from cfgnet.network.network_configuration import NetworkConfiguration
import json
import os
import subprocess
import tempfile
import shutil
import traceback


def get_llm(model: str = "gpt-4o-mini") -> ChatOpenAI:
    """Get an OpenAI LLM instance."""
    return ChatOpenAI(
        model=model,
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )


def extract_options_node(state: DiffAgentState) -> dict[str, Any]:
    """
    Extract changed configuration options from the commit diff.

    This node analyzes the git diff and identifies all configuration
    changes including file paths, option names, and old/new values.
    """
    commit_diff = state["commit_diff"]

    llm = get_llm()

    system_prompt = """You are OptionExtractor-X, an elite code reviewer specialized in analyzing
file diffs of configuration files and extracting changed configuration options.

Your task is to:
1. Identify all configuration files that have been modified in the diff
2. Extract each configuration option that has been changed
3. For each change, identify:
   - The file path
   - The technology to which the configuration file belongs (e.g., Docker, Spring, Kubernetes, etc.)
   - The configuration option name
   - The old value
   - The new value
   - The approximate line number (if available)

Focus on configuration files like:
- Dockerfiles (EXPOSE, ENV, WORKDIR, etc.)
- .properties files (key=value pairs)
- .yaml/.yml files (key: value pairs)
- .json files (JSON key-value pairs)
- .env files (KEY=VALUE pairs)
- .ini/.conf files
- Any other configuration-like files

Return your analysis as a JSON object with this structure:
{
  "changed_options": [
    {
      "file_path": "path/to/file",
      "option_name": "option.name",
      "old_value": "old_value",
      "new_value": "new_value",
      "line_number": 10
    }
  ]
}

If no configuration changes are found, return an empty list."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Analyze this diff and extract all configuration changes:\n\n{commit_diff}")
    ]

    response = llm.invoke(messages)

    # Parse the JSON response
    try:
        result = json.loads(response.content)
        changed_options = [
            ChangedOption(**option)
            for option in result.get("changed_options", [])
        ]
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Response content: {response.content}")
        changed_options = []

    return {
        "changed_options": changed_options,
        "needs_additional_info": False,
        "validation_complete": False
    }


def crawl_repository_node(state: DiffAgentState) -> dict[str, Any]:
    """
    Crawl the repository to gather additional context.

    This node scans the repository for related configuration files,
    documentation, and other relevant information that may aid in
    validating the configuration changes.
    """
    pass 


def crawl_documentation_node(state: DiffAgentState) -> dict[str, Any]:
    """
    Crawl documentation sources to gather additional context.

    This node searches through technology documentation to find information 
    relevant to the changed configuration options.
    """
    pass



def extract_dependencies_node(state: DiffAgentState) -> dict[str, Any]:
    """
    Extract configuration dependencies using CfgNet.

    This node uses CfgNet to analyze the project and extract configuration
    dependencies that will be used in validation to detect violations.
    """
    project_root = state.get("project_root", ".")

    if not project_root or not os.path.exists(project_root):
        print(f"Warning: Project root '{project_root}' not found. Skipping dependency extraction.")
        return {
            "config_dependencies": []
        }

    dependencies = []

    try:
        network_config = NetworkConfiguration(
            project_root_abs=os.path.abspath(project_root),
            enable_static_blacklist=False,
            enable_file_type_plugins=False,
            system_level=False,
            enable_internal_links=True,
            enable_all_conflicts=False
        )

        network = Network.init_network(cfg=network_config)

        if network.links:
            for link in network.links:

                dependency = ConfigDependency(
                    source_file=link.artifact_a.file_path or "",
                    source_option=link.node_a.get_options() or "",
                    source_value=link.node_a.name or "",
                    target_file=link.artifact_b.file_path or "",
                    target_option=link.node_b.get_options() or "",
                    target_value=link.node_b.name or "",
                    dependency_type=link.node_a.config_type 
                )

                print(f"Extracted dependency: {dependency}")

                dependencies.append(dependency)

                
            print(f"Extracted {len(dependencies)} configuration dependencies using CfgNet")

    except subprocess.TimeoutExpired:
        print("CfgNet extraction timed out after 60 seconds")
    except FileNotFoundError:
        print("CfgNet is not installed. Run: pip install cfgnet")
    except Exception as e:
        print(f"Error during CfgNet extraction: {e}")
        traceback.print_exc()

    return {
        "config_dependencies": dependencies
    }


def analyze_changes_node(state: DiffAgentState) -> dict[str, Any]:
    """
    Analyze the extracted changes to determine if they need additional context.

    This node evaluates whether the configuration changes are self-explanatory
    or if additional information from the repository or documentation is needed.
    """
    changed_options = state["changed_options"]

    if not changed_options:
        return {
            "needs_additional_info": False,
            "additional_info": None
        }

    llm = get_llm()

    # Format the changed options for analysis
    options_summary = "\n".join([
        f"- {opt.file_path}: {opt.option_name} changed from '{opt.old_value}' to '{opt.new_value}'"
        for opt in changed_options
    ])

    system_prompt = """You are ChangeAnalyzer-X, an expert at determining whether configuration
changes require additional context for validation.

Analyze the configuration changes and determine if you have enough information to validate them accurately,
or if you need additional context such as:
- Related configuration files in the repository
- Documentation about the configuration options
- Dependencies between configuration values

Respond with a JSON object:
{
  "needs_additional_info": true/false,
  "reasoning": "explanation of why additional info is or isn't needed",
  "info_sources": ["list of sources if needed, e.g., 'check application.properties', 'check Docker documentation'"]
}"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Analyze these configuration changes:\n\n{options_summary}")
    ]

    response = llm.invoke(messages)

    try:
        result = json.loads(response.content)
        needs_info = result.get("needs_additional_info", False)
        additional_info = result.get("reasoning", "")
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error parsing analysis response: {e}")
        needs_info = False
        additional_info = None

    return {
        "needs_additional_info": needs_info,
        "additional_info": additional_info
    }


def detect_errors_node(state: DiffAgentState) -> dict[str, Any]:
    """
    Detect configuration errors in the changed options.

    This node performs deep analysis to identify:
    - Inconsistencies between related configuration values
    - Invalid configuration values
    - Missing required configurations
    - Security issues
    - Best practice violations
    - Dependency violations (using CfgNet extracted dependencies)
    """
    changed_options = state["changed_options"]
    additional_info = state.get("additional_info", "")
    config_dependencies = state.get("config_dependencies", [])

    if not changed_options:
        return {
            "detected_errors": [],
            "validation_complete": True,
            "error_summary": "No configuration changes detected."
        }

    llm = get_llm("gpt-4o")  # Use more powerful model for error detection

    # Format the changed options
    options_detail = "\n\n".join([
        f"File: {opt.file_path}\n"
        f"Option: {opt.option_name}\n"
        f"Old Value: {opt.old_value}\n"
        f"New Value: {opt.new_value}"
        for opt in changed_options
    ])

    # Format configuration dependencies
    dependencies_detail = ""
    if config_dependencies:
        dependencies_detail = "\n\nKNOWN CONFIGURATION DEPENDENCIES (extracted by CfgNet):\n"
        dependencies_detail += "\n".join([
            f"- {dep.source_file}:{dep.source_option}={dep.source_value} -> "
            f"{dep.target_file}:{dep.target_option}={dep.target_value} ({dep.dependency_type})"
            for dep in config_dependencies
        ])
        dependencies_detail += f"\n\nTotal dependencies: {len(config_dependencies)}"

    system_prompt = """You are ConfigValidator-X, an elite configuration validator specialized in
detecting configuration errors, inconsistencies, and potential issues.

Analyze the configuration changes and identify any errors or issues including:

1. **Inconsistencies**: Values that should match but don't (e.g., port numbers in different files)
2. **Invalid Values**: Configuration values that are incorrect or out of range
3. **Security Issues**: Configurations that introduce security vulnerabilities
4. **Missing Dependencies**: Changes that require corresponding changes in other configs
5. **Best Practices**: Violations of configuration best practices
6. **Type Mismatches**: Wrong data types for configuration values
7. **Dependency Violations**: Changes that violate existing configuration dependencies extracted by CfgNet

When configuration dependencies are provided, pay special attention to:
- Check if changed options break existing dependencies
- Verify that dependent configuration values are updated consistently
- Identify missing updates to dependent configurations
- Flag changes that create inconsistencies in the dependency network

For each error found, provide:
- The file path where the error occurs
- The option name
- Severity (critical, warning, or info)
- Clear explanation of why it's an error
- Specific suggested fix

Return a JSON object:
{
  "errors": [
    {
      "file_path": "path/to/file",
      "option_name": "option.name",
      "severity": "critical",
      "reason": "Detailed explanation of the error",
      "suggested_fix": "Specific fix to resolve the issue",
      "old_value": "old_value",
      "new_value": "new_value"
    }
  ],
  "summary": "Brief summary of findings"
}

If no errors are found, return an empty errors list with a positive summary."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Validate these configuration changes:\n\n{options_detail}\n\n"
                             f"Additional context: {additional_info if additional_info else 'None'}"
                             f"{dependencies_detail}")
    ]

    response = llm.invoke(messages)
    
    print("LLM response for error detection:", response.content)
    try:
        result = json.loads(response.content)
        errors = [
            ConfigError(**error)
            for error in result.get("errors", [])
        ]
        summary = result.get("summary", "Validation completed.")
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error parsing validation response: {e}")
        print(f"Response content: {response.content}")
        errors = []
        summary = "Validation completed with parsing errors."

    return {
        "detected_errors": errors,
        "validation_complete": True,
        "error_summary": summary
    }


def should_continue(state: DiffAgentState) -> str:
    """
    Determine the next step based on the current state.

    Returns:
        "detect_errors" to proceed with error detection
        "end" to finish the workflow
    """
    if state.get("validation_complete", False):
        return "end"

    # For now, always proceed directly to error detection
    # In a more complex version, this could check needs_additional_info
    # and route to an information gathering node
    return "detect_errors"

"""State schema for the DiffAgent LangGraph workflow."""

from typing import TypedDict, Optional, Annotated
from operator import add
from models import ChangedOption, ConfigError, ConfigDependency


class DiffAgentState(TypedDict):
    """State that flows through the DiffAgent graph."""

    # Input
    commit_diff: str
    commit_hash: Optional[str]
    project_root: Optional[str]

    # LLM Configuration
    llm_provider: Optional[str]
    llm_model: Optional[str]
    llm_powerful_model: Optional[str]

    # Extracted information
    changed_options: Annotated[list[ChangedOption], add]
    config_dependencies: Annotated[list[ConfigDependency], add]

    # Analysis results
    needs_additional_info: bool
    additional_info: Optional[str]

    # Validation results
    detected_errors: Annotated[list[ConfigError], add]

    # Output
    validation_complete: bool
    error_summary: Optional[str]

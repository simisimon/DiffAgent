"""Data models for the DiffAgent."""

from pydantic import BaseModel, Field
from typing import Optional


class ChangedOption(BaseModel):
    """Represents a changed configuration option."""
    file_path: str = Field(..., description="Path to the modified file.")
    option_name: str = Field(..., description="Name of the configuration option.")
    old_value: str = Field(..., description="Old value of the configuration option.")
    new_value: str = Field(..., description="New value of the configuration option.")
    line_number: Optional[int] = Field(None, description="Line number where the change occurred.")


class CommitChanges(BaseModel):
    """Represents the changes made in a commit."""
    commit_hash: Optional[str] = Field(None, description="Hash of the commit.")
    changed_options: list[ChangedOption] = Field(default_factory=list, description="List of changed configuration options.")


class ConfigError(BaseModel):
    """Represents a configuration error detected in the commit."""
    file_path: str = Field(..., description="Path to the file with the error.")
    option_name: str = Field(..., description="Erroneous configuration option.")
    severity: str = Field(..., description="Severity level: 'critical', 'warning', or 'info'.")
    reason: str = Field(..., description="Explanation of the configuration error.")
    suggested_fix: str = Field(..., description="Potential fix for resolving the configuration error.")
    old_value: Optional[str] = Field(None, description="Old value of the option.")
    new_value: Optional[str] = Field(None, description="New value of the option.")


class ConfigDependency(BaseModel):
    """Represents a configuration dependency extracted by CfgNet."""
    source_file: str = Field(..., description="Source file containing the configuration option.")
    source_option: str = Field(..., description="Source configuration option name.")
    source_value: str = Field(..., description="Value of the source configuration option.")
    target_file: Optional[str] = Field(None, description="Target file that depends on the source.")
    target_option: Optional[str] = Field(None, description="Target configuration option that depends on the source.")
    target_value: Optional[str] = Field(None, description="Value of the target configuration option.")
    dependency_type: str = Field(..., description="Type of dependency (e.g., 'port', 'path', 'reference').")


class ValidationResult(BaseModel):
    """Final validation result containing all detected errors."""
    has_errors: bool = Field(..., description="Indicates if any errors were detected.")
    errors: list[ConfigError] = Field(default_factory=list, description="List of detected configuration errors.")
    summary: str = Field(..., description="Summary of the validation result.")

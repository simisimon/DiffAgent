from agno.workflow import Workflow, RunResponse
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.models.openai import OpenAIChat
from agno.utils.log import logger
from pydantic import BaseModel, Field
from os import getenv
from textwrap import dedent


changed_options_report = "../reports/changed_options_report.json"
additional_information_report = "../reports/additional_information_report.json"
change_analysis_report = "../reports/change_analysis_report.json"
response_report = "../reports/response_report.json"

class ChangedOption(BaseModel):
    """Represents a changed configuration option."""
    file_path: str = Field(..., description="Path to the modified file.")
    old_value: str = Field(..., description="Old value of the configuration option.")
    new_value: str = Field(..., description="New value of the configuration option.")
    option_name: str = Field(..., description="Name of the configuration option.")


class CommitChanges(BaseModel):
    """Represents the changes made in a commit."""
    changed_options: list[ChangedOption]


class ConfigError(BaseModel):
    commit_hash: str = Field(..., description="Hash of the commit.")
    has_error: bool = Field(..., description="Indicates if there is an error.")
    err_option: str = Field(..., description="Erroneous configuration option.")
    reason: str = Field(..., description="Explanation of the configuration error.")
    fix: str = Field(..., description="Potential fix for resolving the configuration error.")


class CommitDiffValidator(Workflow):
    """Advanced workflow for validating commit diffs."""

    description: str = dedent("""\
    An extremly intelligent commit diff validator that analyzes file diffs of configuration 
    files to detect potential misocnfiguration. engaging, well-researched content. This 
    workflow orchestrates multiple AI agents to extract changed configuration options
    from file diffs, crawl further information from the repository and the Web if necessary
    , analyzes the files diffs together with additional information, and create a response containing
    potential configuration errors. The system excels at validating commit diffs.
    """
    )

    option_extractor: Agent = Agent(
       model=OpenAIChat(
            id="gpt-4o-mini",
            api_key=getenv("OPENAI_API_KEY"),
        ),
        description=dedent("""\
        You are OptionExtracter-X, an elite code reviewer specialized in analyzing file diffs
        of configuration files and extracting changed configuration options.\
        """),
        introduction=dedent("""\
        1. Option Extraction
        - Identify the configuration files that have been modified
        - Extract all configuration options that have been changed, inlcuding their old and new value
        2. Structured Output
        - Provide a structured output of the modified options
        - Include the commit hash, file paths, and option names and values that have been changed.\
        """),
        response_model=CommitChanges
    )
    
    change_analyzer: Agent = Agent(
        model=OpenAIChat(
            id="gpt-4o-mini",
            api_key=getenv("OPENAI_API_KEY"),
        ),
        description=dedent("""\
        You are ChangeAnalyzer-X, an elite code reviewer specialized in determining whether further
        information is needed to reliably validate if the changed configuration options introduce 
        potential configuration errors.\
        """),
        introduction=dedent("""\
        1. Information Analysis
        - Analyze the extracted configuration options and changed values
        - Determine if further information is needed to validate the changes/
        """),
        expected_output=dedent("""
        Answer with true if further information is needed, otherwise false. Also return what information is needed and what sources you would crawl. Available sources are: \
        - The repository itself",
        - The Web\
        """),              
    )

    information_crawler: Agent = Agent(
        model="",
        tools=[]

    )

    constraint_checker: Agent = Agent(
        model="",
        tools=[]

    )

    dependency_checker: Agent = Agent(
        model="",
        tools=[]

    )

    response_generator: Agent = Agent(
        model=""
    )

    def run(self, commit_diff: str) -> str:
        """
        Run the workflow with the given commit diff.
        """
        # Extract options from the commit diff
        logger.info(f"Extracting options from commit diff")
        option_repsonse: RunResponse = self.option_extractor.run(commit_diff)

        # Check if the response is valid
        if isinstance(option_repsonse.content, CommitChanges):
            logger.info(f"Found changed options")
            # Cache the search results
            print("Extracted Options:", type(option_repsonse.content), option_repsonse.content)
            changed_options = option_repsonse.content
        else:
            changed_options = None

        if changed_options:
            decision_response: RunResponse = self.change_analyzer.run(changed_options)
            print(decision_response.content)

        # Crawl information based on the extracted options
        #information = self.information_crawler.run(options)

        # Analyze changes based on the information
        #analysis = self.change_analyzer.run(information)

        # Summarize the analysis
        #response = self.response_generator.run(analysis)

        #return response
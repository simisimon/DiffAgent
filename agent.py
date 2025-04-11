import agno
import os

class DiffAgent:
    def __init__(self):
        self.llm = agno.LLM()

    def validate_commit_diff(self, commit_diff):
        """
        Validates the commit diff for configuration errors.
        
        Args:
            commit_diff (str): The diff of the commit to validate.

        Returns:
            list: A list of potential configuration errors.
        """
        # Filter configuration file changes
        config_diffs = self._filter_config_files(commit_diff)
        
        # Validate each configuration file diff
        errors = []
        for file_diff in config_diffs:
            errors.extend(self._validate_config_file(file_diff))
        
        return errors

    def _filter_config_files(self, commit_diff):
        """
        Filters the commit diff to include only configuration file changes.

        Args:
            commit_diff (str): The diff of the commit.

        Returns:
            list: A list of diffs for configuration files.
        """
        # Placeholder logic to filter configuration files
        config_files = []
        for line in commit_diff.splitlines():
            if line.endswith(('.yaml', '.yml', '.json', '.ini', '.cfg')):
                config_files.append(line)
        return config_files

    def _validate_config_file(self, file_diff):
        """
        Validates a single configuration file diff for errors.

        Args:
            file_diff (str): The diff of the configuration file.

        Returns:
            list: A list of potential errors in the configuration file.
        """
        # Use the LLM to analyze the file diff
        response = self.llm.analyze(file_diff)
        return response.get('errors', [])

# Example usage
if __name__ == "__main__":
    agent = DiffAgent()

    # Get the diff from the GitHub environment
    diff_file = os.getenv('GITHUB_EVENT_PATH', 'diff.txt')
    with open(diff_file, 'r') as f:
        commit_diff = f.read()

    # Validate the diff
    errors = agent.validate_commit_diff(commit_diff)

    # Output the results
    with open('results.txt', 'w') as result_file:
        if errors:
            result_file.write("Potential configuration errors:\n")
            result_file.write("\n".join(errors))
        else:
            result_file.write("No configuration errors found.")
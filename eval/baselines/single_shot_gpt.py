"""
Single-shot GPT baseline for configuration validation.
Uses a single LLM call without multi-agent workflow.
"""

import os
import json
from openai import OpenAI
from typing import List, Dict, Any


class SingleShotGPT:
    """Baseline that uses a single GPT-4o call to detect configuration errors."""

    def __init__(self, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def validate(self, diff_content: str) -> Dict[str, Any]:
        """
        Validate configuration changes using a single LLM call.

        Args:
            diff_content: Git diff content

        Returns:
            Dictionary with has_errors, errors list, and summary
        """
        prompt = self._create_prompt(diff_content)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a configuration validation expert. Analyze git diffs and identify potential misconfigurations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return self._format_result(result)

        except Exception as e:
            print(f"Error in single-shot GPT validation: {e}")
            return {
                "has_errors": False,
                "errors": [],
                "summary": f"Validation failed: {str(e)}"
            }

    def _create_prompt(self, diff_content: str) -> str:
        """Create the prompt for single-shot validation."""
        return f"""Analyze the following git diff for configuration file changes and identify any potential errors or misconfigurations.

Git Diff:
```
{diff_content}
```

Look for:
1. **Inconsistencies**: Port mismatches, conflicting settings between files
2. **Invalid values**: Out-of-range values, wrong data types
3. **Security issues**: DEBUG=true in production, exposed secrets, overly permissive settings
4. **Best practice violations**: Missing required settings, deprecated options

Return your analysis as a JSON object with this structure:
{{
  "has_errors": boolean,
  "errors": [
    {{
      "file_path": "path/to/file",
      "option_name": "OPTION_NAME",
      "severity": "critical|warning|info",
      "reason": "Explanation of the issue",
      "suggested_fix": "How to fix it"
    }}
  ],
  "summary": "Brief summary of findings"
}}

If no errors are found, return has_errors: false with an empty errors array."""

    def _format_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure result has the expected format."""
        return {
            "has_errors": result.get("has_errors", False),
            "errors": result.get("errors", []),
            "summary": result.get("summary", "No summary provided")
        }

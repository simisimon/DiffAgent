"""
GitHub data collector for building benchmark datasets.

This script mines GitHub repositories for configuration-related pull requests
and extracts diffs with ground truth labels.
"""

import os
import json
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path


class GitHubCollector:
    """Collect configuration changes from GitHub repositories."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub collector.

        Args:
            github_token: GitHub personal access token (optional but recommended)
        """
        self.token = github_token or os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'

        self.base_url = 'https://api.github.com'

        # Config file patterns
        self.config_patterns = [
            '*.properties', '*.yaml', '*.yml', '*.json', '*.env',
            '*.ini', '*.conf', '*.config', 'Dockerfile', 'docker-compose.yml',
            'settings.py', 'config.py', 'application.yml', 'application.properties'
        ]

    def search_config_prs(
        self,
        query: str,
        max_results: int = 100,
        state: str = 'closed'
    ) -> List[Dict[str, Any]]:
        """
        Search for pull requests related to configuration changes.

        Args:
            query: Search query (e.g., 'fix config', 'revert settings')
            max_results: Maximum number of results to return
            state: PR state ('open', 'closed', 'all')

        Returns:
            List of PR metadata
        """
        print(f"Searching for PRs with query: '{query}'")

        url = f"{self.base_url}/search/issues"
        params = {
            'q': f'{query} is:pr is:{state}',
            'per_page': min(100, max_results),
            'sort': 'updated',
            'order': 'desc'
        }

        prs = []
        page = 1

        while len(prs) < max_results:
            params['page'] = page

            response = self._make_request(url, params=params)
            if not response:
                break

            items = response.get('items', [])
            if not items:
                break

            prs.extend(items)
            print(f"  Retrieved {len(items)} PRs (total: {len(prs)})")

            # Check rate limit
            if response.get('incomplete_results'):
                print("  Warning: Incomplete results from GitHub API")
                break

            page += 1

            # Sleep to respect rate limits
            time.sleep(1)

        return prs[:max_results]

    def get_pr_files(self, repo_full_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get files changed in a pull request.

        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number

        Returns:
            List of changed files with metadata
        """
        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}/files"

        response = self._make_request(url)
        if not response:
            return []

        return response

    def get_pr_diff(self, repo_full_name: str, pr_number: int) -> Optional[str]:
        """
        Get the full diff for a pull request.

        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number

        Returns:
            Diff content as string
        """
        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}"

        headers = self.headers.copy()
        headers['Accept'] = 'application/vnd.github.v3.diff'

        response = self._make_request(url, headers=headers, is_diff=True)
        return response

    def get_pr_comments(self, repo_full_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get comments on a pull request.

        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number

        Returns:
            List of comments
        """
        url = f"{self.base_url}/repos/{repo_full_name}/issues/{pr_number}/comments"

        response = self._make_request(url)
        if not response:
            return []

        return response

    def get_pr_reviews(self, repo_full_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get reviews on a pull request.

        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number

        Returns:
            List of reviews
        """
        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}/reviews"

        response = self._make_request(url)
        if not response:
            return []

        return response

    def is_config_related(self, pr: Dict[str, Any], files: List[Dict[str, Any]]) -> bool:
        """
        Check if PR is related to configuration changes.

        Args:
            pr: PR metadata
            files: List of changed files

        Returns:
            True if PR is config-related
        """
        # Check file names
        for file in files:
            filename = file.get('filename', '')
            for pattern in self.config_patterns:
                if self._matches_pattern(filename, pattern):
                    return True

        # Check PR title/body for config keywords
        title = pr.get('title', '').lower()
        body = pr.get('body', '') or ''
        body = body.lower()

        config_keywords = [
            'config', 'configuration', 'settings', 'dockerfile',
            'environment', 'properties', 'yaml', 'yml'
        ]

        text = f"{title} {body}"
        return any(keyword in text for keyword in config_keywords)

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches pattern."""
        if pattern.startswith('*.'):
            return filename.endswith(pattern[1:])
        return filename.endswith(pattern) or pattern in filename

    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        is_diff: bool = False
    ):
        """
        Make HTTP request to GitHub API.

        Args:
            url: API endpoint URL
            params: Query parameters
            headers: HTTP headers
            is_diff: If True, return raw text response

        Returns:
            JSON response or text for diffs
        """
        headers = headers or self.headers

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)

            # Check rate limit
            if response.status_code == 403:
                print(f"  Rate limit exceeded. Reset at: {response.headers.get('X-RateLimit-Reset')}")
                return None

            response.raise_for_status()

            if is_diff:
                return response.text

            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")
            return None

    def collect_dataset(
        self,
        strategies: List[str],
        max_per_strategy: int = 50,
        output_file: str = 'eval/dataset_builder/collected_data.json'
    ) -> List[Dict[str, Any]]:
        """
        Collect dataset using multiple search strategies.

        Args:
            strategies: List of search strategy names
            max_per_strategy: Maximum PRs per strategy
            output_file: Output file path

        Returns:
            List of collected PR data
        """
        all_data = []

        strategy_queries = {
            'reverted': 'revert config',
            'fix': 'fix config OR fix configuration',
            'bug': 'bug config OR config bug',
            'security': 'security config OR config vulnerability',
            'hotfix': 'hotfix config OR config hotfix',
            'rollback': 'rollback config',
            'incorrect': 'incorrect config OR wrong config',
        }

        for strategy in strategies:
            if strategy not in strategy_queries:
                print(f"Warning: Unknown strategy '{strategy}', skipping")
                continue

            print(f"\n{'='*60}")
            print(f"Strategy: {strategy}")
            print(f"{'='*60}")

            query = strategy_queries[strategy]
            prs = self.search_config_prs(query, max_results=max_per_strategy)

            for pr in prs:
                pr_data = self._extract_pr_data(pr, strategy)
                if pr_data:
                    all_data.append(pr_data)

                time.sleep(0.5)  # Rate limiting

        # Save to file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(all_data, f, indent=2)

        print(f"\n{'='*60}")
        print(f"Collected {len(all_data)} PRs")
        print(f"Saved to {output_file}")
        print(f"{'='*60}")

        return all_data

    def _extract_pr_data(self, pr: Dict[str, Any], strategy: str) -> Optional[Dict[str, Any]]:
        """
        Extract relevant data from a PR.

        Args:
            pr: PR metadata from GitHub API
            strategy: Collection strategy used

        Returns:
            Extracted PR data or None if not config-related
        """
        # Extract repo and PR number
        pr_url = pr.get('pull_request', {}).get('url', '')
        if not pr_url:
            return None

        parts = pr_url.split('/')
        repo_full_name = f"{parts[-4]}/{parts[-3]}"
        pr_number = int(parts[-1])

        print(f"  Processing {repo_full_name}#{pr_number}")

        # Get files changed
        files = self.get_pr_files(repo_full_name, pr_number)
        if not files:
            print(f"    No files found")
            return None

        # Check if config-related
        if not self.is_config_related(pr, files):
            print(f"    Not config-related")
            return None

        # Get diff
        diff = self.get_pr_diff(repo_full_name, pr_number)
        if not diff:
            print(f"    Could not get diff")
            return None

        # Get comments and reviews
        comments = self.get_pr_comments(repo_full_name, pr_number)
        reviews = self.get_pr_reviews(repo_full_name, pr_number)

        # Extract labels
        labels = [label['name'] for label in pr.get('labels', [])]

        print(f"    ✓ Collected ({len(files)} files, {len(comments)} comments)")

        return {
            'id': f"{repo_full_name.replace('/', '_')}_{pr_number}",
            'repo': repo_full_name,
            'pr_number': pr_number,
            'pr_url': pr.get('html_url'),
            'title': pr.get('title'),
            'body': pr.get('body'),
            'state': pr.get('state'),
            'merged': pr.get('pull_request', {}).get('merged_at') is not None,
            'created_at': pr.get('created_at'),
            'closed_at': pr.get('closed_at'),
            'labels': labels,
            'files': [
                {
                    'filename': f.get('filename'),
                    'status': f.get('status'),
                    'additions': f.get('additions'),
                    'deletions': f.get('deletions')
                }
                for f in files
            ],
            'diff': diff,
            'comments': [
                {
                    'body': c.get('body'),
                    'created_at': c.get('created_at')
                }
                for c in comments
            ],
            'reviews': [
                {
                    'state': r.get('state'),
                    'body': r.get('body')
                }
                for r in reviews
            ],
            'collection_strategy': strategy
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Collect GitHub data for benchmark dataset')
    parser.add_argument(
        '--strategies',
        nargs='+',
        default=['reverted', 'fix', 'bug'],
        choices=['reverted', 'fix', 'bug', 'security', 'hotfix', 'rollback', 'incorrect'],
        help='Collection strategies to use'
    )
    parser.add_argument(
        '--max-per-strategy',
        type=int,
        default=50,
        help='Maximum PRs to collect per strategy'
    )
    parser.add_argument(
        '--output',
        default='eval/dataset_builder/collected_data.json',
        help='Output file path'
    )
    parser.add_argument(
        '--token',
        help='GitHub personal access token (or set GITHUB_TOKEN env var)'
    )

    args = parser.parse_args()

    # Check for token
    token = args.token or os.getenv('GITHUB_TOKEN')
    if not token:
        print("Warning: No GitHub token provided. Rate limits will be very restrictive.")
        print("Get a token at: https://github.com/settings/tokens")
        print("Then set GITHUB_TOKEN env var or use --token flag")

    collector = GitHubCollector(github_token=token)
    collector.collect_dataset(
        strategies=args.strategies,
        max_per_strategy=args.max_per_strategy,
        output_file=args.output
    )


if __name__ == '__main__':
    main()

"""
Data filtering and validation for benchmark dataset.

Filters out low-quality data and validates dataset format.
"""

import json
import re
from typing import List, Dict, Any, Optional


class DataFilter:
    """Filter and validate benchmark dataset."""

    def __init__(self):
        self.config_file_patterns = [
            r'\.properties$', r'\.ya?ml$', r'\.json$', r'\.env$',
            r'\.ini$', r'\.conf(ig)?$', r'Dockerfile$', r'docker-compose\.ya?ml$',
            r'settings\.py$', r'config\.py$'
        ]

    def filter_dataset(
        self,
        input_file: str,
        output_file: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Filter dataset based on criteria.

        Args:
            input_file: Input labeled data file
            output_file: Output filtered data file
            filters: Filter criteria

        Returns:
            Statistics about filtering
        """
        filters = filters or {}

        # Load data
        with open(input_file, 'r') as f:
            data = json.load(f)

        print(f"Filtering {len(data)} PRs...")

        filtered_data = []
        stats = {
            'total': len(data),
            'filtered': 0,
            'removed': 0,
            'removal_reasons': {}
        }

        for pr_data in data:
            # Apply filters
            keep, reason = self._should_keep(pr_data, filters)

            if keep:
                filtered_data.append(pr_data)
                stats['filtered'] += 1
            else:
                stats['removed'] += 1
                stats['removal_reasons'][reason] = stats['removal_reasons'].get(reason, 0) + 1

        # Save filtered data
        with open(output_file, 'w') as f:
            json.dump(filtered_data, f, indent=2)

        print(f"\n{'='*60}")
        print(f"Filtering complete!")
        print(f"{'='*60}")
        print(f"Total PRs: {stats['total']}")
        print(f"Kept: {stats['filtered']}")
        print(f"Removed: {stats['removed']}")
        print(f"\nRemoval reasons:")
        for reason, count in sorted(stats['removal_reasons'].items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")
        print(f"\nSaved to {output_file}")

        return stats

    def _should_keep(self, pr_data: Dict[str, Any], filters: Dict[str, Any]) -> tuple:
        """
        Determine if PR should be kept.

        Returns:
            (should_keep, removal_reason)
        """
        # Check if has config files
        if not self._has_config_files(pr_data):
            return False, "no_config_files"

        # Check diff size
        diff = pr_data.get('diff', '')
        if len(diff) < 50:
            return False, "diff_too_small"
        if len(diff) > 50000:  # Very large diffs are hard to process
            return False, "diff_too_large"

        # Check minimum confidence if specified
        min_confidence = filters.get('min_confidence', 0.0)
        confidence = pr_data.get('ground_truth', {}).get('confidence', 0)
        if confidence < min_confidence:
            return False, "low_confidence"

        # Check if requires manual review (optionally filter these out)
        if filters.get('exclude_needs_review', False):
            if pr_data.get('requires_manual_review', False):
                return False, "requires_manual_review"

        # Check error balance (optionally keep only errors or only valid)
        error_filter = filters.get('has_errors')
        if error_filter is not None:
            has_errors = pr_data.get('ground_truth', {}).get('has_errors', False)
            if has_errors != error_filter:
                return False, f"has_errors_mismatch"

        # Check for specific categories
        required_categories = filters.get('categories')
        if required_categories:
            category = pr_data.get('ground_truth', {}).get('category')
            if category not in required_categories:
                return False, "category_mismatch"

        # Check for specific severities
        required_severities = filters.get('severities')
        if required_severities:
            severity = pr_data.get('ground_truth', {}).get('severity')
            if severity not in required_severities:
                return False, "severity_mismatch"

        # All checks passed
        return True, None

    def _has_config_files(self, pr_data: Dict[str, Any]) -> bool:
        """Check if PR has configuration files."""
        files = pr_data.get('files', [])

        for file in files:
            filename = file.get('filename', '')
            for pattern in self.config_file_patterns:
                if re.search(pattern, filename):
                    return True

        return False

    def balance_dataset(
        self,
        input_file: str,
        output_file: str,
        target_ratio: float = 0.5
    ) -> Dict[str, Any]:
        """
        Balance dataset to have desired ratio of errors to valid changes.

        Args:
            input_file: Input file
            output_file: Output file
            target_ratio: Target ratio of has_errors=True (0.0-1.0)

        Returns:
            Statistics
        """
        with open(input_file, 'r') as f:
            data = json.load(f)

        # Separate errors and valid
        with_errors = [d for d in data if d.get('ground_truth', {}).get('has_errors', False)]
        without_errors = [d for d in data if not d.get('ground_truth', {}).get('has_errors', False)]

        print(f"Original dataset:")
        print(f"  With errors: {len(with_errors)}")
        print(f"  Without errors: {len(without_errors)}")
        print(f"  Ratio: {len(with_errors) / len(data):.2f}")

        # Calculate target counts
        total_desired = len(data)
        errors_desired = int(total_desired * target_ratio)
        valid_desired = total_desired - errors_desired

        # Sample to achieve balance
        import random
        random.seed(42)

        if len(with_errors) > errors_desired:
            with_errors = random.sample(with_errors, errors_desired)

        if len(without_errors) > valid_desired:
            without_errors = random.sample(without_errors, valid_desired)

        # Combine and shuffle
        balanced = with_errors + without_errors
        random.shuffle(balanced)

        # Save
        with open(output_file, 'w') as f:
            json.dump(balanced, f, indent=2)

        print(f"\nBalanced dataset:")
        print(f"  With errors: {len(with_errors)}")
        print(f"  Without errors: {len(without_errors)}")
        print(f"  Total: {len(balanced)}")
        print(f"  Ratio: {len(with_errors) / len(balanced):.2f}")
        print(f"\nSaved to {output_file}")

        return {
            'original_total': len(data),
            'balanced_total': len(balanced),
            'with_errors': len(with_errors),
            'without_errors': len(without_errors),
            'ratio': len(with_errors) / len(balanced) if balanced else 0
        }

    def validate_dataset(self, input_file: str) -> bool:
        """
        Validate dataset format and quality.

        Args:
            input_file: Dataset file to validate

        Returns:
            True if valid
        """
        print(f"Validating {input_file}...")

        try:
            with open(input_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ✗ Invalid JSON: {e}")
            return False

        if not isinstance(data, list):
            print(f"  ✗ Data must be a list")
            return False

        required_fields = ['id', 'repo', 'pr_number', 'diff', 'ground_truth']
        ground_truth_fields = ['has_errors', 'confidence']

        issues = []

        for i, item in enumerate(data):
            # Check required fields
            for field in required_fields:
                if field not in item:
                    issues.append(f"Item {i}: Missing field '{field}'")

            # Check ground truth
            if 'ground_truth' in item:
                gt = item['ground_truth']
                for field in ground_truth_fields:
                    if field not in gt:
                        issues.append(f"Item {i}: Missing ground_truth field '{field}'")

                # Validate confidence range
                confidence = gt.get('confidence', 0)
                if not (0 <= confidence <= 1):
                    issues.append(f"Item {i}: Confidence {confidence} out of range [0, 1]")

        if issues:
            print(f"  ✗ Found {len(issues)} issues:")
            for issue in issues[:10]:  # Show first 10
                print(f"    - {issue}")
            if len(issues) > 10:
                print(f"    ... and {len(issues) - 10} more")
            return False

        print(f"  ✓ Valid dataset with {len(data)} items")
        return True

    def convert_to_benchmark_format(
        self,
        input_file: str,
        output_file: str,
        max_items: Optional[int] = None
    ) -> int:
        """
        Convert labeled data to benchmark format for evaluation.

        Args:
            input_file: Labeled data file
            output_file: Benchmark format output file
            max_items: Maximum items to convert

        Returns:
            Number of items converted
        """
        with open(input_file, 'r') as f:
            data = json.load(f)

        if max_items:
            data = data[:max_items]

        benchmark = []

        for item in data:
            # Create benchmark entry
            benchmark_item = {
                'id': item['id'],
                'name': item['title'],
                'diff': item['diff'],
                'ground_truth': {
                    'has_errors': item['ground_truth']['has_errors'],
                    'errors': []  # We don't have specific error details yet
                }
            }

            # If has errors, create a placeholder error entry
            if item['ground_truth']['has_errors']:
                category = item['ground_truth'].get('category', 'other')
                severity = item['ground_truth'].get('severity', 'warning')

                # Try to extract file from diff
                files = item.get('files', [])
                file_path = files[0]['filename'] if files else 'unknown'

                benchmark_item['ground_truth']['errors'].append({
                    'file_path': file_path,
                    'option_name': 'UNKNOWN',  # Requires manual review
                    'severity': severity,
                    'reason': f"Labeled via automated heuristics (confidence: {item['ground_truth']['confidence']:.2f})",
                    'category': category
                })

            benchmark.append(benchmark_item)

        # Save
        with open(output_file, 'w') as f:
            json.dump(benchmark, f, indent=2)

        print(f"Converted {len(benchmark)} items to benchmark format")
        print(f"Saved to {output_file}")

        return len(benchmark)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Filter and validate benchmark dataset')
    parser.add_argument(
        'command',
        choices=['filter', 'balance', 'validate', 'convert'],
        help='Command to execute'
    )
    parser.add_argument(
        '--input',
        default='eval/dataset_builder/labeled_data.json',
        help='Input file'
    )
    parser.add_argument(
        '--output',
        help='Output file'
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.7,
        help='Minimum confidence for filtering'
    )
    parser.add_argument(
        '--target-ratio',
        type=float,
        default=0.5,
        help='Target ratio of errors for balancing'
    )
    parser.add_argument(
        '--max-items',
        type=int,
        help='Maximum items to convert'
    )

    args = parser.parse_args()

    filter_tool = DataFilter()

    if args.command == 'filter':
        output = args.output or 'eval/dataset_builder/filtered_data.json'
        filter_tool.filter_dataset(
            input_file=args.input,
            output_file=output,
            filters={'min_confidence': args.min_confidence}
        )

    elif args.command == 'balance':
        output = args.output or 'eval/dataset_builder/balanced_data.json'
        filter_tool.balance_dataset(
            input_file=args.input,
            output_file=output,
            target_ratio=args.target_ratio
        )

    elif args.command == 'validate':
        filter_tool.validate_dataset(args.input)

    elif args.command == 'convert':
        output = args.output or 'eval/data/benchmark_from_github.json'
        filter_tool.convert_to_benchmark_format(
            input_file=args.input,
            output_file=output,
            max_items=args.max_items
        )


if __name__ == '__main__':
    main()

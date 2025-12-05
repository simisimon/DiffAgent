"""
Complete end-to-end dataset building workflow.

This script runs the entire pipeline:
1. Collect PRs from GitHub
2. Auto-label with heuristics
3. Filter low-quality data
4. Balance the dataset
5. Convert to benchmark format

Usage:
    python eval/dataset_builder/build_dataset.py --size 100
    python eval/dataset_builder/build_dataset.py --size 200 --strategies reverted fix bug security
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from eval.dataset_builder.github_collector import GitHubCollector
from eval.dataset_builder.auto_labeler import AutoLabeler
from eval.dataset_builder.data_filter import DataFilter


def build_dataset(
    target_size: int = 100,
    strategies: list = None,
    min_confidence: float = 0.7,
    target_ratio: float = 0.5,
    output_dir: str = 'eval/dataset_builder',
    github_token: str = None
):
    """
    Run complete dataset building pipeline.

    Args:
        target_size: Target number of items in final dataset
        strategies: Collection strategies to use
        min_confidence: Minimum confidence threshold
        target_ratio: Target ratio of errors
        output_dir: Output directory for intermediate files
        github_token: GitHub personal access token
    """
    strategies = strategies or ['reverted', 'fix', 'bug']

    print(f"\n{'='*80}")
    print(f"Building Dataset")
    print(f"{'='*80}")
    print(f"Target size: {target_size}")
    print(f"Strategies: {', '.join(strategies)}")
    print(f"Min confidence: {min_confidence}")
    print(f"Target error ratio: {target_ratio}")
    print(f"{'='*80}\n")

    # Calculate collection targets (collect 3x to account for filtering)
    collection_target = target_size * 3
    per_strategy = collection_target // len(strategies)

    # File paths
    collected_file = os.path.join(output_dir, 'collected_data.json')
    labeled_file = os.path.join(output_dir, 'labeled_data.json')
    filtered_file = os.path.join(output_dir, 'filtered_data.json')
    balanced_file = os.path.join(output_dir, 'balanced_data.json')
    benchmark_file = 'eval/data/github_benchmark.json'

    # Step 1: Collect from GitHub
    print(f"\nSTEP 1: Collecting PRs from GitHub")
    print(f"{'='*80}")

    collector = GitHubCollector(github_token=github_token)
    collected = collector.collect_dataset(
        strategies=strategies,
        max_per_strategy=per_strategy,
        output_file=collected_file
    )

    print(f"\n✓ Collected {len(collected)} PRs")

    # Step 2: Auto-label
    print(f"\nSTEP 2: Auto-labeling PRs")
    print(f"{'='*80}")

    labeler = AutoLabeler()
    label_stats = labeler.label_dataset(
        input_file=collected_file,
        output_file=labeled_file,
        min_confidence=min_confidence
    )

    print(f"\n✓ Labeled {label_stats['total']} PRs")

    # Step 3: Filter
    print(f"\nSTEP 3: Filtering data")
    print(f"{'='*80}")

    filter_tool = DataFilter()
    filter_stats = filter_tool.filter_dataset(
        input_file=labeled_file,
        output_file=filtered_file,
        filters={'min_confidence': min_confidence}
    )

    print(f"\n✓ Filtered to {filter_stats['filtered']} PRs")

    # Step 4: Balance
    print(f"\nSTEP 4: Balancing dataset")
    print(f"{'='*80}")

    balance_stats = filter_tool.balance_dataset(
        input_file=filtered_file,
        output_file=balanced_file,
        target_ratio=target_ratio
    )

    print(f"\n✓ Balanced to {balance_stats['balanced_total']} PRs")

    # Step 5: Convert to benchmark format
    print(f"\nSTEP 5: Converting to benchmark format")
    print(f"{'='*80}")

    converted = filter_tool.convert_to_benchmark_format(
        input_file=balanced_file,
        output_file=benchmark_file,
        max_items=target_size
    )

    print(f"\n✓ Converted {converted} items")

    # Step 6: Validate
    print(f"\nSTEP 6: Validating dataset")
    print(f"{'='*80}")

    is_valid = filter_tool.validate_dataset(benchmark_file)

    # Final summary
    print(f"\n{'='*80}")
    print(f"Dataset Building Complete!")
    print(f"{'='*80}")
    print(f"\nFinal dataset:")
    print(f"  File: {benchmark_file}")
    print(f"  Size: {converted} items")
    print(f"  With errors: {balance_stats['with_errors']}")
    print(f"  Without errors: {balance_stats['without_errors']}")
    print(f"  Error ratio: {balance_stats['ratio']:.2%}")
    print(f"  Valid: {'Yes' if is_valid else 'No'}")

    print(f"\nIntermediate files:")
    print(f"  Collected: {collected_file}")
    print(f"  Labeled: {labeled_file}")
    print(f"  Filtered: {filtered_file}")
    print(f"  Balanced: {balanced_file}")

    print(f"\nNext steps:")
    print(f"  1. Review low-confidence items:")
    print(f"     python eval/dataset_builder/manual_review.py review \\")
    print(f"       --input {balanced_file} \\")
    print(f"       --filter needs_review")
    print(f"\n  2. Run evaluation:")
    print(f"     python eval/run_evaluation.py \\")
    print(f"       --benchmark {benchmark_file}")
    print(f"\n  3. Visualize results:")
    print(f"     python eval/visualize_results.py \\")
    print(f"       eval/results/comparison.json --all")

    print(f"\n{'='*80}\n")

    return {
        'collected': len(collected),
        'labeled': label_stats['total'],
        'filtered': filter_stats['filtered'],
        'balanced': balance_stats['balanced_total'],
        'final': converted,
        'valid': is_valid
    }


def main():
    parser = argparse.ArgumentParser(
        description='Build a benchmark dataset from GitHub PRs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build a 100-item dataset with default strategies
  python eval/dataset_builder/build_dataset.py --size 100

  # Build a 200-item dataset with custom strategies
  python eval/dataset_builder/build_dataset.py --size 200 --strategies reverted fix bug security

  # Build with higher confidence threshold
  python eval/dataset_builder/build_dataset.py --size 100 --min-confidence 0.8

  # Build security-focused dataset
  python eval/dataset_builder/build_dataset.py --size 50 --strategies security --ratio 0.8
        """
    )

    parser.add_argument(
        '--size',
        type=int,
        default=100,
        help='Target size of final dataset (default: 100)'
    )
    parser.add_argument(
        '--strategies',
        nargs='+',
        default=['reverted', 'fix', 'bug'],
        choices=['reverted', 'fix', 'bug', 'security', 'hotfix', 'rollback', 'incorrect'],
        help='Collection strategies (default: reverted fix bug)'
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.7,
        help='Minimum confidence threshold (default: 0.7)'
    )
    parser.add_argument(
        '--ratio',
        type=float,
        default=0.5,
        help='Target ratio of errors (default: 0.5)'
    )
    parser.add_argument(
        '--output-dir',
        default='eval/dataset_builder',
        help='Output directory for intermediate files'
    )
    parser.add_argument(
        '--token',
        help='GitHub personal access token (or set GITHUB_TOKEN env var)'
    )

    args = parser.parse_args()

    # Check for GitHub token
    token = args.token or os.getenv('GITHUB_TOKEN')
    if not token:
        print("="*80)
        print("WARNING: No GitHub token provided")
        print("="*80)
        print("Rate limits will be very restrictive (60 requests/hour).")
        print("\nTo get a token:")
        print("  1. Visit: https://github.com/settings/tokens")
        print("  2. Generate a new token (classic)")
        print("  3. Select 'public_repo' scope")
        print("  4. Set GITHUB_TOKEN env var or use --token flag")
        print("\nContinuing without token in 5 seconds...")
        print("="*80 + "\n")

        import time
        time.sleep(5)

    # Run pipeline
    try:
        stats = build_dataset(
            target_size=args.size,
            strategies=args.strategies,
            min_confidence=args.min_confidence,
            target_ratio=args.ratio,
            output_dir=args.output_dir,
            github_token=token
        )

        # Exit with success
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Partial progress saved.")
        sys.exit(1)

    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

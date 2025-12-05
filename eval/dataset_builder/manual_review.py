"""
Manual review interface for validating and correcting labels.

Provides a simple CLI interface for reviewing automatically labeled PRs.
"""

import json
import os
from typing import Dict, Any, List, Optional


class ManualReviewer:
    """Manual review interface for dataset validation."""

    def __init__(self):
        self.current_index = 0
        self.data = []
        self.reviewed = []
        self.changes_made = 0

    def load_data(self, input_file: str):
        """Load data for review."""
        with open(input_file, 'r') as f:
            self.data = json.load(f)

        print(f"Loaded {len(self.data)} items for review")

    def review_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review a single item.

        Args:
            item: PR data with ground truth

        Returns:
            Reviewed item with potentially updated labels
        """
        self._display_item(item)

        # Get user input
        while True:
            print("\nOptions:")
            print("  [a] Accept label as-is")
            print("  [e] Edit label")
            print("  [s] Skip (mark for later review)")
            print("  [d] Delete (exclude from dataset)")
            print("  [q] Quit and save progress")

            choice = input("\nYour choice: ").lower().strip()

            if choice == 'a':
                item['manually_reviewed'] = True
                return item

            elif choice == 'e':
                return self._edit_item(item)

            elif choice == 's':
                item['needs_review'] = True
                return item

            elif choice == 'd':
                item['excluded'] = True
                return item

            elif choice == 'q':
                return None

            else:
                print("Invalid choice. Please try again.")

    def _display_item(self, item: Dict[str, Any]):
        """Display item for review."""
        print("\n" + "="*80)
        print(f"Review Item {self.current_index + 1}/{len(self.data)}")
        print("="*80)

        print(f"\nID: {item['id']}")
        print(f"Repo: {item['repo']}#{item['pr_number']}")
        print(f"URL: {item['pr_url']}")
        print(f"\nTitle: {item['title']}")

        # Display ground truth
        gt = item.get('ground_truth', {})
        print(f"\n--- Current Label ---")
        print(f"Has Errors: {gt.get('has_errors')}")
        print(f"Confidence: {gt.get('confidence', 0):.2f}")
        print(f"Category: {gt.get('category')}")
        print(f"Severity: {gt.get('severity')}")
        print(f"\nLabeling Reasons:")
        for reason in gt.get('labeling_reasons', []):
            print(f"  - {reason}")

        # Display diff (truncated)
        diff = item.get('diff', '')
        print(f"\n--- Diff Preview (first 1000 chars) ---")
        print(diff[:1000])
        if len(diff) > 1000:
            print(f"\n... ({len(diff) - 1000} more characters)")

        # Display comments if any
        comments = item.get('comments', [])
        if comments:
            print(f"\n--- Comments ({len(comments)}) ---")
            for i, comment in enumerate(comments[:3], 1):
                print(f"{i}. {comment.get('body', '')[:200]}")
            if len(comments) > 3:
                print(f"... and {len(comments) - 3} more comments")

    def _edit_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Edit item labels."""
        gt = item['ground_truth']

        print("\n--- Edit Labels ---")

        # Edit has_errors
        current = gt.get('has_errors', False)
        response = input(f"Has errors? [{current}] (y/n or Enter to keep): ").lower().strip()
        if response == 'y':
            gt['has_errors'] = True
        elif response == 'n':
            gt['has_errors'] = False

        if gt['has_errors']:
            # Edit category
            current = gt.get('category', 'best_practice')
            print(f"\nCategories: security, inconsistency, invalid_value, best_practice")
            response = input(f"Category? [{current}] (or Enter to keep): ").strip()
            if response:
                gt['category'] = response

            # Edit severity
            current = gt.get('severity', 'warning')
            print(f"\nSeverities: critical, warning, info")
            response = input(f"Severity? [{current}] (or Enter to keep): ").strip()
            if response:
                gt['severity'] = response

        # Set confidence to 1.0 for manually reviewed items
        gt['confidence'] = 1.0
        gt['labeling_reasons'].append("Manually reviewed and corrected")

        item['ground_truth'] = gt
        item['manually_reviewed'] = True

        self.changes_made += 1

        return item

    def review_all(
        self,
        input_file: str,
        output_file: str,
        review_filter: Optional[str] = None,
        start_index: int = 0
    ):
        """
        Review all items in dataset.

        Args:
            input_file: Input labeled data
            output_file: Output file for reviewed data
            review_filter: Filter for which items to review ('needs_review', 'all', 'errors_only')
            start_index: Index to start from (for resuming)
        """
        self.load_data(input_file)

        # Filter items to review
        if review_filter == 'needs_review':
            items_to_review = [
                (i, item) for i, item in enumerate(self.data)
                if item.get('requires_manual_review', False)
            ]
        elif review_filter == 'errors_only':
            items_to_review = [
                (i, item) for i, item in enumerate(self.data)
                if item.get('ground_truth', {}).get('has_errors', False)
            ]
        else:  # 'all'
            items_to_review = list(enumerate(self.data))

        # Skip to start index
        items_to_review = items_to_review[start_index:]

        print(f"\nReviewing {len(items_to_review)} items")
        print(f"Starting from index {start_index}")

        # Review each item
        for idx, (original_idx, item) in enumerate(items_to_review):
            self.current_index = original_idx

            reviewed_item = self.review_item(item)

            if reviewed_item is None:
                # User quit
                print(f"\nQuitting. Reviewed {idx} items, made {self.changes_made} changes.")
                break

            # Update item in original data
            self.data[original_idx] = reviewed_item

            # Save progress periodically
            if idx > 0 and idx % 10 == 0:
                self._save_progress(output_file)
                print(f"\nProgress saved after {idx} reviews")

        # Save final results
        self._save_progress(output_file)
        print(f"\n{'='*80}")
        print(f"Review complete!")
        print(f"Total items reviewed: {len(items_to_review)}")
        print(f"Changes made: {self.changes_made}")
        print(f"Saved to {output_file}")
        print(f"{'='*80}")

    def _save_progress(self, output_file: str):
        """Save current progress."""
        with open(output_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def generate_review_stats(self, input_file: str):
        """Generate statistics about review status."""
        with open(input_file, 'r') as f:
            data = json.load(f)

        stats = {
            'total': len(data),
            'manually_reviewed': 0,
            'needs_review': 0,
            'excluded': 0,
            'high_confidence': 0,
            'low_confidence': 0
        }

        for item in data:
            if item.get('manually_reviewed', False):
                stats['manually_reviewed'] += 1
            if item.get('needs_review', False):
                stats['needs_review'] += 1
            if item.get('excluded', False):
                stats['excluded'] += 1

            confidence = item.get('ground_truth', {}).get('confidence', 0)
            if confidence >= 0.8:
                stats['high_confidence'] += 1
            else:
                stats['low_confidence'] += 1

        print(f"\n{'='*60}")
        print(f"Review Statistics")
        print(f"{'='*60}")
        print(f"Total items: {stats['total']}")
        print(f"Manually reviewed: {stats['manually_reviewed']}")
        print(f"Needs review: {stats['needs_review']}")
        print(f"Excluded: {stats['excluded']}")
        print(f"High confidence (≥0.8): {stats['high_confidence']}")
        print(f"Low confidence (<0.8): {stats['low_confidence']}")

        return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Manual review interface for dataset')
    parser.add_argument(
        'command',
        choices=['review', 'stats'],
        help='Command to execute'
    )
    parser.add_argument(
        '--input',
        default='eval/dataset_builder/labeled_data.json',
        help='Input labeled data file'
    )
    parser.add_argument(
        '--output',
        default='eval/dataset_builder/reviewed_data.json',
        help='Output file for reviewed data'
    )
    parser.add_argument(
        '--filter',
        choices=['all', 'needs_review', 'errors_only'],
        default='needs_review',
        help='Which items to review'
    )
    parser.add_argument(
        '--start',
        type=int,
        default=0,
        help='Index to start from (for resuming)'
    )

    args = parser.parse_args()

    reviewer = ManualReviewer()

    if args.command == 'review':
        reviewer.review_all(
            input_file=args.input,
            output_file=args.output,
            review_filter=args.filter,
            start_index=args.start
        )
    elif args.command == 'stats':
        reviewer.generate_review_stats(args.input)


if __name__ == '__main__':
    main()

"""
Automatic labeling of GitHub PRs to create ground truth.

Uses heuristics to determine if a configuration change has errors:
1. Reverted PRs → likely had errors
2. Follow-up fixes within 24-48h → likely had errors
3. Negative review comments → likely has errors
4. "bug", "fix", "revert" in title → likely had errors
5. Successfully merged with positive reviews → likely valid
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple


class AutoLabeler:
    """Automatically label PRs with ground truth based on heuristics."""

    def __init__(self):
        # Keywords indicating errors
        self.error_keywords = [
            'revert', 'fix', 'bug', 'issue', 'problem', 'incorrect',
            'wrong', 'broken', 'error', 'mistake', 'rollback', 'hotfix'
        ]

        # Keywords indicating specific error types
        self.security_keywords = [
            'security', 'vulnerability', 'exposed', 'leak', 'secret',
            'token', 'password', 'key', 'credential', 'auth'
        ]

        self.inconsistency_keywords = [
            'mismatch', 'inconsistent', 'conflict', 'differ', 'sync'
        ]

        self.invalid_keywords = [
            'invalid', 'out of range', 'too high', 'too low', 'exceed'
        ]

    def label_pr(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Label a PR with ground truth.

        Args:
            pr_data: PR data from GitHub collector

        Returns:
            Labeled data with ground_truth field
        """
        # Extract signals
        signals = self._extract_signals(pr_data)

        # Determine if has errors
        has_errors, confidence, reasons = self._determine_errors(signals)

        # Determine error category if errors exist
        category = self._determine_category(signals) if has_errors else None
        severity = self._determine_severity(signals, category) if has_errors else None

        # Create ground truth
        ground_truth = {
            'has_errors': has_errors,
            'confidence': confidence,
            'labeling_reasons': reasons,
            'category': category,
            'severity': severity,
            'signals': signals
        }

        # Add ground truth to PR data
        labeled_data = pr_data.copy()
        labeled_data['ground_truth'] = ground_truth
        labeled_data['requires_manual_review'] = confidence < 0.8

        return labeled_data

    def _extract_signals(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract signals from PR data."""
        title = pr_data.get('title', '').lower()
        body = pr_data.get('body', '') or ''
        body = body.lower()
        labels = [l.lower() for l in pr_data.get('labels', [])]

        # Combine all text
        all_text = f"{title} {body}"

        # Extract signals
        signals = {
            # Basic info
            'merged': pr_data.get('merged', False),
            'state': pr_data.get('state'),

            # Title/body analysis
            'has_revert_keyword': any(kw in title for kw in ['revert', 'rollback']),
            'has_fix_keyword': any(kw in title for kw in ['fix', 'hotfix']),
            'has_bug_keyword': 'bug' in all_text,
            'has_error_keyword': any(kw in all_text for kw in self.error_keywords),

            # Category indicators
            'has_security_keyword': any(kw in all_text for kw in self.security_keywords),
            'has_inconsistency_keyword': any(kw in all_text for kw in self.inconsistency_keywords),
            'has_invalid_keyword': any(kw in all_text for kw in self.invalid_keywords),

            # Labels
            'has_bug_label': any(label in labels for label in ['bug', 'bugfix', 'fix']),
            'has_security_label': 'security' in labels,
            'has_hotfix_label': 'hotfix' in labels,

            # Reviews
            'num_comments': len(pr_data.get('comments', [])),
            'num_reviews': len(pr_data.get('reviews', [])),
            'has_changes_requested': any(
                r.get('state') == 'CHANGES_REQUESTED'
                for r in pr_data.get('reviews', [])
            ),
            'has_approved': any(
                r.get('state') == 'APPROVED'
                for r in pr_data.get('reviews', [])
            ),

            # Comments analysis
            'has_negative_comments': self._has_negative_comments(pr_data.get('comments', [])),

            # Collection strategy
            'collection_strategy': pr_data.get('collection_strategy')
        }

        return signals

    def _has_negative_comments(self, comments: List[Dict[str, Any]]) -> bool:
        """Check if comments indicate problems."""
        negative_patterns = [
            r'this (breaks|broke)',
            r'(incorrect|wrong|invalid)',
            r'should (not|be)',
            r'(issue|problem|error)',
            r'(revert|rollback)',
            r'needs? (fix|change)',
        ]

        for comment in comments:
            body = comment.get('body', '').lower()
            for pattern in negative_patterns:
                if re.search(pattern, body):
                    return True

        return False

    def _determine_errors(self, signals: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
        """
        Determine if PR has errors based on signals.

        Returns:
            (has_errors, confidence, reasons)
        """
        confidence = 0.5  # Start neutral
        reasons = []

        # Strong indicators of errors
        if signals['has_revert_keyword']:
            confidence += 0.35
            reasons.append("Title contains 'revert'")

        if signals['has_bug_label'] or signals['has_hotfix_label']:
            confidence += 0.25
            reasons.append("Labeled as bug/hotfix")

        if signals['has_changes_requested']:
            confidence += 0.15
            reasons.append("Changes requested in review")

        if signals['has_fix_keyword']:
            confidence += 0.20
            reasons.append("Title contains 'fix'")

        if signals['has_negative_comments']:
            confidence += 0.15
            reasons.append("Negative comments detected")

        if signals['collection_strategy'] in ['reverted', 'fix', 'bug', 'hotfix', 'rollback']:
            confidence += 0.10
            reasons.append(f"Collected via '{signals['collection_strategy']}' strategy")

        # Indicators of valid changes
        if signals['has_approved'] and signals['merged']:
            confidence -= 0.20
            reasons.append("Approved and merged successfully")

        if not signals['has_error_keyword'] and signals['merged']:
            confidence -= 0.10
            reasons.append("No error keywords and merged")

        # Clamp confidence
        confidence = max(0.0, min(1.0, confidence))

        # Decision threshold
        has_errors = confidence > 0.6

        return has_errors, confidence, reasons

    def _determine_category(self, signals: Dict[str, Any]) -> str:
        """Determine error category based on signals."""
        if signals['has_security_keyword'] or signals['has_security_label']:
            return 'security'

        if signals['has_inconsistency_keyword']:
            return 'inconsistency'

        if signals['has_invalid_keyword']:
            return 'invalid_value'

        # Default
        return 'best_practice'

    def _determine_severity(self, signals: Dict[str, Any], category: Optional[str]) -> str:
        """Determine error severity."""
        # Security issues are always critical
        if category == 'security':
            return 'critical'

        # Hotfixes and reverts are usually critical
        if signals['has_revert_keyword'] or signals['has_hotfix_label']:
            return 'critical'

        # Changes requested usually indicates at least warning
        if signals['has_changes_requested']:
            return 'warning'

        # Default
        return 'warning'

    def label_dataset(
        self,
        input_file: str,
        output_file: str,
        min_confidence: float = 0.0
    ) -> Dict[str, Any]:
        """
        Label entire dataset.

        Args:
            input_file: Input JSON file from collector
            output_file: Output JSON file with labels
            min_confidence: Minimum confidence to include

        Returns:
            Statistics about labeling
        """
        # Load data
        with open(input_file, 'r') as f:
            data = json.load(f)

        print(f"Labeling {len(data)} PRs...")

        labeled_data = []
        stats = {
            'total': len(data),
            'has_errors': 0,
            'no_errors': 0,
            'requires_review': 0,
            'high_confidence': 0,
            'by_category': {},
            'by_severity': {}
        }

        for pr_data in data:
            labeled = self.label_pr(pr_data)

            # Filter by confidence
            if labeled['ground_truth']['confidence'] >= min_confidence:
                labeled_data.append(labeled)

                # Update stats
                if labeled['ground_truth']['has_errors']:
                    stats['has_errors'] += 1

                    category = labeled['ground_truth']['category']
                    stats['by_category'][category] = stats['by_category'].get(category, 0) + 1

                    severity = labeled['ground_truth']['severity']
                    stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
                else:
                    stats['no_errors'] += 1

                if labeled['requires_manual_review']:
                    stats['requires_review'] += 1
                else:
                    stats['high_confidence'] += 1

        # Save labeled data
        with open(output_file, 'w') as f:
            json.dump(labeled_data, f, indent=2)

        print(f"\n{'='*60}")
        print(f"Labeling complete!")
        print(f"{'='*60}")
        print(f"Total PRs: {stats['total']}")
        print(f"Labeled: {len(labeled_data)}")
        print(f"  With errors: {stats['has_errors']}")
        print(f"  No errors: {stats['no_errors']}")
        print(f"  High confidence: {stats['high_confidence']}")
        print(f"  Requires manual review: {stats['requires_review']}")
        print(f"\nBy category:")
        for category, count in stats['by_category'].items():
            print(f"  {category}: {count}")
        print(f"\nBy severity:")
        for severity, count in stats['by_severity'].items():
            print(f"  {severity}: {count}")
        print(f"\nSaved to {output_file}")

        return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Auto-label GitHub PRs for benchmark dataset')
    parser.add_argument(
        '--input',
        default='eval/dataset_builder/collected_data.json',
        help='Input file from GitHub collector'
    )
    parser.add_argument(
        '--output',
        default='eval/dataset_builder/labeled_data.json',
        help='Output file with labels'
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.6,
        help='Minimum confidence to include (0.0-1.0)'
    )

    args = parser.parse_args()

    labeler = AutoLabeler()
    labeler.label_dataset(
        input_file=args.input,
        output_file=args.output,
        min_confidence=args.min_confidence
    )


if __name__ == '__main__':
    main()

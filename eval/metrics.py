"""
Evaluation metrics for configuration validation systems.
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict


class EvaluationMetrics:
    """Calculate evaluation metrics for configuration validation."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all counters."""
        self.true_positives = 0
        self.false_positives = 0
        self.true_negatives = 0
        self.false_negatives = 0

        # Track by severity
        self.severity_stats = {
            'critical': {'tp': 0, 'fp': 0, 'fn': 0},
            'warning': {'tp': 0, 'fp': 0, 'fn': 0},
            'info': {'tp': 0, 'fp': 0, 'fn': 0}
        }

        # Track by category
        self.category_stats = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})

    def add_prediction(self, ground_truth: Dict[str, Any], prediction: Dict[str, Any]):
        """
        Add a prediction for evaluation.

        Args:
            ground_truth: Ground truth with has_errors and errors list
            prediction: Model prediction with has_errors and errors list
        """
        gt_has_errors = ground_truth.get('has_errors', False)
        pred_has_errors = prediction.get('has_errors', False)

        gt_errors = ground_truth.get('errors', [])
        pred_errors = prediction.get('errors', [])

        # Binary classification metrics (has errors or not)
        if gt_has_errors and pred_has_errors:
            self.true_positives += 1
        elif not gt_has_errors and not pred_has_errors:
            self.true_negatives += 1
        elif not gt_has_errors and pred_has_errors:
            self.false_positives += 1
        elif gt_has_errors and not pred_has_errors:
            self.false_negatives += 1

        # Detailed error matching
        self._match_errors(gt_errors, pred_errors)

    def _match_errors(self, gt_errors: List[Dict], pred_errors: List[Dict]):
        """
        Match predicted errors to ground truth errors.

        An error matches if file_path and option_name are the same.
        """
        matched_gt = set()
        matched_pred = set()

        # Match errors
        for i, pred_error in enumerate(pred_errors):
            for j, gt_error in enumerate(gt_errors):
                if j in matched_gt:
                    continue

                # Check if errors match (same file and option)
                if (self._normalize_path(pred_error.get('file_path', '')) ==
                    self._normalize_path(gt_error.get('file_path', '')) and
                    pred_error.get('option_name', '').lower() ==
                    gt_error.get('option_name', '').lower()):

                    matched_gt.add(j)
                    matched_pred.add(i)

                    # Update severity stats
                    severity = gt_error.get('severity', 'warning')
                    if severity in self.severity_stats:
                        self.severity_stats[severity]['tp'] += 1

                    # Update category stats
                    category = gt_error.get('category', 'other')
                    self.category_stats[category]['tp'] += 1

                    break

        # Count false positives (predicted but not in ground truth)
        for i, pred_error in enumerate(pred_errors):
            if i not in matched_pred:
                severity = pred_error.get('severity', 'warning')
                if severity in self.severity_stats:
                    self.severity_stats[severity]['fp'] += 1

                category = pred_error.get('category', 'other')
                self.category_stats[category]['fp'] += 1

        # Count false negatives (in ground truth but not predicted)
        for j, gt_error in enumerate(gt_errors):
            if j not in matched_gt:
                severity = gt_error.get('severity', 'warning')
                if severity in self.severity_stats:
                    self.severity_stats[severity]['fn'] += 1

                category = gt_error.get('category', 'other')
                self.category_stats[category]['fn'] += 1

    def _normalize_path(self, path: str) -> str:
        """Normalize file path for comparison."""
        return path.replace('\\', '/').strip().lower()

    def precision(self, tp: int = None, fp: int = None) -> float:
        """Calculate precision: TP / (TP + FP)"""
        tp = tp if tp is not None else self.true_positives
        fp = fp if fp is not None else self.false_positives

        if tp + fp == 0:
            return 0.0
        return tp / (tp + fp)

    def recall(self, tp: int = None, fn: int = None) -> float:
        """Calculate recall: TP / (TP + FN)"""
        tp = tp if tp is not None else self.true_positives
        fn = fn if fn is not None else self.false_negatives

        if tp + fn == 0:
            return 0.0
        return tp / (tp + fn)

    def f1_score(self, precision: float = None, recall: float = None) -> float:
        """Calculate F1 score: 2 * (precision * recall) / (precision + recall)"""
        if precision is None:
            precision = self.precision()
        if recall is None:
            recall = self.recall()

        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def accuracy(self) -> float:
        """Calculate accuracy: (TP + TN) / (TP + TN + FP + FN)"""
        total = self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total

    def false_positive_rate(self) -> float:
        """Calculate FPR: FP / (FP + TN)"""
        if self.false_positives + self.true_negatives == 0:
            return 0.0
        return self.false_positives / (self.false_positives + self.true_negatives)

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary."""
        precision = self.precision()
        recall = self.recall()

        return {
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(self.f1_score(precision, recall), 4),
            'accuracy': round(self.accuracy(), 4),
            'false_positive_rate': round(self.false_positive_rate(), 4),
            'true_positives': self.true_positives,
            'false_positives': self.false_positives,
            'true_negatives': self.true_negatives,
            'false_negatives': self.false_negatives
        }

    def get_severity_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get metrics broken down by severity level."""
        severity_metrics = {}

        for severity, stats in self.severity_stats.items():
            tp = stats['tp']
            fp = stats['fp']
            fn = stats['fn']

            precision = self.precision(tp, fp)
            recall = self.recall(tp, fn)

            severity_metrics[severity] = {
                'precision': round(precision, 4),
                'recall': round(recall, 4),
                'f1_score': round(self.f1_score(precision, recall), 4),
                'true_positives': tp,
                'false_positives': fp,
                'false_negatives': fn
            }

        return severity_metrics

    def get_category_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get metrics broken down by error category."""
        category_metrics = {}

        for category, stats in self.category_stats.items():
            tp = stats['tp']
            fp = stats['fp']
            fn = stats['fn']

            precision = self.precision(tp, fp)
            recall = self.recall(tp, fn)

            category_metrics[category] = {
                'precision': round(precision, 4),
                'recall': round(recall, 4),
                'f1_score': round(self.f1_score(precision, recall), 4),
                'true_positives': tp,
                'false_positives': fp,
                'false_negatives': fn
            }

        return category_metrics

    def print_summary(self, name: str = "Model"):
        """Print a summary of metrics."""
        metrics = self.get_metrics()

        print(f"\n{name} Evaluation Results")
        print("=" * 50)
        print(f"Precision:            {metrics['precision']:.4f}")
        print(f"Recall:               {metrics['recall']:.4f}")
        print(f"F1 Score:             {metrics['f1_score']:.4f}")
        print(f"Accuracy:             {metrics['accuracy']:.4f}")
        print(f"False Positive Rate:  {metrics['false_positive_rate']:.4f}")
        print(f"\nConfusion Matrix:")
        print(f"  True Positives:     {metrics['true_positives']}")
        print(f"  False Positives:    {metrics['false_positives']}")
        print(f"  True Negatives:     {metrics['true_negatives']}")
        print(f"  False Negatives:    {metrics['false_negatives']}")

        # Print severity breakdown
        print(f"\nMetrics by Severity:")
        severity_metrics = self.get_severity_metrics()
        for severity, smetrics in severity_metrics.items():
            if smetrics['true_positives'] + smetrics['false_positives'] + smetrics['false_negatives'] > 0:
                print(f"  {severity.upper()}:")
                print(f"    Precision: {smetrics['precision']:.4f}, Recall: {smetrics['recall']:.4f}, F1: {smetrics['f1_score']:.4f}")

        # Print category breakdown
        print(f"\nMetrics by Category:")
        category_metrics = self.get_category_metrics()
        for category, cmetrics in category_metrics.items():
            if cmetrics['true_positives'] + cmetrics['false_positives'] + cmetrics['false_negatives'] > 0:
                print(f"  {category}:")
                print(f"    Precision: {cmetrics['precision']:.4f}, Recall: {cmetrics['recall']:.4f}, F1: {cmetrics['f1_score']:.4f}")

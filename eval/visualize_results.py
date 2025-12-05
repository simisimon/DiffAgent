"""
Visualize evaluation results for research papers.

This script takes evaluation results and generates tables and charts
suitable for inclusion in research papers.
"""

import json
import sys
from typing import Dict, Any


def generate_latex_table(results: Dict[str, Any]) -> str:
    """
    Generate a LaTeX table for research paper.

    Args:
        results: Evaluation results dictionary

    Returns:
        LaTeX table code
    """
    latex = []
    latex.append("\\begin{table}[h]")
    latex.append("\\centering")
    latex.append("\\caption{Performance Comparison of Configuration Validation Approaches}")
    latex.append("\\label{tab:performance_comparison}")
    latex.append("\\begin{tabular}{lcccccc}")
    latex.append("\\hline")
    latex.append("\\textbf{Model} & \\textbf{Precision} & \\textbf{Recall} & \\textbf{F1 Score} & \\textbf{FPR} & \\textbf{Time (s)} \\\\")
    latex.append("\\hline")

    # Sort by F1 score descending
    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1]['metrics']['f1_score'],
        reverse=True
    )

    for model_name, result in sorted_results:
        metrics = result['metrics']
        timing = result['timing']

        model_display = model_name.replace('_', '\\_')

        latex.append(
            f"{model_display} & "
            f"{metrics['precision']:.3f} & "
            f"{metrics['recall']:.3f} & "
            f"\\textbf{{{metrics['f1_score']:.3f}}} & "
            f"{metrics['false_positive_rate']:.3f} & "
            f"{timing['avg_time_per_test']:.2f} \\\\"
        )

    latex.append("\\hline")
    latex.append("\\end{tabular}")
    latex.append("\\end{table}")

    return '\n'.join(latex)


def generate_markdown_table(results: Dict[str, Any]) -> str:
    """
    Generate a Markdown table for README or documentation.

    Args:
        results: Evaluation results dictionary

    Returns:
        Markdown table
    """
    lines = []
    lines.append("| Model | Precision | Recall | F1 Score | FPR | Avg Time (s) |")
    lines.append("|-------|-----------|--------|----------|-----|--------------|")

    # Sort by F1 score descending
    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1]['metrics']['f1_score'],
        reverse=True
    )

    for model_name, result in sorted_results:
        metrics = result['metrics']
        timing = result['timing']

        lines.append(
            f"| {model_name} | "
            f"{metrics['precision']:.4f} | "
            f"{metrics['recall']:.4f} | "
            f"**{metrics['f1_score']:.4f}** | "
            f"{metrics['false_positive_rate']:.4f} | "
            f"{timing['avg_time_per_test']:.2f} |"
        )

    return '\n'.join(lines)


def generate_severity_breakdown(results: Dict[str, Any]) -> str:
    """
    Generate severity breakdown table.

    Args:
        results: Evaluation results dictionary

    Returns:
        Markdown table with severity breakdown
    """
    lines = []
    lines.append("\n## Performance by Severity Level\n")

    for model_name, result in results.items():
        lines.append(f"\n### {model_name}\n")
        lines.append("| Severity | Precision | Recall | F1 Score | TP | FP | FN |")
        lines.append("|----------|-----------|--------|----------|----|----|-----|")

        severity_metrics = result['severity_metrics']
        for severity in ['critical', 'warning', 'info']:
            if severity in severity_metrics:
                sm = severity_metrics[severity]
                lines.append(
                    f"| {severity.capitalize()} | "
                    f"{sm['precision']:.4f} | "
                    f"{sm['recall']:.4f} | "
                    f"{sm['f1_score']:.4f} | "
                    f"{sm['true_positives']} | "
                    f"{sm['false_positives']} | "
                    f"{sm['false_negatives']} |"
                )

    return '\n'.join(lines)


def generate_category_breakdown(results: Dict[str, Any]) -> str:
    """
    Generate category breakdown table.

    Args:
        results: Evaluation results dictionary

    Returns:
        Markdown table with category breakdown
    """
    lines = []
    lines.append("\n## Performance by Error Category\n")

    for model_name, result in results.items():
        lines.append(f"\n### {model_name}\n")
        lines.append("| Category | Precision | Recall | F1 Score | TP | FP | FN |")
        lines.append("|----------|-----------|--------|----------|----|----|-----|")

        category_metrics = result['category_metrics']
        for category, cm in sorted(category_metrics.items()):
            lines.append(
                f"| {category} | "
                f"{cm['precision']:.4f} | "
                f"{cm['recall']:.4f} | "
                f"{cm['f1_score']:.4f} | "
                f"{cm['true_positives']} | "
                f"{cm['false_positives']} | "
                f"{cm['false_negatives']} |"
            )

    return '\n'.join(lines)


def generate_confusion_matrices(results: Dict[str, Any]) -> str:
    """
    Generate confusion matrix visualization.

    Args:
        results: Evaluation results dictionary

    Returns:
        ASCII art confusion matrices
    """
    lines = []
    lines.append("\n## Confusion Matrices\n")

    for model_name, result in results.items():
        metrics = result['metrics']

        lines.append(f"\n### {model_name}\n")
        lines.append("```")
        lines.append("                 Predicted")
        lines.append("                Pos    Neg")
        lines.append("Actual  Pos  |  {:3d}  |  {:3d}  |".format(
            metrics['true_positives'],
            metrics['false_negatives']
        ))
        lines.append("        Neg  |  {:3d}  |  {:3d}  |".format(
            metrics['false_positives'],
            metrics['true_negatives']
        ))
        lines.append("```")

    return '\n'.join(lines)


def generate_summary_stats(results: Dict[str, Any]) -> str:
    """
    Generate summary statistics.

    Args:
        results: Evaluation results dictionary

    Returns:
        Summary statistics text
    """
    lines = []
    lines.append("\n## Summary Statistics\n")

    # Find best model by different metrics
    best_f1 = max(results.items(), key=lambda x: x[1]['metrics']['f1_score'])
    best_precision = max(results.items(), key=lambda x: x[1]['metrics']['precision'])
    best_recall = max(results.items(), key=lambda x: x[1]['metrics']['recall'])
    fastest = min(results.items(), key=lambda x: x[1]['timing']['avg_time_per_test'])

    lines.append(f"- **Best F1 Score**: {best_f1[0]} ({best_f1[1]['metrics']['f1_score']:.4f})")
    lines.append(f"- **Best Precision**: {best_precision[0]} ({best_precision[1]['metrics']['precision']:.4f})")
    lines.append(f"- **Best Recall**: {best_recall[0]} ({best_recall[1]['metrics']['recall']:.4f})")
    lines.append(f"- **Fastest**: {fastest[0]} ({fastest[1]['timing']['avg_time_per_test']:.2f}s)")

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python eval/visualize_results.py <results.json> [--latex] [--markdown] [--all]")
        print("\nOptions:")
        print("  --latex      Generate LaTeX table")
        print("  --markdown   Generate Markdown tables")
        print("  --all        Generate all visualizations")
        sys.exit(1)

    results_file = sys.argv[1]

    # Load results
    try:
        with open(results_file, 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{results_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in '{results_file}'")
        sys.exit(1)

    # Determine what to generate
    generate_latex = '--latex' in sys.argv or '--all' in sys.argv
    generate_md = '--markdown' in sys.argv or '--all' in sys.argv

    if not generate_latex and not generate_md:
        # Default to markdown if nothing specified
        generate_md = True

    # Generate outputs
    if generate_latex:
        print("\n" + "=" * 80)
        print("LaTeX Table")
        print("=" * 80)
        print(generate_latex_table(results))

    if generate_md:
        print("\n" + "=" * 80)
        print("Markdown Table")
        print("=" * 80)
        print(generate_markdown_table(results))

        print(generate_summary_stats(results))
        print(generate_severity_breakdown(results))
        print(generate_category_breakdown(results))
        print(generate_confusion_matrices(results))


if __name__ == '__main__':
    main()

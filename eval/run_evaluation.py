"""
Main evaluation script to compare DiffAgent with baselines.

Usage:
    python eval/run_evaluation.py
    python eval/run_evaluation.py --models diffagent single_shot rule_based
    python eval/run_evaluation.py --output results/comparison.json
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path to import agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import DiffAgent
from eval.baselines.single_shot_gpt import SingleShotGPT
from eval.baselines.rule_based import RuleBasedValidator
from eval.metrics import EvaluationMetrics


class BenchmarkRunner:
    """Run benchmarks and compare different models."""

    def __init__(self, benchmark_path: str = "eval/data/benchmark.json"):
        self.benchmark_path = benchmark_path
        self.benchmark_data = self._load_benchmark()

        # Initialize models
        self.models = {
            'diffagent': DiffAgent(),
            'single_shot_gpt4o': SingleShotGPT(model='gpt-4o'),
            'single_shot_gpt4o_mini': SingleShotGPT(model='gpt-4o-mini'),
            'rule_based': RuleBasedValidator()
        }

    def _load_benchmark(self) -> List[Dict[str, Any]]:
        """Load benchmark dataset."""
        with open(self.benchmark_path, 'r') as f:
            return json.load(f)

    def run_single_test(self, model_name: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single test case with a model.

        Args:
            model_name: Name of the model to test
            test_case: Test case with diff and ground_truth

        Returns:
            Dictionary with prediction and timing info
        """
        model = self.models[model_name]
        diff = test_case['diff']

        start_time = time.time()

        try:
            if model_name == 'diffagent':
                # DiffAgent uses run() method
                result = model.run(diff)
            else:
                # Baselines use validate() method
                result = model.validate(diff)

            elapsed = time.time() - start_time

            return {
                'prediction': result,
                'elapsed_time': elapsed,
                'success': True,
                'error': None
            }

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  Error in {model_name} for test {test_case['id']}: {e}")

            return {
                'prediction': {'has_errors': False, 'errors': [], 'summary': f'Error: {str(e)}'},
                'elapsed_time': elapsed,
                'success': False,
                'error': str(e)
            }

    def evaluate_model(self, model_name: str) -> Dict[str, Any]:
        """
        Evaluate a single model on the entire benchmark.

        Args:
            model_name: Name of the model to evaluate

        Returns:
            Dictionary with metrics and detailed results
        """
        print(f"\nEvaluating {model_name}...")
        print("-" * 50)

        metrics = EvaluationMetrics()
        detailed_results = []
        total_time = 0
        successes = 0

        for test_case in self.benchmark_data:
            test_id = test_case['id']
            print(f"  Running {test_id}...", end=" ")

            result = self.run_single_test(model_name, test_case)

            if result['success']:
                successes += 1
                print(f"✓ ({result['elapsed_time']:.2f}s)")
            else:
                print(f"✗ (error: {result['error']})")

            # Update metrics
            metrics.add_prediction(
                test_case['ground_truth'],
                result['prediction']
            )

            total_time += result['elapsed_time']

            detailed_results.append({
                'test_id': test_id,
                'test_name': test_case['name'],
                'ground_truth': test_case['ground_truth'],
                'prediction': result['prediction'],
                'elapsed_time': result['elapsed_time'],
                'success': result['success']
            })

        # Get metrics
        overall_metrics = metrics.get_metrics()
        severity_metrics = metrics.get_severity_metrics()
        category_metrics = metrics.get_category_metrics()

        # Print summary
        metrics.print_summary(model_name)
        print(f"\nTotal time: {total_time:.2f}s")
        print(f"Average time per test: {total_time / len(self.benchmark_data):.2f}s")
        print(f"Success rate: {successes}/{len(self.benchmark_data)}")

        return {
            'model': model_name,
            'metrics': overall_metrics,
            'severity_metrics': severity_metrics,
            'category_metrics': category_metrics,
            'timing': {
                'total_time': round(total_time, 2),
                'avg_time_per_test': round(total_time / len(self.benchmark_data), 2)
            },
            'success_rate': successes / len(self.benchmark_data),
            'detailed_results': detailed_results
        }

    def run_all(self, model_names: List[str] = None) -> Dict[str, Any]:
        """
        Run evaluation for all models.

        Args:
            model_names: List of model names to evaluate (default: all)

        Returns:
            Dictionary with results for all models
        """
        if model_names is None:
            model_names = list(self.models.keys())

        results = {}

        for model_name in model_names:
            if model_name not in self.models:
                print(f"Warning: Model '{model_name}' not found. Skipping.")
                continue

            results[model_name] = self.evaluate_model(model_name)

        return results

    def print_comparison(self, results: Dict[str, Any]):
        """Print a comparison table of all models."""
        print("\n" + "=" * 80)
        print("COMPARISON TABLE")
        print("=" * 80)

        # Header
        print(f"{'Model':<25} {'Precision':<12} {'Recall':<12} {'F1 Score':<12} {'FPR':<12} {'Avg Time (s)'}")
        print("-" * 80)

        # Rows
        for model_name, result in results.items():
            metrics = result['metrics']
            timing = result['timing']

            print(f"{model_name:<25} "
                  f"{metrics['precision']:<12.4f} "
                  f"{metrics['recall']:<12.4f} "
                  f"{metrics['f1_score']:<12.4f} "
                  f"{metrics['false_positive_rate']:<12.4f} "
                  f"{timing['avg_time_per_test']:.2f}")

        print("=" * 80)

    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save results to JSON file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Run DiffAgent evaluation')
    parser.add_argument(
        '--models',
        nargs='+',
        choices=['diffagent', 'single_shot_gpt4o', 'single_shot_gpt4o_mini', 'rule_based'],
        help='Models to evaluate (default: all)'
    )
    parser.add_argument(
        '--output',
        default='eval/results/comparison.json',
        help='Output path for results (default: eval/results/comparison.json)'
    )
    parser.add_argument(
        '--benchmark',
        default='eval/data/benchmark.json',
        help='Path to benchmark dataset (default: eval/data/benchmark.json)'
    )

    args = parser.parse_args()

    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    # Run evaluation
    runner = BenchmarkRunner(benchmark_path=args.benchmark)
    results = runner.run_all(model_names=args.models)

    # Print comparison
    runner.print_comparison(results)

    # Save results
    runner.save_results(results, args.output)


if __name__ == '__main__':
    main()

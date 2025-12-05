"""
Example usage of the evaluation framework.

This script demonstrates how to use the evaluation framework programmatically
for custom evaluation scenarios.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import DiffAgent
from eval.baselines.single_shot_gpt import SingleShotGPT
from eval.baselines.rule_based import RuleBasedValidator
from eval.metrics import EvaluationMetrics


def example_1_single_diff():
    """Example 1: Validate a single diff with multiple models."""
    print("Example 1: Single Diff Validation")
    print("=" * 60)

    # Sample diff with a security issue
    diff = """diff --git a/settings.py b/settings.py
index abc1234..def5678 100644
--- a/settings.py
+++ b/settings.py
@@ -5,7 +5,7 @@ import os
 SECRET_KEY = os.getenv('SECRET_KEY')

 # Debug mode
-DEBUG = False
+DEBUG = True

 ALLOWED_HOSTS = ['example.com']
"""

    # Initialize models
    diffagent = DiffAgent()
    single_shot = SingleShotGPT(model='gpt-4o')
    rule_based = RuleBasedValidator()

    # Run each model
    print("\nDiffAgent:")
    result1 = diffagent.run(diff)
    print(f"  Has errors: {result1['has_errors']}")
    print(f"  Errors found: {len(result1['errors'])}")

    print("\nSingle-Shot GPT-4o:")
    result2 = single_shot.validate(diff)
    print(f"  Has errors: {result2['has_errors']}")
    print(f"  Errors found: {len(result2['errors'])}")

    print("\nRule-Based:")
    result3 = rule_based.validate(diff)
    print(f"  Has errors: {result3['has_errors']}")
    print(f"  Errors found: {len(result3['errors'])}")
    for error in result3['errors']:
        print(f"  - {error['option_name']}: {error['reason']}")


def example_2_metrics():
    """Example 2: Calculate metrics for model predictions."""
    print("\n\nExample 2: Metrics Calculation")
    print("=" * 60)

    # Ground truth
    ground_truth = {
        'has_errors': True,
        'errors': [
            {
                'file_path': 'settings.py',
                'option_name': 'DEBUG',
                'severity': 'critical',
                'reason': 'DEBUG mode enabled',
                'category': 'security'
            }
        ]
    }

    # Model prediction (correct)
    prediction_correct = {
        'has_errors': True,
        'errors': [
            {
                'file_path': 'settings.py',
                'option_name': 'DEBUG',
                'severity': 'critical',
                'reason': 'DEBUG is True in production',
                'category': 'security'
            }
        ]
    }

    # Model prediction (missed error)
    prediction_missed = {
        'has_errors': False,
        'errors': []
    }

    # Calculate metrics for correct prediction
    metrics1 = EvaluationMetrics()
    metrics1.add_prediction(ground_truth, prediction_correct)
    print("\nCorrect Prediction:")
    print(f"  Precision: {metrics1.precision():.4f}")
    print(f"  Recall: {metrics1.recall():.4f}")
    print(f"  F1 Score: {metrics1.f1_score():.4f}")

    # Calculate metrics for missed error
    metrics2 = EvaluationMetrics()
    metrics2.add_prediction(ground_truth, prediction_missed)
    print("\nMissed Error:")
    print(f"  Precision: {metrics2.precision():.4f}")
    print(f"  Recall: {metrics2.recall():.4f}")
    print(f"  F1 Score: {metrics2.f1_score():.4f}")


def example_3_batch_evaluation():
    """Example 3: Batch evaluation with multiple test cases."""
    print("\n\nExample 3: Batch Evaluation")
    print("=" * 60)

    # Multiple test cases
    test_cases = [
        {
            'diff': 'diff --git a/settings.py...\n-DEBUG = False\n+DEBUG = True',
            'ground_truth': {'has_errors': True, 'errors': [{'file_path': 'settings.py', 'option_name': 'DEBUG', 'severity': 'critical', 'category': 'security'}]}
        },
        {
            'diff': 'diff --git a/config.yaml...\n-level: INFO\n+level: DEBUG',
            'ground_truth': {'has_errors': False, 'errors': []}
        }
    ]

    # Evaluate rule-based model
    rule_based = RuleBasedValidator()
    metrics = EvaluationMetrics()

    print("\nEvaluating Rule-Based Model:")
    for i, test in enumerate(test_cases, 1):
        prediction = rule_based.validate(test['diff'])
        metrics.add_prediction(test['ground_truth'], prediction)
        print(f"  Test {i}: {'✓' if prediction['has_errors'] == test['ground_truth']['has_errors'] else '✗'}")

    print(f"\nOverall Metrics:")
    print(f"  Precision: {metrics.precision():.4f}")
    print(f"  Recall: {metrics.recall():.4f}")
    print(f"  F1 Score: {metrics.f1_score():.4f}")


def example_4_custom_benchmark():
    """Example 4: Run evaluation on custom benchmark data."""
    print("\n\nExample 4: Custom Benchmark")
    print("=" * 60)

    import json

    # Create a mini benchmark
    mini_benchmark = [
        {
            'id': 'custom_001',
            'name': 'DEBUG mode test',
            'diff': 'diff --git a/settings.py...\n-DEBUG = False\n+DEBUG = True',
            'ground_truth': {
                'has_errors': True,
                'errors': [{
                    'file_path': 'settings.py',
                    'option_name': 'DEBUG',
                    'severity': 'critical',
                    'category': 'security'
                }]
            }
        }
    ]

    # Save to temporary file
    temp_file = 'eval/data/custom_benchmark.json'
    with open(temp_file, 'w') as f:
        json.dump(mini_benchmark, f, indent=2)

    print(f"\nCreated custom benchmark at {temp_file}")
    print("You can now run:")
    print(f"  python eval/run_evaluation.py --benchmark {temp_file}")


if __name__ == '__main__':
    import os

    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("Warning: OPENAI_API_KEY not set. Examples using LLM models will fail.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'\n")

    # Run examples
    # example_1_single_diff()  # Uncomment to run (requires API key)
    example_2_metrics()
    example_3_batch_evaluation()
    example_4_custom_benchmark()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)

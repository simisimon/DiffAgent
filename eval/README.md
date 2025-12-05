# DiffAgent Evaluation Framework

This directory contains the evaluation framework for comparing DiffAgent against baseline approaches.

## Overview

The evaluation framework provides:
- **Benchmark Dataset**: 12 labeled test cases covering various misconfiguration scenarios
- **Baseline Models**: Rule-based and single-shot LLM approaches
- **Evaluation Metrics**: Precision, Recall, F1, False Positive Rate, and more
- **Automated Comparison**: Scripts to run all models and generate comparison reports

## Directory Structure

```
eval/
├── baselines/
│   ├── single_shot_gpt.py      # Single LLM call baseline (GPT-4o, GPT-4o-mini)
│   └── rule_based.py            # Pattern matching and heuristics baseline
├── data/
│   └── benchmark.json           # Labeled benchmark dataset
├── results/                     # Output directory for evaluation results
├── metrics.py                   # Evaluation metrics implementation
├── run_evaluation.py            # Main evaluation script
└── README.md                    # This file
```

## Benchmark Dataset

The benchmark dataset (`data/benchmark.json`) contains 12 test cases:

### Test Categories:
1. **Inconsistencies** (3 tests)
   - Port mismatches between files
   - Database adapter/port conflicts
   - Memory limit vs reservation conflicts

2. **Security Issues** (4 tests)
   - DEBUG mode enabled
   - Wildcard in ALLOWED_HOSTS
   - Hardcoded API keys
   - CORS misconfiguration

3. **Best Practices** (2 tests)
   - Missing environment variables
   - Unrealistic timeout values

4. **Valid Changes** (3 tests)
   - Legitimate configuration updates
   - Security improvements
   - Performance tuning

Each test case includes:
- `id`: Unique identifier
- `name`: Descriptive name
- `diff`: Git diff content
- `ground_truth`: Expected errors with file_path, option_name, severity, reason, category

## Baseline Models

### 1. DiffAgent (Main Approach)
Multi-agent LangGraph workflow with:
- Option extraction using GPT-4o-mini
- Change analysis
- Error detection using GPT-4o

### 2. Single-Shot GPT
Single LLM call without multi-agent workflow:
- **single_shot_gpt4o**: Uses GPT-4o
- **single_shot_gpt4o_mini**: Uses GPT-4o-mini

### 3. Rule-Based Validator
Pattern matching and heuristics:
- DEBUG mode detection
- Secret exposure patterns
- Port conflict detection
- Memory limit validation
- And more...

## Running Evaluations

### Setup

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY='your-api-key-here'
```

### Run All Models

```bash
python eval/run_evaluation.py
```

This will:
1. Run all 4 models on all 12 test cases
2. Calculate metrics for each model
3. Print comparison table
4. Save detailed results to `eval/results/comparison.json`

### Run Specific Models

```bash
# Run only DiffAgent and rule-based
python eval/run_evaluation.py --models diffagent rule_based

# Run only single-shot GPT-4o
python eval/run_evaluation.py --models single_shot_gpt4o
```

### Custom Output Path

```bash
python eval/run_evaluation.py --output my_results.json
```

### Custom Benchmark Dataset

```bash
python eval/run_evaluation.py --benchmark my_benchmark.json
```

## Evaluation Metrics

### Overall Metrics
- **Precision**: TP / (TP + FP) - What % of flagged errors are actual errors?
- **Recall**: TP / (TP + FN) - What % of actual errors are caught?
- **F1 Score**: Harmonic mean of precision and recall
- **Accuracy**: (TP + TN) / Total
- **False Positive Rate**: FP / (FP + TN)

### Breakdown Metrics
- **By Severity**: Metrics for critical, warning, and info level errors
- **By Category**: Metrics for security, inconsistency, invalid_value, best_practice

### Timing Metrics
- Total time
- Average time per test

## Output Format

Results are saved as JSON with the following structure:

```json
{
  "model_name": {
    "model": "diffagent",
    "metrics": {
      "precision": 0.8750,
      "recall": 0.8235,
      "f1_score": 0.8485,
      "accuracy": 0.8333,
      "false_positive_rate": 0.1250,
      "true_positives": 14,
      "false_positives": 2,
      "true_negatives": 10,
      "false_negatives": 3
    },
    "severity_metrics": { ... },
    "category_metrics": { ... },
    "timing": {
      "total_time": 45.23,
      "avg_time_per_test": 3.77
    },
    "detailed_results": [ ... ]
  }
}
```

## Adding New Test Cases

To add a new test case to the benchmark:

1. Edit `data/benchmark.json`
2. Add a new object with:
   ```json
   {
     "id": "test_013",
     "name": "Description of the test",
     "diff": "git diff content here...",
     "ground_truth": {
       "has_errors": true,
       "errors": [
         {
           "file_path": "path/to/file",
           "option_name": "OPTION_NAME",
           "severity": "critical",
           "reason": "Why this is an error",
           "category": "security"
         }
       ]
     }
   }
   ```

3. Run evaluation again

## Adding New Baselines

To add a new baseline model:

1. Create a new file in `baselines/` (e.g., `my_baseline.py`)
2. Implement a class with a `validate(diff_content: str)` method that returns:
   ```python
   {
     "has_errors": bool,
     "errors": [
       {
         "file_path": str,
         "option_name": str,
         "severity": str,  # "critical", "warning", or "info"
         "reason": str,
         "suggested_fix": str
       }
     ],
     "summary": str
   }
   ```

3. Add your model to `run_evaluation.py`:
   ```python
   from eval.baselines.my_baseline import MyBaseline

   self.models = {
       ...
       'my_baseline': MyBaseline()
   }
   ```

4. Run evaluation with your new baseline

## Example Output

```
Evaluating diffagent...
--------------------------------------------------
  Running test_001... ✓ (4.23s)
  Running test_002... ✓ (3.87s)
  ...

DiffAgent Evaluation Results
==================================================
Precision:            0.8750
Recall:               0.8235
F1 Score:             0.8485
Accuracy:             0.8333
False Positive Rate:  0.1250

Confusion Matrix:
  True Positives:     14
  False Positives:    2
  True Negatives:     10
  False Negatives:    3

================================================================================
COMPARISON TABLE
================================================================================
Model                     Precision    Recall       F1 Score     FPR          Avg Time (s)
------------------------------------------------------------------------------------
diffagent                 0.8750       0.8235       0.8485       0.1250       3.77
single_shot_gpt4o         0.8125       0.7647       0.7879       0.1875       2.15
single_shot_gpt4o_mini    0.7500       0.7059       0.7273       0.2500       1.43
rule_based                0.9167       0.4706       0.6207       0.0833       0.08
================================================================================
```

## Interpreting Results

### High Precision, Low Recall
- Model is conservative, only flags high-confidence errors
- Few false positives but misses some errors
- Example: Rule-based approaches

### Low Precision, High Recall
- Model is aggressive, flags many potential errors
- Catches most errors but has many false positives
- May cause alert fatigue

### High F1 Score
- Good balance between precision and recall
- Ideal for production use

### Low False Positive Rate
- Few unnecessary alerts
- Better user experience
- Important for CI/CD integration

## Cost Analysis

To estimate API costs:
1. Check `timing.total_time` in results
2. Count tokens in requests (can be added to baselines)
3. Calculate cost based on OpenAI pricing

Approximate costs (as of 2024):
- GPT-4o: $5/1M input tokens, $15/1M output tokens
- GPT-4o-mini: $0.15/1M input tokens, $0.60/1M output tokens

## Next Steps

For research paper evaluation:
1. **Expand benchmark**: Add 50-100 more test cases from real repositories
2. **Add baselines**: Compare against Checkov, yamllint, hadolint
3. **Run ablation studies**: Test DiffAgent without certain components
4. **User study**: Get feedback from developers on error messages
5. **Real-world deployment**: Deploy on 5-10 repositories and track results

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"
Set your API key:
```bash
export OPENAI_API_KEY='sk-...'
```

### Rate limit errors
Add delays between API calls or use a higher tier API key.

### Out of memory
Reduce batch size or run models one at a time.

### Incorrect metrics
Verify ground truth labels in `data/benchmark.json` are correct.

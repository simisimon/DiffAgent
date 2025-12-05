# Evaluation Quick Start Guide

This is a quick reference for running evaluations. For full documentation, see [README.md](README.md).

## 1. Setup (First Time Only)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY='sk-...'

# Or add to .env file in project root
echo "OPENAI_API_KEY=sk-..." >> .env
```

## 2. Run Full Evaluation

```bash
# Run all models on all test cases
python eval/run_evaluation.py
```

This will:
- Test 4 models (DiffAgent, Single-Shot GPT-4o, Single-Shot GPT-4o-mini, Rule-based)
- Run 12 benchmark tests
- Print comparison table
- Save results to `eval/results/comparison.json`

## 3. Run Specific Models

```bash
# Only DiffAgent
python eval/run_evaluation.py --models diffagent

# DiffAgent vs Rule-based
python eval/run_evaluation.py --models diffagent rule_based

# All GPT models
python eval/run_evaluation.py --models diffagent single_shot_gpt4o single_shot_gpt4o_mini
```

## 4. Generate Tables for Paper

```bash
# Run evaluation first
python eval/run_evaluation.py

# Generate Markdown tables
python eval/visualize_results.py eval/results/comparison.json --markdown

# Generate LaTeX table
python eval/visualize_results.py eval/results/comparison.json --latex

# Generate all visualizations
python eval/visualize_results.py eval/results/comparison.json --all
```

## 5. Add Your Own Test Cases

Edit `eval/data/benchmark.json`:

```json
{
  "id": "test_013",
  "name": "Your test description",
  "diff": "diff --git a/file.py...",
  "ground_truth": {
    "has_errors": true,
    "errors": [
      {
        "file_path": "file.py",
        "option_name": "SETTING",
        "severity": "critical",
        "reason": "Why this is wrong",
        "category": "security"
      }
    ]
  }
}
```

Then run evaluation again.

## 6. Test a Single Diff

```python
from eval.baselines.rule_based import RuleBasedValidator

validator = RuleBasedValidator()
result = validator.validate(your_diff_content)
print(result)
```

## Expected Output

```
Evaluating diffagent...
--------------------------------------------------
  Running test_001... ✓ (4.23s)
  Running test_002... ✓ (3.87s)
  ...

================================================================================
COMPARISON TABLE
================================================================================
Model                     Precision    Recall       F1 Score     FPR
------------------------------------------------------------------------------------
diffagent                 0.8750       0.8235       0.8485       0.1250
single_shot_gpt4o         0.8125       0.7647       0.7879       0.1875
single_shot_gpt4o_mini    0.7500       0.7059       0.7273       0.2500
rule_based                0.9167       0.4706       0.6207       0.0833
================================================================================
```

## Metric Interpretation

- **Precision**: Of all errors flagged, what % are real errors?
  - Higher = fewer false alarms

- **Recall**: Of all real errors, what % did we catch?
  - Higher = fewer missed errors

- **F1 Score**: Balance between precision and recall
  - Higher = better overall performance

- **FPR** (False Positive Rate): What % of valid configs are flagged?
  - Lower = better (less noise)

## Troubleshooting

**"OPENAI_API_KEY not set"**
```bash
export OPENAI_API_KEY='your-key-here'
```

**Rate limit errors**
- Wait a few minutes
- Upgrade to higher tier API key
- Add delays in code

**Import errors**
```bash
pip install -r requirements.txt
```

**No results directory**
- It's created automatically
- Check permissions if it fails

## Next Steps

1. ✅ Run initial evaluation
2. ✅ Review results
3. ✅ Add more test cases
4. ✅ Generate tables for paper
5. Compare with other tools (checkov, yamllint)
6. Run ablation studies
7. Deploy to real repositories

## File Structure

```
eval/
├── QUICKSTART.md           ← You are here
├── README.md               ← Full documentation
├── run_evaluation.py       ← Main evaluation script
├── visualize_results.py    ← Generate tables/charts
├── example_usage.py        ← Code examples
├── metrics.py              ← Metrics calculation
├── baselines/
│   ├── single_shot_gpt.py
│   └── rule_based.py
├── data/
│   └── benchmark.json      ← Test cases (edit here)
└── results/
    └── comparison.json     ← Results (generated)
```

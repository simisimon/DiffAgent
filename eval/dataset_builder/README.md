# GitHub Dataset Builder

Build high-quality benchmark datasets from real-world GitHub pull requests.

## Overview

This toolkit automates the process of building benchmark datasets for configuration validation by:

1. **Collecting** PRs from GitHub using strategic queries
2. **Labeling** PRs automatically using heuristics
3. **Filtering** low-quality data
4. **Manual Review** for quality assurance
5. **Converting** to benchmark format for evaluation

## Quick Start

### 1. Setup

```bash
# Get a GitHub Personal Access Token
# Visit: https://github.com/settings/tokens
# Scopes needed: public_repo (for public repos)

export GITHUB_TOKEN='ghp_your_token_here'

# Install dependencies (if needed)
pip install requests
```

### 2. Collect Data from GitHub

```bash
# Collect 50 PRs using 3 strategies
python eval/dataset_builder/github_collector.py \
  --strategies reverted fix bug \
  --max-per-strategy 50 \
  --output eval/dataset_builder/collected_data.json
```

### 3. Auto-Label the Data

```bash
# Apply automatic labeling heuristics
python eval/dataset_builder/auto_labeler.py \
  --input eval/dataset_builder/collected_data.json \
  --output eval/dataset_builder/labeled_data.json \
  --min-confidence 0.6
```

### 4. Filter and Clean

```bash
# Filter out low-quality data
python eval/dataset_builder/data_filter.py filter \
  --input eval/dataset_builder/labeled_data.json \
  --output eval/dataset_builder/filtered_data.json \
  --min-confidence 0.7

# Balance the dataset (50% errors, 50% valid)
python eval/dataset_builder/data_filter.py balance \
  --input eval/dataset_builder/filtered_data.json \
  --output eval/dataset_builder/balanced_data.json \
  --target-ratio 0.5
```

### 5. Manual Review (Optional but Recommended)

```bash
# Review items flagged for manual review
python eval/dataset_builder/manual_review.py review \
  --input eval/dataset_builder/balanced_data.json \
  --output eval/dataset_builder/reviewed_data.json \
  --filter needs_review
```

### 6. Convert to Benchmark Format

```bash
# Convert to evaluation benchmark format
python eval/dataset_builder/data_filter.py convert \
  --input eval/dataset_builder/reviewed_data.json \
  --output eval/data/github_benchmark.json \
  --max-items 100
```

### 7. Run Evaluation

```bash
# Evaluate models on your new benchmark
python eval/run_evaluation.py \
  --benchmark eval/data/github_benchmark.json
```

## Collection Strategies

The collector supports multiple strategies for finding relevant PRs:

### Strategy: `reverted`
**Query:** `revert config`

Finds PRs that reverted configuration changes. These are strong indicators of errors.

**Why it works:** If a config change was reverted, it likely caused problems.

### Strategy: `fix`
**Query:** `fix config OR fix configuration`

Finds PRs that fix configuration issues.

**Why it works:** These PRs often reference the original problematic change.

### Strategy: `bug`
**Query:** `bug config OR config bug`

Finds bug-related configuration changes.

**Why it works:** Explicitly labeled as bugs by developers.

### Strategy: `security`
**Query:** `security config OR config vulnerability`

Finds security-related configuration issues.

**Why it works:** Security issues are well-documented and critical.

### Strategy: `hotfix`
**Query:** `hotfix config OR config hotfix`

Finds urgent fixes to configuration.

**Why it works:** Hotfixes indicate production issues.

### Strategy: `rollback`
**Query:** `rollback config`

Finds configuration rollbacks.

**Why it works:** Similar to reverts, indicates problems.

### Strategy: `incorrect`
**Query:** `incorrect config OR wrong config`

Finds PRs explicitly mentioning incorrect configs.

**Why it works:** Developers explicitly state the config was wrong.

## Auto-Labeling Heuristics

The auto-labeler uses multiple signals to determine ground truth:

### Signals for "Has Errors"
- **Title contains "revert"** (+0.35 confidence)
- **Labeled as bug/hotfix** (+0.25 confidence)
- **Changes requested in review** (+0.15 confidence)
- **Title contains "fix"** (+0.20 confidence)
- **Negative comments detected** (+0.15 confidence)
- **Collection strategy** (+0.10 confidence)

### Signals for "No Errors"
- **Approved and merged** (-0.20 confidence)
- **No error keywords and merged** (-0.10 confidence)

### Category Detection
- **Security:** Keywords like "security", "vulnerability", "exposed"
- **Inconsistency:** Keywords like "mismatch", "inconsistent", "conflict"
- **Invalid Value:** Keywords like "invalid", "out of range"
- **Best Practice:** Default category

### Severity Detection
- **Critical:** Security issues, reverts, hotfixes
- **Warning:** Changes requested, other issues
- **Info:** Minor issues

## Data Quality

### Automatic Filtering

The filter removes:
- **No config files:** PRs without configuration file changes
- **Too small:** Diffs < 50 characters (likely trivial)
- **Too large:** Diffs > 50,000 characters (hard to process)
- **Low confidence:** Below specified threshold

### Manual Review Criteria

Review is recommended for:
- **Low confidence** (<0.8): Automatic label uncertain
- **Critical severity:** High-impact errors
- **Security category:** Important to verify
- **Edge cases:** Unusual patterns

## Output Formats

### Collected Data Format
```json
{
  "id": "owner_repo_123",
  "repo": "owner/repo",
  "pr_number": 123,
  "pr_url": "https://github.com/...",
  "title": "Fix config bug",
  "diff": "diff --git ...",
  "files": [...],
  "comments": [...],
  "reviews": [...],
  "collection_strategy": "fix"
}
```

### Labeled Data Format
```json
{
  "id": "owner_repo_123",
  "...": "... (same as collected)",
  "ground_truth": {
    "has_errors": true,
    "confidence": 0.85,
    "category": "security",
    "severity": "critical",
    "labeling_reasons": ["Title contains 'fix'", ...]
  },
  "requires_manual_review": false
}
```

### Benchmark Format
```json
{
  "id": "owner_repo_123",
  "name": "Fix config bug",
  "diff": "diff --git ...",
  "ground_truth": {
    "has_errors": true,
    "errors": [
      {
        "file_path": "config.yaml",
        "option_name": "UNKNOWN",
        "severity": "critical",
        "reason": "Labeled via automated heuristics (confidence: 0.85)",
        "category": "security"
      }
    ]
  }
}
```

## Pipeline Examples

### Example 1: Quick 50-item Dataset

```bash
# Collect
python eval/dataset_builder/github_collector.py \
  --strategies reverted --max-per-strategy 50

# Label
python eval/dataset_builder/auto_labeler.py \
  --min-confidence 0.7

# Convert
python eval/dataset_builder/data_filter.py convert \
  --max-items 50
```

### Example 2: High-Quality 200-item Dataset

```bash
# Collect from multiple strategies
python eval/dataset_builder/github_collector.py \
  --strategies reverted fix bug security --max-per-strategy 100

# Label with high threshold
python eval/dataset_builder/auto_labeler.py \
  --min-confidence 0.8

# Filter
python eval/dataset_builder/data_filter.py filter \
  --min-confidence 0.85

# Balance
python eval/dataset_builder/data_filter.py balance \
  --target-ratio 0.5

# Manual review
python eval/dataset_builder/manual_review.py review \
  --filter needs_review

# Convert
python eval/dataset_builder/data_filter.py convert \
  --max-items 200
```

### Example 3: Security-Focused Dataset

```bash
# Collect only security-related PRs
python eval/dataset_builder/github_collector.py \
  --strategies security --max-per-strategy 100

# Label
python eval/dataset_builder/auto_labeler.py

# Filter for security category only
python eval/dataset_builder/data_filter.py filter \
  --categories security

# Manual review (important for security)
python eval/dataset_builder/manual_review.py review \
  --filter all
```

## Best Practices

### For Research Papers

1. **Document your methodology:**
   - Which strategies you used
   - Confidence thresholds
   - Manual review process

2. **Report statistics:**
   - Total PRs collected
   - Filtering criteria
   - Final dataset size
   - Error/valid ratio
   - Confidence distribution

3. **Ensure quality:**
   - Manual review of at least 10-20% of data
   - Especially review high-impact items (security, critical)
   - Validate ground truth with domain experts

4. **Maintain reproducibility:**
   - Save intermediate files
   - Document exact commands used
   - Note GitHub API version and date of collection

### Improving Label Quality

1. **Use multiple strategies:** Diverse collection improves coverage
2. **Set reasonable confidence thresholds:** 0.7-0.8 is a good balance
3. **Balance the dataset:** Avoid skew toward errors or valid
4. **Manual review low-confidence items:** Most improvement comes from reviewing uncertain cases
5. **Iterate:** Collect → Label → Review → Refine heuristics → Repeat

### Ethical Considerations

1. **Respect GitHub's Terms of Service**
2. **Use personal access tokens (not scraping)**
3. **Respect rate limits** (sleep between requests)
4. **Don't publish sensitive information** (secrets, passwords)
5. **Anonymize if needed** (though public PRs are already public)
6. **Give credit** (cite repositories if using in paper)

## Troubleshooting

### Rate Limit Errors

**Problem:** "Rate limit exceeded"

**Solution:**
- Use a GitHub token (increases limit from 60 to 5000 req/hour)
- Add delays between requests
- Reduce `--max-per-strategy`

### No PRs Found

**Problem:** Collector returns 0 PRs

**Solution:**
- Check your query is valid
- Try different strategies
- Check GitHub is accessible
- Verify your token has correct permissions

### Low Confidence Labels

**Problem:** All labels have confidence < 0.6

**Solution:**
- Strategies might not be selective enough
- Try more specific queries
- Increase manual review
- Adjust confidence calculation in `auto_labeler.py`

### Imbalanced Dataset

**Problem:** 90% errors or 90% valid

**Solution:**
- Use `balance` command
- Collect from both error and valid strategies
- Manually curate a validation set

## Advanced Usage

### Custom Strategies

Edit `github_collector.py` to add custom strategies:

```python
strategy_queries = {
    'custom': 'your custom query here',
    ...
}
```

### Custom Labeling Logic

Edit `auto_labeler.py` to adjust confidence calculation:

```python
def _determine_errors(self, signals):
    # Add your custom logic
    if custom_condition:
        confidence += 0.3
    ...
```

### Batch Processing

Process multiple datasets:

```bash
for strategy in reverted fix bug security; do
  python eval/dataset_builder/github_collector.py \
    --strategies $strategy \
    --output data_${strategy}.json
done
```

## File Structure

```
eval/dataset_builder/
├── README.md                    # This file
├── github_collector.py          # Collect PRs from GitHub
├── auto_labeler.py              # Automatic labeling
├── data_filter.py               # Filtering and validation
├── manual_review.py             # Manual review interface
├── collected_data.json          # Raw collected data
├── labeled_data.json            # Auto-labeled data
├── filtered_data.json           # Filtered data
├── balanced_data.json           # Balanced dataset
└── reviewed_data.json           # Manually reviewed data
```

## Next Steps

After building your dataset:

1. **Evaluate models** on it using `eval/run_evaluation.py`
2. **Compare** with hand-crafted benchmark
3. **Analyze** where models fail
4. **Iterate** on collection and labeling strategies
5. **Expand** dataset to 200-500 items for publication
6. **Share** (if appropriate) with the community

## Citation

If you use this toolkit for research, please cite your methodology:

```
We constructed a benchmark dataset of N configuration changes from GitHub,
using automated search strategies (revert, fix, bug, security) and applying
heuristic-based labeling with manual review of M items. Final dataset contains
X items with Y% error rate and average confidence of Z.
```

## Support

For issues or questions:
- Check GitHub API status: https://www.githubstatus.com/
- Review GitHub API docs: https://docs.github.com/en/rest
- Check rate limits: https://api.github.com/rate_limit

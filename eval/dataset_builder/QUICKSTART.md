# Dataset Builder - Quick Start

Build a benchmark dataset from GitHub in 5 minutes.

## Prerequisites

1. **GitHub Token** (Required for good rate limits)
   ```bash
   # Get token at: https://github.com/settings/tokens
   # Required scope: public_repo

   export GITHUB_TOKEN='ghp_your_token_here'
   ```

2. **Install dependencies**
   ```bash
   pip install requests
   ```

## One-Command Build

Build a 100-item dataset with one command:

```bash
python eval/dataset_builder/build_dataset.py --size 100
```

This will:
1. ✅ Collect 300 PRs from GitHub (3x oversampling)
2. ✅ Auto-label using heuristics
3. ✅ Filter low-quality data
4. ✅ Balance errors vs. valid (50/50)
5. ✅ Convert to benchmark format
6. ✅ Validate the dataset

**Output:** `eval/data/github_benchmark.json`

## Custom Builds

### Large Dataset (200 items)
```bash
python eval/dataset_builder/build_dataset.py --size 200
```

### Security-Focused Dataset
```bash
python eval/dataset_builder/build_dataset.py \
  --size 50 \
  --strategies security \
  --ratio 0.8
```

### High-Quality Dataset (manual review)
```bash
# Build with high confidence threshold
python eval/dataset_builder/build_dataset.py \
  --size 100 \
  --min-confidence 0.8

# Then manually review low-confidence items
python eval/dataset_builder/manual_review.py review \
  --input eval/dataset_builder/balanced_data.json \
  --filter needs_review
```

### Multiple Strategies
```bash
python eval/dataset_builder/build_dataset.py \
  --size 150 \
  --strategies reverted fix bug security hotfix
```

## Step-by-Step (Manual Control)

If you want fine-grained control:

### Step 1: Collect
```bash
python eval/dataset_builder/github_collector.py \
  --strategies reverted fix bug \
  --max-per-strategy 100
```

### Step 2: Label
```bash
python eval/dataset_builder/auto_labeler.py \
  --min-confidence 0.7
```

### Step 3: Filter
```bash
python eval/dataset_builder/data_filter.py filter \
  --min-confidence 0.7
```

### Step 4: Balance
```bash
python eval/dataset_builder/data_filter.py balance \
  --target-ratio 0.5
```

### Step 5: Review (Optional)
```bash
python eval/dataset_builder/manual_review.py review \
  --filter needs_review
```

### Step 6: Convert
```bash
python eval/dataset_builder/data_filter.py convert \
  --max-items 100
```

## Evaluate Your Dataset

Once built, test it:

```bash
# Run evaluation
python eval/run_evaluation.py \
  --benchmark eval/data/github_benchmark.json

# Generate tables
python eval/visualize_results.py \
  eval/results/comparison.json --all
```

## Collection Strategies Explained

| Strategy | Query | Best For |
|----------|-------|----------|
| `reverted` | "revert config" | High-confidence errors |
| `fix` | "fix config" | Common config bugs |
| `bug` | "bug config" | Labeled issues |
| `security` | "security config" | Security vulnerabilities |
| `hotfix` | "hotfix config" | Production incidents |
| `rollback` | "rollback config" | Deployment issues |
| `incorrect` | "incorrect config" | Explicit mistakes |

**Recommendation:** Start with `reverted fix bug` for balanced coverage.

## Expected Results

For a 100-item dataset:

```
Collected: ~300 PRs (3x oversampling)
Labeled: ~300 PRs
Filtered: ~150 PRs (removed low quality)
Balanced: ~100 PRs (50/50 split)
Final: 100 items
```

**Time:** 10-20 minutes depending on rate limits

**Quality:**
- High confidence: 60-70%
- Needs review: 30-40%
- Average confidence: 0.75-0.85

## Common Issues

### Rate Limit
**Error:** "Rate limit exceeded"

**Fix:**
```bash
export GITHUB_TOKEN='your-token-here'
```

### No PRs Found
**Error:** "Collected 0 PRs"

**Fix:**
- Check internet connection
- Try different strategies
- Verify token has `public_repo` scope

### Low Confidence
**Problem:** All items have confidence < 0.6

**Fix:**
- Use more selective strategies (`reverted`, `security`)
- Increase `--min-confidence` threshold
- Plan for manual review

## Pro Tips

1. **Start small:** Build 50 items first to test the pipeline
2. **Use multiple strategies:** Diverse data improves coverage
3. **Review critical items:** Always review security/critical severity
4. **Balance your dataset:** 50/50 errors vs. valid is ideal
5. **Document your process:** Save commands and parameters for reproducibility

## Next Steps

After building your dataset:

1. **Evaluate models:**
   ```bash
   python eval/run_evaluation.py --benchmark eval/data/github_benchmark.json
   ```

2. **Analyze results:**
   ```bash
   python eval/visualize_results.py eval/results/comparison.json --all
   ```

3. **Refine and expand:**
   - Add more items
   - Adjust confidence thresholds
   - Manual review low-confidence items
   - Test on different model variants

4. **Use in paper:**
   - Report collection methodology
   - Show dataset statistics
   - Compare with hand-crafted benchmark
   - Discuss limitations

## Full Documentation

See [README.md](README.md) for complete documentation.

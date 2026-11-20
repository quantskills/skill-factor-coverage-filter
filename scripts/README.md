# Scripts

Install dependencies with `python -m pip install -r requirements.txt`. Run `coverage_filter.py` from the repository root:

```bash
python scripts/coverage_filter.py \
  --manifest /path/to/manifest.json \
  --output-dir /path/to/output \
  --start-date 2023-01-01 \
  --end-date 2023-12-31
```

The command writes `selected_factors.json`, `ranked_factor_set.json`, `factor_audit.csv`, `excluded_factors.csv` and `audit_receipt.json`. Outputs belong outside the repository or under an ignored output directory.

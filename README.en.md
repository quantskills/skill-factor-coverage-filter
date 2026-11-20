# Factor Coverage Filter

[Simplified Chinese](README.md) | English

`skill-factor-coverage-filter` is an independent QuantSkills Community Project. Audit a factor panel and select factors that satisfy declared coverage, finite-value, and key-integrity thresholds.

## Scope

- Use when an agent needs a reproducible data-quality gate before factor selection or modeling.
- Do not use labels, validation performance, or OOS outcomes to decide which factors pass.
- Valid and OOS or holdout data must follow the freeze and leakage rules in `SKILL.md`.

## Research disclosure

- Data source: use only public data, user-provided local data, or material the user has the right to use, and record provenance.
- Assumptions: state time semantics, universe construction, factor direction, missing-value handling, and label availability.
- Parameters: persist thresholds, seeds, split boundaries, preprocessing, and method settings.
- Limitations: disclose sample dependence, instability, approximations, missingness, and untested regimes.
- Risk boundary: all artifacts are for quantitative research and education only.

## Current status

- Catalog: `02.factor-selection`
- Workflow: `data-quality`
- Validation: `runnable`
- License: `GPL-3.0-only`

The repository contains an execution-tested Python CLI, independent dependencies, a synthetic fixture generator, and pytest smoke tests.

## Runnable implementation

```bash
python -m pip install -r requirements.txt
python scripts/coverage_filter.py \
  --manifest /path/to/manifest.json \
  --output-dir /path/to/output \
  --start-date 2023-01-01 \
  --end-date 2023-12-31
python -m pytest -q
```

The primary structured output is `ranked_factor_set.json` using the `ranked-factor-set` 1.0.0 profile. Additional artifacts provide method-specific audit evidence.

## Entrypoints

- `SKILL.md`: canonical Skill instructions and QuantSkills frontmatter.
- `references/protocol.md`: temporal boundary, input audit, and output acceptance contract.
- `references/source_boundary.md`: data, licensing, privacy, and research-risk boundary.

## Disclaimer

This project is for quantitative research and education only. It is not investment advice, a return guarantee, or production approval.

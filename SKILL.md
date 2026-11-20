---
name: skill-factor-coverage-filter
description: Audit a factor panel and select factors that satisfy declared coverage, finite-value, and key-integrity
  thresholds. Use when an agent needs a reproducible data-quality gate before factor selection or modeling. Do not
  use labels, validation performance, or OOS outcomes to decide which factors pass.
quantSkills:
  schema_version: 2.0.0
  organization: quantskills
  organization_url: https://github.com/quantskills
  repository: skill-factor-coverage-filter
  repository_url: https://github.com/quantskills/skill-factor-coverage-filter
  project_type: skill
  license: GPL-3.0-only
  maintainer: X-Tech-group
  collection: factor-research
  catalog:
    category: '02'
    subcategory: 02.factor-selection
  workflow:
    primary_stage: data-quality
    workflow_stages:
    - data-quality
    - factor-screening
  tags:
  - factor-selection
  - data-quality
  - coverage
  - anti-leakage
  requires: []
  summary_zh: 在因子研究前检查数据覆盖率、有限值、日期覆盖和横截面完整性的因子筛选技能。
  summary_en: Factor coverage and data-integrity screening before downstream factor research.
  status: active
  validation_level: runnable
  maintainer_type: community
  platforms:
  - cursor
  - claude-code
  - codex
  - hermes
  - openclaw
  interface:
    mode: hybrid
    envelope:
      name: quantskills-envelope
      version: 1.0.0
    inputs: []
    outputs:
    - profile: ranked-factor-set
      version: 1.0.0
    adapters: []
---
# Factor Coverage Filter

Audit a factor panel and select factors that satisfy declared coverage, finite-value, and key-integrity thresholds.

## Use This Skill When

- Use it when an agent needs a reproducible data-quality gate before factor selection or modeling.
- Do not use labels, validation performance, or OOS outcomes to decide which factors pass.
- Treat all outputs as quantitative research artifacts, not investment advice or production approval.

## Inputs

- A schema-compatible factor panel with stable factor identifiers.
- Explicit audit range, universe rules, coverage thresholds, finite-value policy, and output directory.

Read `references/protocol.md` before preparing inputs or interpreting outputs.

## Method Decisions

- Compute date, instrument, finite-value, and missing-value coverage on the declared research range.
- Apply frozen thresholds and record one explicit outcome for every candidate factor.

## Workflow

1. Validate the factor panel, candidate manifest, primary keys, date ordering, and universe identifiers.
2. Freeze the audit range, thresholds, denominator rules, and failure policy before computation.
3. Compute date, instrument, finite-value, and missing-value coverage without labels or performance metrics.
4. Assign every candidate an explicit selected, excluded, or failed outcome and reason.
5. Re-audit the selected set and verify counts against the original manifest.
6. Freeze the ranked factor set and audit receipts before downstream modeling or OOS access.

## Output Contract

- Emit a QuantSkills `quantskills-envelope` with profile `ranked-factor-set` version `1.0.0`.
- Preserve the resolved thresholds, denominators, candidate outcomes, date boundaries, and input/output SHA256 receipts.
- Never silently drop missing files, duplicate keys, invalid factor identifiers, or non-finite values.

## Research Invariants

- Compute coverage from declared panel keys and denominators, not from labels or performance metrics.
- Freeze thresholds and missing-value policy before candidate outcomes are calculated.
- Valid and OOS outcomes must not influence the data-quality gate.
- Record one selected, excluded, or failed outcome for every candidate.
- Record data provenance, assumptions, limitations, and all deviations from the declared protocol.

## Research Disclosure

- Data source: use only public data, user-provided local data, or material the user has the right to use; record provenance.
- Assumptions: document time semantics, universe construction, factor direction, missing-value handling, and label availability.
- Parameters: persist every threshold, seed, split boundary, preprocessing option, and method setting.
- Limitations: disclose sample dependence, instability, approximation, missingness, and any untested operating regime.
- Risk boundary: outputs are research evidence only and are not investment advice, promised returns, or production approval.

## Runnable Implementation

Install dependencies with `python -m pip install -r requirements.txt` and run:

```bash
python scripts/coverage_filter.py \
  --manifest /path/to/manifest.json \
  --output-dir /path/to/output \
  --start-date 2023-01-01 \
  --end-date 2023-12-31
```

The CLI writes `ranked_factor_set.json` using the registered `ranked-factor-set` 1.0.0 profile together with method-specific audit artifacts. Generate synthetic smoke inputs from `examples/` and run `python -m pytest -q` before release.

## Optional qsh-form

```json qsh-form
{"version":1,"task":{"placeholder":"Describe the Factor Coverage Filter research task and attach the required local inputs","required":true},"fields":[],"prompt_template":"Handle this task: {{task}}. Attachments: {{#attachments}}"}
```

## References

- `references/protocol.md`: input, temporal, output, and validation contract.
- `references/source_boundary.md`: source, licensing, privacy, and research boundaries.

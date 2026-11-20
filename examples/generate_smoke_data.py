#!/usr/bin/env python3
"""Generate a deterministic coverage-filter smoke fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dates = pd.date_range("2023-01-02", periods=8, freq="D")
    symbols = ["AAA", "BBB", "CCC"]
    good, sparse = [], []
    for day, date in enumerate(dates):
        for offset, symbol in enumerate(symbols):
            good.append({"date": date.date().isoformat(), "ticker": symbol, "value": day + offset / 10})
            sparse.append(
                {
                    "date": date.date().isoformat(),
                    "ticker": symbol,
                    "value": np.nan if day < 4 else day + offset / 10,
                }
            )
    pd.DataFrame(good).to_csv(args.output_dir / "good.csv", index=False)
    pd.DataFrame(sparse).to_csv(args.output_dir / "sparse.csv", index=False)
    manifest = {
        "factors": [
            {"name": "good_factor", "path": "good.csv", "factor_column": "value"},
            {"name": "sparse_factor", "path": "sparse.csv", "factor_column": "value"},
        ]
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(args.output_dir / "manifest.json")


if __name__ == "__main__":
    main()

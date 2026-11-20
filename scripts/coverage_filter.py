#!/usr/bin/env python3
"""Audit and filter a factor panel by train-period coverage and finite values.

The script deliberately treats the manifest as an input contract.  It never
silently removes a factor: every rejected factor is written to
``excluded_factors.csv`` with reproducible reasons.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from ranked_factor_output import build_ranked_factor_set


DATE_NAMES = ("date", "trade_date", "datetime")
SYMBOL_NAMES = ("ticker", "symbol", "stock_code", "security")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
    if path.is_dir():
        files = sorted(item for item in path.rglob("*") if item.is_file())
        if not files:
            raise ValueError(f"Cannot hash empty directory: {path}")
        for item in files:
            digest.update(item.relative_to(path).as_posix().encode("utf-8"))
            with item.open("rb") as handle:
                while chunk := handle.read(8 * 1024 * 1024):
                    digest.update(chunk)
        return digest.hexdigest()
    raise FileNotFoundError(path)


def read_table(path: Path) -> pd.DataFrame:
    if path.is_dir():
        return pd.read_parquet(path)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv" or path.name.lower().endswith(".csv.gz"):
        return pd.read_csv(path)
    raise ValueError(f"Unsupported factor file: {path}")


def first_column(columns: Iterable[str], names: Iterable[str]) -> str | None:
    lookup = {str(column).lower(): str(column) for column in columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def load_manifest(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise ValueError("Every manifest list item must be an object")
        return payload, payload
    if not isinstance(payload, dict):
        raise ValueError("Manifest must be a JSON list or object")
    records = payload.get("factors", payload.get("candidates", payload.get("items")))
    if records is None and all(isinstance(value, str) for value in payload.values()):
        records = [{"name": key, "path": value} for key, value in payload.items()]
    if not isinstance(records, list):
        raise ValueError("Manifest must contain a factors/candidates/items list")
    if not all(isinstance(item, dict) for item in records):
        raise ValueError("Every factor record must be an object")
    return payload, records


def record_path(record: dict[str, Any], manifest_dir: Path) -> Path:
    value = record.get("path", record.get("file", record.get("data_path")))
    if not value:
        raise ValueError(f"Factor record has no path: {record}")
    path = Path(str(value))
    return path if path.is_absolute() else (manifest_dir / path).resolve()


def factor_frames(record: dict[str, Any], path: Path) -> list[tuple[str, pd.DataFrame, str]]:
    frame = read_table(path)
    date_col = first_column(frame.columns, DATE_NAMES)
    if date_col is None:
        raise ValueError(f"{path} has no date column")
    symbol_col = first_column(frame.columns, SYMBOL_NAMES)
    value_col = record.get("factor_column", record.get("value_column"))
    if value_col:
        if value_col not in frame.columns:
            raise ValueError(f"{path} has no declared factor column {value_col}")
        names = [str(record.get("name", value_col))]
        return [(names[0], frame, str(value_col))]
    numeric = [
        str(column)
        for column in frame.columns
        if column not in {date_col, symbol_col}
        and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not numeric:
        raise ValueError(f"{path} has no numeric factor column")
    if len(numeric) == 1:
        return [(str(record.get("name", numeric[0])), frame, numeric[0])]
    # A wide panel is expanded into one auditable factor per numeric column.
    return [(column, frame, column) for column in numeric]


def audit_factor(
    name: str,
    frame: pd.DataFrame,
    value_col: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    expected_dates: set[pd.Timestamp],
    expected_symbols: set[str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    date_col = first_column(frame.columns, DATE_NAMES)
    symbol_col = first_column(frame.columns, SYMBOL_NAMES)
    work = frame.copy()
    parsed_dates = pd.to_datetime(work[date_col], errors="coerce").dt.normalize()
    invalid_date_rows = int((work[date_col].notna() & parsed_dates.isna()).sum())
    work["__date"] = parsed_dates
    work = work.loc[work["__date"].between(start, end)].copy()
    if symbol_col is None:
        work["__symbol"] = "__single_series__"
    else:
        work["__symbol"] = work[symbol_col].astype(str)
    values = pd.to_numeric(work[value_col], errors="coerce")
    key_duplicates = int(work.duplicated(["__date", "__symbol"]).sum())
    finite = np.isfinite(values.to_numpy(dtype=float, na_value=np.nan))
    observed_dates = {pd.Timestamp(value).normalize() for value in work["__date"].dropna().unique()}
    observed_symbols = set(work["__symbol"].dropna().astype(str))
    date_coverage = len(observed_dates & expected_dates) / max(len(expected_dates), 1)
    symbol_coverage = len(observed_symbols & expected_symbols) / max(len(expected_symbols), 1)
    finite_ratio = float(finite.mean()) if len(finite) else 0.0
    counts = work.groupby("__date", dropna=True)["__symbol"].nunique()
    median_cross_section = float(counts.median()) if len(counts) else 0.0
    reasons: list[str] = []
    if invalid_date_rows:
        reasons.append("invalid_date")
    if key_duplicates:
        reasons.append("duplicate_date_symbol_key")
    if date_coverage < args.min_date_coverage:
        reasons.append("date_coverage_below_threshold")
    if symbol_coverage < args.min_symbol_coverage:
        reasons.append("symbol_coverage_below_threshold")
    if finite_ratio < args.min_finite_ratio:
        reasons.append("finite_ratio_below_threshold")
    if median_cross_section < args.min_cross_section:
        reasons.append("cross_section_below_threshold")
    return {
        "factor": name,
        "factor_column": value_col,
        "rows": int(len(work)),
        "unique_dates": int(len(observed_dates)),
        "unique_symbols": int(len(observed_symbols)),
        "date_coverage": date_coverage,
        "symbol_coverage": symbol_coverage,
        "finite_ratio": finite_ratio,
        "coverage_score": float(np.mean([date_coverage, symbol_coverage, finite_ratio])),
        "duplicate_date_symbol_keys": key_duplicates,
        "median_cross_section": median_cross_section,
        "reasons": reasons,
        "selected": not reasons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--calendar", type=Path)
    parser.add_argument("--min-date-coverage", type=float, default=0.80)
    parser.add_argument("--min-symbol-coverage", type=float, default=0.80)
    parser.add_argument("--min-finite-ratio", type=float, default=0.95)
    parser.add_argument("--min-cross-section", type=float, default=2.0)
    args = parser.parse_args()
    for value in (args.min_date_coverage, args.min_symbol_coverage, args.min_finite_ratio):
        if not 0 <= value <= 1:
            raise ValueError("Coverage and finite-value thresholds must be in [0, 1]")
    if args.min_cross_section < 1:
        raise ValueError("min_cross_section must be at least 1")
    start = pd.Timestamp(args.start_date).normalize()
    end = pd.Timestamp(args.end_date).normalize()
    if start > end:
        raise ValueError("start-date must not be after end-date")
    payload, records = load_manifest(args.manifest.resolve())
    if not records:
        raise ValueError("Manifest contains no factor records")

    loaded: list[tuple[dict[str, Any], str, Path, pd.DataFrame, str]] = []
    manifest_paths: set[Path] = set()
    factor_names: set[str] = set()
    for record in records:
        path = record_path(record, args.manifest.resolve().parent)
        if path in manifest_paths:
            raise ValueError(f"Duplicate factor path in manifest: {path}")
        manifest_paths.add(path)
        for name, frame, value_col in factor_frames(record, path):
            if name in factor_names:
                raise ValueError(f"Duplicate factor identifier after expansion: {name}")
            factor_names.add(name)
            loaded.append((record, name, path, frame, value_col))
    if args.calendar:
        calendar = read_table(args.calendar.resolve())
        calendar_col = first_column(calendar.columns, DATE_NAMES)
        if calendar_col is None:
            raise ValueError("Calendar has no date column")
        expected_dates = {
            pd.Timestamp(date).normalize()
            for date in pd.to_datetime(calendar[calendar_col], errors="coerce").dt.normalize().dropna().unique()
            if start <= pd.Timestamp(date).normalize() <= end
        }
    else:
        expected_dates = set()
        for _, _, _, frame, _ in loaded:
            date_col = first_column(frame.columns, DATE_NAMES)
            dates = pd.to_datetime(frame[date_col], errors="coerce").dt.normalize()
            expected_dates.update(
                pd.Timestamp(date).normalize()
                for date in dates.dropna().unique()
                if start <= pd.Timestamp(date).normalize() <= end
            )
    if not expected_dates:
        raise ValueError("The declared research range has no expected dates")
    expected_symbols: set[str] = set()
    for _, _, _, frame, _ in loaded:
        symbol_col = first_column(frame.columns, SYMBOL_NAMES)
        date_col = first_column(frame.columns, DATE_NAMES)
        if symbol_col and date_col:
            dates = pd.to_datetime(frame[date_col], errors="coerce").dt.normalize()
            in_range = dates.between(start, end)
            expected_symbols.update(frame.loc[in_range, symbol_col].dropna().astype(str))
    expected_symbols = expected_symbols or {"__single_series__"}

    audits: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for record, name, path, frame, value_col in loaded:
        try:
            audit = audit_factor(name, frame, value_col, start, end, expected_dates, expected_symbols, args)
            audit["path"] = str(path)
            audits.append(audit)
            if audit["selected"]:
                item = dict(record)
                item.update({"name": name, "path": str(path), "factor_column": value_col})
                selected.append(item)
        except Exception as exc:  # record failures instead of silently dropping them
            errors.append({"factor": name, "path": str(path), "error": repr(exc)})
    for error in errors:
        audits.append({"factor": error["factor"], "path": error["path"], "selected": False, "reasons": ["audit_error"], **error})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(audits).to_csv(args.output_dir / "factor_audit.csv", index=False)
    excluded = [item for item in audits if not item.get("selected", False)]
    pd.DataFrame(excluded).to_csv(args.output_dir / "excluded_factors.csv", index=False)
    result = {
        "schema_version": "1.0.0",
        "selected_factors": selected,
        "study_range": [args.start_date, args.end_date],
        "thresholds": {
            "min_date_coverage": args.min_date_coverage,
            "min_symbol_coverage": args.min_symbol_coverage,
            "min_finite_ratio": args.min_finite_ratio,
            "min_cross_section": args.min_cross_section,
        },
        "counts": {"input_records": len(loaded), "selected": len(selected), "excluded": len(excluded)},
    }
    (args.output_dir / "selected_factors.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_sha256 = sha256_file(args.manifest.resolve())
    receipt = {
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": manifest_sha256,
        "input_files": sorted({str(path): sha256_file(path) for _, _, path, _, _ in loaded}.items()),
        "study_range": [args.start_date, args.end_date],
        "expected_dates": len(expected_dates),
        "expected_symbols": len(expected_symbols),
        "no_oos_used": True,
    }
    (args.output_dir / "audit_receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    selected_audits = [item for item in audits if item.get("selected", False)]
    envelope = build_ranked_factor_set(
        selected_audits,
        dataset_id=f"coverage-filter-{args.end_date}",
        producer="skill-factor-coverage-filter",
        selection_method="coverage-threshold-filter",
        source_profile="factor-panel",
        source_path=args.manifest.resolve(),
        source_sha256=manifest_sha256,
        as_of=args.end_date,
        score_key="coverage_score",
        evaluation_ref="artifact://factor-coverage-filter/factor_audit.csv",
        evidence_ref="artifact://factor-coverage-filter/audit_receipt.json",
        checks=["date-coverage", "symbol-coverage", "finite-values", "duplicate-keys"],
        warnings=[f"{len(excluded)} candidates excluded"] if excluded else [],
    )
    (args.output_dir / "ranked_factor_set.json").write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()

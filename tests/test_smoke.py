from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def prepare(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    subprocess.run(
        [sys.executable, str(ROOT / "examples/generate_smoke_data.py"), "--output-dir", str(data)],
        check=True,
        text=True,
        capture_output=True,
    )
    return data


def run_cli(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    data = prepare(tmp_path)
    command = [
        sys.executable,
        str(ROOT / "scripts/coverage_filter.py"),
        "--manifest",
        str(data / "manifest.json"),
        "--output-dir",
        str(tmp_path / "out"),
        "--start-date",
        "2023-01-02",
        "--end-date",
        "2023-01-09",
        "--min-date-coverage",
        "1",
        "--min-symbol-coverage",
        "1",
        "--min-finite-ratio",
        "0.9",
        "--min-cross-section",
        "3",
    ]
    return subprocess.run(command, text=True, capture_output=True)


def test_smoke_outputs_ranked_envelope_and_audits(tmp_path: Path) -> None:
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"input_records": 2, "selected": 1, "excluded": 1}
    output = tmp_path / "out"
    envelope = json.loads((output / "ranked_factor_set.json").read_text(encoding="utf-8"))
    assert envelope["$contract"]["profile"] == "ranked-factor-set"
    assert [item["factor_id"] for item in envelope["payload"]["records"]] == ["good_factor"]
    audit = pd.read_csv(output / "factor_audit.csv")
    assert set(audit["factor"]) == {"good_factor", "sparse_factor"}
    assert (output / "audit_receipt.json").is_file()


def test_invalid_date_is_explicitly_excluded(tmp_path: Path) -> None:
    data = prepare(tmp_path)
    frame = pd.read_csv(data / "sparse.csv")
    frame.loc[0, "date"] = "not-a-date"
    frame.to_csv(data / "sparse.csv", index=False)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/coverage_filter.py"),
            "--manifest",
            str(data / "manifest.json"),
            "--output-dir",
            str(tmp_path / "invalid-out"),
            "--start-date",
            "2023-01-02",
            "--end-date",
            "2023-01-09",
            "--min-date-coverage",
            "0.8",
            "--min-symbol-coverage",
            "1",
            "--min-finite-ratio",
            "0.4",
            "--min-cross-section",
            "3",
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    audit = pd.read_csv(tmp_path / "invalid-out/factor_audit.csv")
    sparse = audit.loc[audit["factor"] == "sparse_factor"].iloc[0]
    assert "invalid_date" in sparse["reasons"]

def test_zero_selection_fails_after_writing_audit_receipt(tmp_path: Path) -> None:
    data = prepare(tmp_path)
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    manifest["factors"] = [manifest["factors"][1]]
    (data / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/coverage_filter.py"),
            "--manifest",
            str(data / "manifest.json"),
            "--output-dir",
            str(tmp_path / "empty-out"),
            "--start-date",
            "2023-01-02",
            "--end-date",
            "2023-01-09",
            "--min-date-coverage",
            "1",
            "--min-symbol-coverage",
            "1",
            "--min-finite-ratio",
            "0.9",
            "--min-cross-section",
            "3",
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert (tmp_path / "empty-out/factor_audit.csv").is_file()
    assert (tmp_path / "empty-out/audit_receipt.json").is_file()
    assert not (tmp_path / "empty-out/ranked_factor_set.json").exists()


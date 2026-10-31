import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from civictrace.lineage import (
    fixture_passports,
    migrate_passport,
    snapshot_record_lineage,
    verify_fixture_passports,
)
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "examples/synthetic_procurement.json").read_bytes()
KW = dict(
    expected_sha256="bb30164c2944433984b29855a5416be52e640fd94a48916ef9327ed9697bcef2",
    collected_at="2026-10-10T00:00:00Z",
)


def validator():
    schema = json.loads((ROOT / "schemas/evidence-passport.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_every_supported_fixture_result_and_unknown_zero():
    passports = fixture_passports(RAW, **KW)
    assert len(passports) == 7
    rows = [p for p in passports if p["result_kind"] == "explorer-record"]
    assert [r["lineage"]["original_pointer"] for r in rows] == [f"/{i}" for i in range(5)]
    assert rows[2]["result"]["bid_count"] is None
    assert rows[3]["result"]["bid_count"] == 0
    assert verify_fixture_passports(passports, RAW, **KW)["source_truth_verified"] is False
    for p in passports:
        if p["result_kind"] == "finding":
            validator().validate(p["result"])
    assert passports == fixture_passports(RAW, **KW)


@pytest.mark.parametrize("mutation", ["pointer", "hash", "environment", "result", "code", "rights"])
def test_tampering_rejected(mutation):
    passports = fixture_passports(RAW, **KW)
    row = passports[0]
    if mutation == "pointer":
        row["lineage"]["original_pointer"] = "/1"
    elif mutation == "hash":
        row["lineage"]["decompressed_sha256"] = "a" * 64
    elif mutation == "environment":
        row["lineage"]["environment"]["python"] = "unknown"
    elif mutation == "result":
        row["result"]["bid_count"] = 100
    elif mutation == "code":
        row["lineage"]["transformations"][0]["implementation_sha256"] = "a" * 64
    else:
        row["lineage"]["rights"]["license"] = "invented"
    with pytest.raises(ValueError, match="replay mismatch"):
        verify_fixture_passports(passports, RAW, **KW)


def test_missing_and_wrong_source_inputs():
    for raw in (b"", RAW + b" ", b"[]"):
        with pytest.raises(ValueError):
            fixture_passports(raw, **KW)
    with pytest.raises(ValueError):
        fixture_passports(RAW, **dict(KW, expected_sha256="a" * 64))
    with pytest.raises(ValueError):
        fixture_passports(RAW, **dict(KW, collected_at="2026-01-01"))


def test_lossless_migration_and_schema_dispatch():
    p = next(p["result"] for p in fixture_passports(RAW, **KW) if p["result_kind"] == "finding")
    legacy = deepcopy(p)
    legacy.pop("lineage")
    legacy["schema_version"] = "0.1.0"
    previous = deepcopy(legacy)
    validator().validate(legacy)
    migrated = migrate_passport(legacy)
    validator().validate(migrated)
    assert legacy == previous
    assert migrated["finding_id"] == legacy["finding_id"]
    assert migrated["lineage"]["environment"] is None
    assert migrated["lineage"]["decompressed_sha256"] is None
    assert migrate_passport(migrated) == migrated
    for key in legacy:
        if key != "schema_version":
            assert migrated[key] == legacy[key]
    legacy["schema_version"] = "9"
    with pytest.raises(ValueError):
        migrate_passport(legacy)
    assert list(validator().iter_errors(legacy))


def test_snapshot_complete_chain_replay(tmp_path):
    completed = subprocess.run(
        [sys.executable, "scripts/snapshot_example.py", str(tmp_path / "demo"), "--rows", "2"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    snapshot_id = json.loads(completed.stdout)["snapshot_id"]
    path = tmp_path / "demo/snapshot-a"
    result = snapshot_record_lineage(path, expected_snapshot_id=snapshot_id)
    assert len(result["rows"]) == 2
    assert result["analytics_enabled"] is False
    assert all(row["provenance"]["record_sha256"] for row in result["rows"])
    assert result == snapshot_record_lineage(path, expected_snapshot_id=snapshot_id)
    with pytest.raises(ValueError, match="pin mismatch"):
        snapshot_record_lineage(path, expected_snapshot_id="a" * 64)
    (path / "evidence/source.jsonl.gz").write_bytes(b"changed")
    with pytest.raises(ValueError):
        snapshot_record_lineage(path, expected_snapshot_id=snapshot_id)


def test_cohort_passport_and_changed_result(tmp_path):
    from civictrace.analytics import Cohort, query_snapshot
    from civictrace.lineage import cohort_result_passport

    completed = subprocess.run(
        [sys.executable, "scripts/snapshot_example.py", str(tmp_path / "demo"), "--rows", "2"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    identity = json.loads(completed.stdout)["snapshot_id"]
    path = tmp_path / "demo/snapshot-a"
    result = query_snapshot(
        path,
        expected_snapshot_id=identity,
        cohort=Cohort("PYG", "2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z", "complete"),
    )
    passport = cohort_result_passport(path, result, expected_snapshot_id=identity)
    assert len(passport["lineage"]["rows"]) == 2
    assert passport["result"]["included_rows"] == 2
    result["exact_amount_sum"] = "1"
    with pytest.raises(ValueError, match="result replay mismatch"):
        cohort_result_passport(path, result, expected_snapshot_id=identity)


def test_cli_lineage_and_example(tmp_path):
    output = tmp_path / "findings.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "civictrace.cli",
            str(ROOT / "examples/synthetic_procurement.json"),
            "--collected-at",
            KW["collected_at"],
            "--lineage",
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "2 synthetic" in completed.stdout
    for finding in json.loads(output.read_text()):
        assert finding["schema_version"] == "0.2.0"
        validator().validate(finding)
    bundle = tmp_path / "bundle.json"
    command = [sys.executable, "scripts/lineage_example.py", "--output", str(bundle)]
    run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    assert json.loads(run.stdout)["results"] == 5
    assert len(json.loads(bundle.read_text())) == 7
    assert subprocess.run(command, cwd=ROOT, capture_output=True).returncode != 0


def test_frontend_projection_is_the_passported_result():
    payload = json.loads((ROOT / "frontend/public/data/synthetic-v1.json").read_text())
    records = [
        p["result"] for p in fixture_passports(RAW, **KW) if p["result_kind"] == "explorer-record"
    ]
    assert records == payload["records"]


@pytest.mark.parametrize(
    "field",
    ["environment", "artifacts", "transformations", "original_pointer", "decompressed_sha256"],
)
def test_complete_schema_rejects_missing_evidence(field):
    finding = next(
        p["result"] for p in fixture_passports(RAW, **KW) if p["result_kind"] == "finding"
    )
    finding["lineage"].pop(field)
    assert list(validator().iter_errors(finding))

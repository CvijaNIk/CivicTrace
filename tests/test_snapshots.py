"""Synthetic byte evidence only; snapshot integrity, precision and interruption regressions."""

import json
import os
import signal
import subprocess
import sys
import time
from decimal import Decimal
from unittest.mock import patch

import pyarrow.parquet as pq
import pytest
from civictrace import snapshots
from civictrace.dncp import IntakeError, OutputBudget, import_file
from test_dncp import BUDGET, release, setup


def intake(tmp_path, rows=None):
    raw = None if rows is None else ("\n".join(json.dumps(r) for r in rows) + "\n").encode()
    source, manifest = setup(tmp_path, raw)
    directory = tmp_path / "intake"
    import_file(source, directory, manifest, budget=BUDGET)
    return directory


def read_table(directory, table):
    return [
        row
        for p in sorted((directory / "tables" / table).rglob("*.parquet"))
        for row in pq.ParquetFile(p).read().to_pylist()
    ]


def test_deterministic_precision_lineage_and_no_overwrite(tmp_path):
    src = intake(tmp_path)
    a, b = tmp_path / "a", tmp_path / "b"
    m = snapshots.build_snapshot(src, a, budget=BUDGET)
    assert snapshots.build_snapshot(src, b, budget=BUDGET) == m
    assert snapshots.inventory(a) == snapshots.inventory(b)
    assert snapshots.verify_snapshot(a) == m
    assert m["analytics_enabled"] is False
    assert m["tables"] == dict(
        processes=1, releases=1, parties=2, awards=1, contracts=1, award_suppliers=2
    )
    award = read_table(a, "awards")[0]
    assert award["amount"] == Decimal("9007199254740993.01")
    assert award["currency"] == "PYG"
    assert read_table(a, "releases")[0]["date"].isoformat() == "2025-01-01T00:00:00+00:00"
    assert list((a / "tables" / "awards" / "release_year=2025").glob("*.parquet"))
    assert (a / "evidence" / "source.jsonl.gz").read_bytes() == (
        src / "source.jsonl.gz"
    ).read_bytes()
    assert award["record_sha256"] in award["source_file"]
    assert json.loads(award["canonical_json"])["money"]["amount"]["value"] == "9007199254740993.01"
    with pytest.raises(IntakeError, match="output_exists"):
        snapshots.build_snapshot(src, a, budget=BUDGET)
    assert snapshots.verify_snapshot(a) == m


@pytest.mark.parametrize(
    "value,expected,exclusion",
    [
        ("0", Decimal(0), False),
        ("0.000000000000000001", Decimal("1e-18"), False),
        ("0.0000000000000000001", None, True),
        ("1e58", None, True),
        ("9" * 58 + "." + "9" * 18, Decimal("9" * 58 + "." + "9" * 18), False),
        ("-1", None, False),
        (None, None, False),
    ],
)
def test_decimal_boundaries_preserve_original(tmp_path, value, expected, exclusion):
    r = release()
    r["awards"][0]["value"]["amount"] = value
    src = intake(tmp_path, [r])
    out = tmp_path / "out"
    m = snapshots.build_snapshot(src, out, budget=BUDGET)
    award = read_table(out, "awards")[0]
    assert award["amount"] == expected
    assert bool(award["projection_exclusion"]) == exclusion
    assert m["projection_exclusions"] == int(exclusion)
    assert json.loads(award["canonical_json"])["money"]["amount"]["raw"] == value


def test_rejections_unknowns_and_quarantine(tmp_path):
    r = release()
    r["date"] = "invalid"
    r["awards"][0]["value"]["currency"] = "XXX"
    r["contracts"].insert(0, {"id": "broken", "awardID": "no-such-award", "value": {}})
    src = intake(tmp_path, [r, r, {"bad": "record"}])
    out = tmp_path / "out"
    m = snapshots.build_snapshot(src, out, budget=BUDGET)
    assert m["import_summary"]["rejected"] == 2
    assert m["validation_field_states"]["invalid"] == 1
    assert m["validation_field_states"]["unsupported"] == 1
    assert list((out / "tables" / "awards" / "release_year=unknown").glob("*.parquet"))
    assert read_table(out, "awards")[0]["currency"] is None
    report = [
        json.loads(x) for x in (out / "evidence" / "validation.jsonl").read_text().splitlines()
    ]
    assert report[0]["quarantined"][0]["reason"] == "contract_linkage"
    assert len(list((out / "evidence").glob("*.raw"))) == 3


@pytest.mark.parametrize(
    "target",
    [
        "manifest.json",
        "summary.json",
        "validation.jsonl",
        "source.jsonl.gz",
        "canonical",
        "raw",
        "extra",
    ],
)
def test_corrupted_intake_is_not_projected(tmp_path, target):
    src = intake(tmp_path)
    path = (
        next(src.glob("*.canonical.json"))
        if target == "canonical"
        else next(src.glob("*.raw"))
        if target == "raw"
        else src / target
    )
    if target in {"manifest.json", "summary.json", "canonical"}:
        data = json.loads(path.read_text())
        data["tamper"] = "changed"
        path.write_text(json.dumps(data))
    else:
        path.write_bytes(b"corrupted")
    with pytest.raises((ValueError, OSError)):
        snapshots.build_snapshot(src, tmp_path / "out", budget=BUDGET)
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".parquet-*"))


@pytest.mark.parametrize(
    "target", ["manifest.json", "manifest.sha256", "parquet", "evidence", "extra"]
)
def test_snapshot_corruption(tmp_path, target):
    out = tmp_path / "out"
    snapshots.build_snapshot(intake(tmp_path), out, budget=BUDGET)
    path = (
        next(out.rglob("*.parquet"))
        if target == "parquet"
        else out / "evidence" / "validation.jsonl"
        if target == "evidence"
        else out / target
    )
    path.write_bytes(b"changed")
    with pytest.raises((ValueError, OSError)):
        snapshots.verify_snapshot(out)


@pytest.mark.parametrize("mode", ["bytes", "files", "free-bytes", "free-inodes"])
def test_budgets_fail_during_projection(tmp_path, mode):
    src = intake(tmp_path)
    files = snapshots.inventory(src)
    budget = OutputBudget(
        max_bytes=sum(f["bytes"] for f in files) + len(snapshots.SCHEMA.serialize()) + 1
        if mode == "bytes"
        else BUDGET.max_bytes,
        max_files=len(files) + 1 if mode == "files" else BUDGET.max_files,
        min_free_bytes=10**30 if mode == "free-bytes" else 0,
        min_free_inodes=10**30 if mode == "free-inodes" else 0,
    )
    with pytest.raises(IntakeError):
        snapshots.build_snapshot(src, tmp_path / "out", budget=budget)
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".parquet-*"))


def test_writer_failure_and_publication_race(tmp_path):
    src = intake(tmp_path)
    out = tmp_path / "out"
    with patch.object(snapshots.pq, "write_table", side_effect=OSError("synthetic disk failure")):
        with pytest.raises(OSError):
            snapshots.build_snapshot(src, out, budget=BUDGET)
    assert not out.exists()
    real_publish = snapshots._publisher()

    def race(stage, dest):
        dest.mkdir()
        (dest / "sentinel").write_text("preserve")
        real_publish(stage, dest)

    with patch.object(snapshots, "_publisher", return_value=race):
        with pytest.raises(FileExistsError):
            snapshots.build_snapshot(src, out, budget=BUDGET)
    assert (out / "sentinel").read_text() == "preserve"
    assert not list(tmp_path.glob(".parquet-*"))


def test_sigkill_during_parquet_writing_and_retry(tmp_path):
    src = intake(tmp_path)
    out = tmp_path / "out"
    marker = tmp_path / "ready"
    code = """
import os, signal, sys
from pathlib import Path
from civictrace import snapshots as s
from civictrace.dncp import OutputBudget
write = s.pq.write_table
def stop(*args, **kwargs):
    write(*args, **kwargs)
    Path(sys.argv[3]).write_text("ready")
    os.kill(os.getpid(), signal.SIGSTOP)
s.pq.write_table = stop
s.build_snapshot(sys.argv[1], sys.argv[2], budget=OutputBudget(100000000, 1000))
"""
    child = subprocess.Popen([sys.executable, "-c", code, str(src), str(out), str(marker)])
    try:
        deadline = time.monotonic() + 20
        while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists()
        assert not out.exists()
        child.kill()
        child.wait(timeout=5)
        assert child.returncode == -signal.SIGKILL
        stages = list(tmp_path.glob(".parquet-*"))
        assert len(stages) == 1
        assert stat_private(stages[0])
        snapshots.build_snapshot(src, out, budget=BUDGET)
        snapshots.verify_snapshot(out)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)


def stat_private(path):
    return path.stat().st_mode & 0o777 == 0o700


def test_many_records_have_bounded_row_groups(tmp_path):
    rows = []
    for n in range(100):
        r = release()
        r["ocid"] += str(n)
        rows.append(r)
    src = intake(tmp_path, rows)
    m = snapshots.build_snapshot(src, tmp_path / "out", budget=BUDGET)
    assert m["tables"]["awards"] == 100
    assert m["tables"]["parties"] == 200
    assert len(m["files"]) < 1000
    assert sum(x["bytes"] for x in m["files"]) < 32 * 1024**2
    for path in (tmp_path / "out").rglob("*.parquet"):
        pf = pq.ParquetFile(path)
        assert pf.schema_arrow == snapshots.SCHEMA
        assert pf.metadata.row_group(0).num_rows <= 4096


def test_empty_source_retains_schema_and_evidence(tmp_path):
    source, manifest = setup(tmp_path, b"")
    directory = tmp_path / "intake"
    import_file(source, directory, manifest, budget=BUDGET)
    out = tmp_path / "out"
    result = snapshots.build_snapshot(directory, out, budget=BUDGET)
    assert all(n == 0 for n in result["tables"].values())
    assert not list(out.rglob("*.parquet"))
    assert (out / "schema.arrow").is_file()
    snapshots.verify_snapshot(out)


def test_partitions_are_utc_and_keep_cancelled_versions(tmp_path):
    a, b = release(), release()
    a["date"] = "2025-01-01T00:30:00+01:00"
    b["ocid"] += "-OTHER"
    b["tender"]["status"] = "cancelled"
    src = intake(tmp_path, [a, b])
    out = tmp_path / "out"
    result = snapshots.build_snapshot(src, out, budget=BUDGET)
    assert result["tables"]["releases"] == 2
    assert {p.name for p in (out / "tables" / "releases").iterdir()} == {
        "release_year=2024",
        "release_year=2025",
    }
    assert {r["status"] for r in read_table(out, "releases")} == {"complete", "cancelled"}


def test_symlinks_rejected_without_reading_targets(tmp_path):
    src = intake(tmp_path)
    raw = next(src.glob("*.raw"))
    raw.unlink()
    raw.symlink_to("/dev/zero")
    with pytest.raises(IntakeError, match="unsafe_snapshot_entry"):
        snapshots.build_snapshot(src, tmp_path / "out", budget=BUDGET)
    assert not (tmp_path / "out").exists()


def test_verifier_rejects_fifo_hash_without_blocking(tmp_path):
    out = tmp_path / "out"
    snapshots.build_snapshot(intake(tmp_path), out, budget=BUDGET)
    path = out / "manifest.sha256"
    path.unlink()
    os.mkfifo(path)
    with pytest.raises(IntakeError, match="regular_file_required"):
        snapshots.verify_snapshot(out)

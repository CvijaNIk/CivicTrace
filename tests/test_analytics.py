"""Deterministic invented snapshots; no real indicators or network fixtures."""

import json
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch

import pytest
from civictrace.analytics import (
    AnalyticsError,
    Cohort,
    QueryBudget,
    _connection,
    query_snapshot,
)
from civictrace.canonical import serialize
from civictrace.snapshots import build_snapshot, verify_snapshot
from test_dncp import BUDGET, release
from test_snapshots import intake

COHORT = Cohort("PYG", "2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "complete")


def snapshot(tmp_path, rows=None):
    directory = tmp_path / "snapshot"
    manifest = build_snapshot(intake(tmp_path, rows), directory, budget=BUDGET)
    return directory, manifest["snapshot_id"]


def run(snap, cohort=COHORT, **kwargs):
    return query_snapshot(snap[0], expected_snapshot_id=snap[1], cohort=cohort, **kwargs)


def test_exact_repeatable_cohort_and_lineage(tmp_path):
    snap = snapshot(tmp_path)
    before = verify_snapshot(snap[0])
    a = run(snap)
    assert run(snap) == a
    assert Decimal(a["exact_amount_sum"]) == Decimal("9007199254740993.01")
    assert (a["total_rows"], a["included_rows"], a["excluded_rows"]) == (1, 1, 0)
    assert not a["analytics_enabled"] and a["synthetic_only"]
    assert a["source"] == before["source"]
    assert a["import_summary"] == before["import_summary"]
    assert verify_snapshot(snap[0]) == before
    assert Decimal(run(snap, replace(COHORT, table="contracts"))["exact_amount_sum"]) == 0


def test_decimal256_sum_exceeds_duckdb_precision(tmp_path):
    a, b = release(), release()
    b["ocid"] += "2"
    value = "9" * 58 + "." + "9" * 18
    for row in (a, b):
        row["awards"][0]["value"]["amount"] = value
    result = run(snapshot(tmp_path, [a, b]))
    assert result["exact_amount_sum"] == "1" + "9" * 58 + "." + "9" * 17 + "8"


def test_exclusions_and_independent_missing_states(tmp_path):
    rows = []
    for n in range(9):
        row = release()
        row["ocid"] += str(n)
        rows.append(row)
    rows[1]["tender"]["status"] = "cancelled"
    rows[2]["date"] = "2024-12-31T23:59:59.999999Z"
    rows[3]["awards"][0]["value"]["currency"] = "USD"
    rows[4]["awards"][0]["value"]["currency"] = "XXX"
    rows[5]["awards"][0]["value"]["amount"] = None
    rows[6]["awards"][0]["value"]["amount"] = "1e58"
    rows[7].pop("date")
    rows[8]["tender"].pop("status")
    result = run(snapshot(tmp_path, rows))
    assert result["included_rows"] == 1 and result["excluded_rows"] == 8
    assert result["exclusions"] == dict(
        different_process_status=1,
        outside_period=1,
        different_currency=1,
        missing_currency=1,
        missing_amount=1,
        projection_exclusion=1,
        missing_release_date=1,
        missing_process_status=1,
    )
    assert result["field_states"]["currency"]["unsupported"] == 1
    assert result["field_states"]["amount"]["null"] == 1
    assert result["field_states"]["release_date"]["absent"] == 1


def test_utc_half_open_boundaries_and_currency(tmp_path):
    rows = []
    for n, date in enumerate(
        ("2025-01-01T01:00:00+01:00", "2026-01-01T00:00:00Z", "2025-12-31T23:59:59.999999Z")
    ):
        row = release()
        row["ocid"] += str(n)
        row["date"] = date
        row["awards"][0]["value"]["amount"] = "0.1"
        rows.append(row)
    rows[2]["awards"][0]["value"]["currency"] = "USD"
    snap = snapshot(tmp_path, rows)
    assert run(snap)["included_rows"] == 1
    usd = run(snap, replace(COHORT, currency="USD"))
    assert usd["included_rows"] == 1
    assert Decimal(usd["exact_amount_sum"]) == Decimal("0.1")
    assert usd["exclusions"] == {"different_currency": 1, "outside_period": 1}


@pytest.mark.parametrize(
    "cohort",
    [
        replace(COHORT, currency=""),
        replace(COHORT, status="complete' OR true--"),
        replace(COHORT, table="read_csv('/etc/passwd')"),
        replace(COHORT, start="2025-01-01"),
        replace(COHORT, end=COHORT.start),
        replace(COHORT, currency=None),
        replace(COHORT, start="2025-01-01T00:00:00.0000001Z"),
    ],
)
def test_reject_bad_cohort_before_process(cohort):
    with patch("civictrace.analytics.subprocess.run") as child:
        with pytest.raises(AnalyticsError):
            query_snapshot("/absent", expected_snapshot_id="a" * 64, cohort=cohort)
        child.assert_not_called()


@pytest.mark.parametrize(
    "query",
    [
        "SELECT 1",
        "COPY awards TO '/tmp/leak'",
        "INSTALL httpfs",
        "LOAD httpfs",
        "ATTACH '/etc/passwd'",
        "single_bid",
    ],
)
def test_no_unapproved_queries(query):
    with pytest.raises(AnalyticsError, match="unauthorized_query"):
        query_snapshot("/absent", expected_snapshot_id="a" * 64, cohort=COHORT, query=query)


def test_pin_corruption_and_unsafe_files(tmp_path):
    snap = snapshot(tmp_path)
    with pytest.raises(AnalyticsError, match="snapshot_pin_mismatch"):
        run((snap[0], "0" * 64))
    parquet = next(snap[0].rglob("*.parquet"))
    parquet.write_bytes(b"corrupt")
    with pytest.raises(AnalyticsError, match="snapshot_or_worker_invalid"):
        run(snap)
    parquet.unlink()
    parquet.symlink_to("/dev/zero")
    with pytest.raises(AnalyticsError, match="unsafe_snapshot_entry"):
        run(snap)


@pytest.mark.parametrize(
    "budget", [QueryBudget(max_files=1), QueryBudget(max_bytes=1), QueryBudget(max_rows=1)]
)
def test_resource_budgets(tmp_path, budget):
    with pytest.raises(AnalyticsError, match="budget"):
        run(snapshot(tmp_path), budget=budget)


def test_wall_timeout_and_worker_failure():
    with patch(
        "civictrace.analytics.subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1)
    ):
        with pytest.raises(AnalyticsError, match="worker_wall_limit"):
            run(("/unused", "a" * 64))
    with patch(
        "civictrace.analytics.subprocess.run", return_value=subprocess.CompletedProcess([], -9)
    ):
        with pytest.raises(AnalyticsError, match="worker_resource_or_execution_failure"):
            run(("/unused", "a" * 64))


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM read_csv('/etc/passwd')",
        "SELECT * FROM read_parquet('https://example.com/a.parquet')",
        "INSTALL httpfs",
        "LOAD httpfs",
        "COPY (SELECT 1) TO '/tmp/civictrace-forbidden'",
        "SET enable_external_access=true",
        "SET memory_limit='1TB'",
        "ATTACH '/tmp/forbidden.db' AS other",
    ],
)
def test_engine_defense_in_depth(sql):
    with _connection() as con:
        with pytest.raises(Exception):
            con.execute(sql)


def test_worker_network_syscalls_denied():
    code = """
import socket
from civictrace.analytics import _deny_network
_deny_network()
try:
    socket.socket()
except PermissionError:
    print('blocked')
else:
    raise AssertionError('network allowed')
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "blocked"


def test_empty_snapshot(tmp_path):
    result = run(snapshot(tmp_path, []))
    assert result["total_rows"] == 0 and result["exact_amount_sum"] is None


def test_real_source_guard_even_with_rehashed_manifest(tmp_path):
    import hashlib

    snap = snapshot(tmp_path)
    path = snap[0] / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["source"]["source_url"] = "https://example.org/real"
    manifest.pop("snapshot_id")
    identity = hashlib.sha256(serialize(manifest).encode()).hexdigest()
    manifest["snapshot_id"] = identity
    path.write_text(serialize(manifest))
    (snap[0] / "manifest.sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(AnalyticsError, match="synthetic_only"):
        run((snap[0], identity))

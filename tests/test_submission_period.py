"""Reviewed invented windows, explicit comparisons, replay and fail-closed boundaries."""

import json
import subprocess
import sys
from copy import deepcopy
from decimal import getcontext
from hashlib import sha256
from pathlib import Path

import pytest
from civictrace.submission_period import benchmarks, encoded, report
from civictrace.synthetic import assess_record, tender_period

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "examples/synthetic_submission_period.json").read_bytes()
CONFIG = (ROOT / "examples/synthetic_submission_benchmarks.json").read_bytes()


def test_exact_reviewed_results_and_denominators():
    result = report(RAW, CONFIG)
    rows = result["results"]
    assert result["denominators"] == dict(
        total_records=10, valid_duration_records=6, comparison_records=4, excluded_records=6
    )
    assert result["comparison_counts"] == dict(below=3, equal=1, above=0)
    assert result["exclusions"] == dict(
        period_unknown=1,
        period_absent=1,
        period_invalid=1,
        period_reversed=1,
        benchmark_unmatched=1,
        group_unknown=1,
    )
    assert [r["elapsed_seconds"] for r in rows] == [
        3600,
        0,
        86400,
        172800,
        None,
        None,
        None,
        86400,
        None,
        86400,
    ]
    assert [r["deviation_hours"] for r in rows] == ["-23", "-24", "0", "-24"] + [None] * 6
    assert rows[3]["benchmark"]["id"] == "SYN-LIMITED-72"
    assert rows[4]["field_states"]["tender_start"] == "null"
    assert rows[8]["field_states"] == dict(tender_start="absent", tender_end="absent")
    for i, row in enumerate(rows):
        assert row["original_pointer"] == f"/records/{i}"
        assert row["working_days"] is None
        assert row["allegations"] == []
    assert result["input_sha256"] == sha256(RAW).hexdigest()
    assert result["configuration_sha256"] == sha256(CONFIG).hexdigest()
    assert result["rights"]["license"] == "Apache-2.0"
    assert result["analytics_enabled"] is False


def test_configuration_sensitivity_changes_only_comparison():
    original = report(RAW, CONFIG)
    config = json.loads(CONFIG)
    config["version"] = "invented-v2"
    config["benchmarks"][0]["elapsed_hours"] = "0.5"
    config["benchmarks"][0]["basis"] = "Invented sensitivity scenario, not legal guidance"
    changed = report(RAW, encoded(config))
    assert changed["results"][0]["deviation_hours"] == "0.5"
    assert changed["results"][0]["relation"] == "above"
    assert changed["results"][2]["deviation_hours"] == "23.5"
    assert changed["configuration_sha256"] != original["configuration_sha256"]
    assert changed["results"][3] == original["results"][3]
    assert changed["denominators"] == original["denominators"]
    for a, b in zip(original["results"], changed["results"], strict=True):
        for key in ("elapsed_seconds", "elapsed_hours", "period_state", "original_dates"):
            assert a[key] == b[key]


@pytest.mark.parametrize(
    "start,end,state,seconds",
    [
        ("2026-01-01T23:30:00-03:00", "2026-01-02T03:30:00Z", "present", 3600),
        ("2026-01-01T01:00:00+01:00", "2026-01-01T00:00:00Z", "present", 0),
        ("2026-01-01T00:00:00Z", "2026-01-01T00:00:00.000001Z", "present", 0.000001),
        ("2026-01-01T00:00:00Z", "2026-01-01T23:59:59.999999Z", "present", 86399.999999),
        ("2026-01-01T00:00:00Z", "2026-01-02T00:00:00.000001Z", "present", 86400.000001),
        ("2026-03-29T01:30:00+01:00", "2026-03-29T03:30:00+02:00", "present", 3600),
        ("2026-01-01T00:00:00-03:00", "2026-01-01T01:00:00Z", "reversed", None),
        (None, "2026-01-01T00:00:00Z", "unknown", None),
        ("2026-01-01T00:00:00", "2026-01-02T00:00:00Z", "invalid", None),
        ("2026-02-30T00:00:00Z", "2026-03-01T00:00:00Z", "invalid", None),
        (42, False, "invalid", None),
    ],
)
def test_shared_utc_logic_and_legacy_compatibility(start, end, state, seconds):
    record = dict(tender_start=start, tender_end=end, bid_count=1)
    assert tender_period(record) == (state, seconds)
    legacy = assess_record(record)
    assert legacy["tender_period_state"] == state
    assert legacy["tender_duration_seconds"] == seconds


@pytest.mark.parametrize(
    "hours", ["0", "-1", "NaN", "Infinity", "87600.000001", "0.0000001", True, 24]
)
def test_bad_reference_periods(hours):
    config = json.loads(CONFIG)
    config["benchmarks"][0]["elapsed_hours"] = hours
    with pytest.raises(ValueError):
        report(RAW, encoded(config))


@pytest.mark.parametrize("key", ["basis", "reference", "id"])
def test_missing_justification_or_identity(key):
    config = json.loads(CONFIG)
    del config["benchmarks"][0][key]
    with pytest.raises(ValueError):
        report(RAW, encoded(config))


def test_ambiguous_groups_unknown_input_and_bounds():
    config = json.loads(CONFIG)
    config["benchmarks"].append(deepcopy(config["benchmarks"][0]))
    with pytest.raises(ValueError, match="ambiguous"):
        report(RAW, encoded(config))
    with pytest.raises(ValueError, match="pinned invented"):
        report(RAW.replace(b"SYN-WINDOW-offset", b"DNCP-REAL-record"), CONFIG)
    with pytest.raises(ValueError, match="64 KiB"):
        report(RAW, b" " * 65537)
    with pytest.raises(ValueError, match="duplicate JSON key"):
        benchmarks(b'{"version":"a","version":"b"}')
    with pytest.raises(ValueError, match="nonfinite"):
        benchmarks(b'{"x":NaN}')
    config = json.loads(CONFIG)
    config["benchmarks"][0]["group"]["category"] = None
    with pytest.raises(ValueError, match="dimensions"):
        report(RAW, encoded(config))
    config = json.loads(CONFIG)
    config["benchmarks"] = []
    result = report(RAW, encoded(config))
    assert result["denominators"]["comparison_records"] == 0
    assert result["comparison_counts"] == dict(below=0, equal=0, above=0)


def test_reproducibility_cli_and_no_input_mutation():
    before = (RAW, CONFIG)
    expected = encoded(report(RAW, CONFIG))
    assert encoded(report(RAW, CONFIG)) == expected
    old = getcontext().prec
    try:
        getcontext().prec = 3
        assert encoded(report(RAW, CONFIG)) == expected
    finally:
        getcontext().prec = old
    args = [sys.executable, str(ROOT / "scripts/submission_period_example.py")]
    assert subprocess.check_output(args) == expected
    assert subprocess.check_output(args) == expected
    assert (RAW, CONFIG) == before


def test_working_day_configuration_is_rejected():
    config = json.loads(CONFIG)
    config["benchmarks"][0]["working_days"] = 2
    with pytest.raises(ValueError, match="elapsed hours only"):
        report(RAW, encoded(config))

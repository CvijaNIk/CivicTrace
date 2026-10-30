"""Deterministic synthetic frames plus importer/profiler compatibility; no network."""

import importlib.util
import json
import random
import sys
from pathlib import Path

import pytest
from civictrace.dncp import import_file
from test_dncp import BUDGET, release, setup

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("quality", SCRIPTS / "assess_dncp_quality.py")
quality = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quality)


def row(i, status="complete", year=2025, lots=2):
    r = release()
    r["ocid"] = f"ocds-03ad3f-SYN-{i}"
    r["tender"].update(
        status=status,
        numberOfTenderers=2,
        tenderers=[{"id": "p1"}, {"id": "p2"}],
        tenderPeriod={"startDate": f"{year}-03-01T00:00:00Z"},
        lots=[{"id": f"l{x}"} for x in range(lots)],
    )
    r["bids"] = {
        "details": [
            {"id": "b1", "tenderers": [{"id": "p1"}], "relatedLots": ["l0", "l1"]},
            {"id": "b2", "tenderers": [{"id": "p2"}], "relatedLots": ["l1"]},
            {"id": "b3", "tenderers": [{"id": "p1"}], "relatedLots": ["l0"]},
        ]
    }
    return r


def intake(tmp_path, records):
    raw = b"".join((json.dumps(r) + "\n").encode() for r in records)
    source, manifest = setup(tmp_path, raw)
    output = tmp_path / "import"
    import_file(source, output, manifest, budget=BUDGET)
    return output


def test_all_substantive_strata_and_reproducibility(tmp_path):
    records = [
        row(f"{s}-{y}-{lots}-{i}", s, y, lots)
        for s in quality.STATUSES[:-1]
        for y in (2022, 2025)
        for lots in (1, 2)
        for i in range(7)
    ]
    out = intake(tmp_path, records)
    a = quality.assess(out, per_stratum=3)
    b = quality.assess(out, per_stratum=3)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    populated = [s for s in a["strata"] if s["frame_rows"]]
    assert len(populated) == 12
    assert all(s["frame_rows"] == 7 and s["selected_rows"] == 3 for s in populated)
    assert all(s["inclusion_probability"] == {"numerator": 3, "denominator": 7} for s in populated)
    assert a["frame_rows"] == a["profiled_rows"] == 84
    # Listing order and input line order cannot change chosen process units.
    other = tmp_path / "other"
    other.mkdir()
    reverse = quality.assess(intake(other, records[::-1]), per_stratum=3)
    assert a["strata"] == reverse["strata"]
    different = quality.assess(out, seed="predeclared-other-seed", per_stratum=3)
    assert a["strata"] != different["strata"]
    assert a["analytics"]["status"] == "blocked"


def test_participant_bid_and_lot_counts_are_distinct():
    r = quality.relation(row(1))
    assert r["reported_tenderers"] == r["unique_tenderers"] == 2
    assert r["bid_details"] == 3
    assert r["unique_bid_participants"] == 2
    assert r["per_lot_unique_participants"] == [1, 2]
    assert r["reported_vs_bid_participants"] == "equal"
    assert r["bid_lot_linkage"] == "valid"


@pytest.mark.parametrize(
    "mutation,expected", [("absent", "unknown"), ("null", "unknown"), ("dangling", "invalid")]
)
def test_missing_or_dangling_lot_linkage(mutation, expected):
    r = row(1)
    b = r["bids"]["details"][0]
    if mutation == "absent":
        del b["relatedLots"]
    else:
        b["relatedLots"] = None if mutation == "null" else ["missing-lot"]
    assert quality.relation(r)["bid_lot_linkage"] == expected
    assert quality.relation(r)["per_lot_unique_participants"] is None


def test_absent_null_empty_and_duplicate_counts():
    r = row(1)
    del r["bids"]
    r["tender"]["numberOfTenderers"] = None
    a = quality.relation(r)
    assert a["reported_tenderers_state"] == "null"
    assert a["bid_details"] is None and a["unique_bid_participants"] is None
    r["bids"] = {"details": []}
    r["tender"]["numberOfTenderers"] = 0
    b = quality.relation(r)
    assert b["bid_details"] == b["unique_bid_participants"] == 0
    r = row(2)
    r["bids"]["details"][1]["id"] = "b1"
    assert quality.relation(r)["bid_ids"] == "duplicate"
    r["tender"]["numberOfTenderers"] = True
    assert quality.relation(r)["reported_tenderers_state"] == "invalid"


def test_importer_quarantine_does_not_hide_missing_contract(tmp_path):
    r = row(1)
    r["contracts"].append({"dateSigned": None})
    out = intake(tmp_path, [r])
    canonical = json.loads(next(out.glob("*.canonical.json")).read_text())
    assert len(canonical["contracts"]) == 1
    result = quality.assess(out)
    sample = next(s for s in result["strata"] if s["selected_rows"])
    fields = sample["observations"][0]["fields"]
    assert len(fields["contracts"]) == 2
    assert fields["contracts"][1]["id"] == "absent"
    assert fields["contracts"][1]["date_signed"] == "null"
    assert result["checks"]["contracts_id"]["denominator"] == 2
    assert result["checks"]["contracts_id"]["result"] == "fail"
    assert sample["coverage"] == "shortfall"
    assert any(s["coverage"] == "empty" for s in result["strata"])


def test_unknown_strata_privacy_and_utc_period():
    r = row(1)
    r["tender"]["status"] = "private-name@example.invalid"
    r["tender"]["tenderPeriod"]["startDate"] = "2024-01-01T00:30:00+02:00"
    r["contracts"][0]["status"] = "private-name@example.invalid"
    raw = json.dumps(r).encode()
    s, o, _ = quality.observe(raw, 2024)
    assert s == ("unknown", "older", "multiple")
    text = json.dumps(o)
    assert "private-name" not in text and "ocds-03ad3f-SYN" not in text
    assert "9007199254740993" not in text
    r["tender"]["tenderPeriod"]["startDate"] = None
    del r["tender"]["lots"]
    assert quality.observe(json.dumps(r).encode(), 2024)[0] == ("unknown", "unknown", "unknown")


def test_duplicate_process_and_tamper_fail_closed(tmp_path):
    a, b = row(1), row(1)
    b["id"] = "r2"
    out = intake(tmp_path, [a, b])
    with pytest.raises(ValueError, match="duplicate_process"):
        quality.assess(out)
    raw = next(out.glob("*.raw"))
    raw.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="raw_hash_mismatch"):
        quality.assess(out)


def test_rejected_rows_remain_in_frame(tmp_path):
    r = row(1)
    r["tender"] = []
    out = intake(tmp_path, [r])
    result = quality.assess(out)
    assert result["frame_rows"] == 1 and result["profiled_rows"] == 0
    assert result["unprofiled"] == {"unsupported_or_invalid_raw_row": 1}
    assert result["checks"]["contracts_id"]["result"] == "insufficient_data"


@pytest.mark.parametrize(
    "kwargs", [dict(per_stratum=0), dict(per_stratum=26), dict(seed=""), dict(cutoff=True)]
)
def test_invalid_design(tmp_path, kwargs):
    with pytest.raises(ValueError):
        quality.assess(tmp_path, **kwargs)


def test_incomplete_frame(tmp_path):
    out = intake(tmp_path, [row(1)])
    next(out.glob("*.raw")).unlink()
    with pytest.raises(ValueError, match="incomplete_intake_frame"):
        quality.assess(out)


def test_profiler_compatibility_boundary_is_visible(tmp_path):
    r = row(1)
    r["unused"] = random.Random(0).randbytes(530000).hex()
    out = intake(tmp_path, [r])
    result = quality.assess(out)
    assert result["profiled_rows"] == 0
    assert result["unprofiled"]["unsupported_or_invalid_raw_row"] == 1


def test_coverage_threshold_exact_boundary(tmp_path):
    records = [row(i) for i in range(20)]
    records[0]["tender"]["numberOfTenderers"] = None
    out = intake(tmp_path, records)
    a = quality.assess(out, per_stratum=25)
    assert a["checks"]["reported_tenderers"]["valid"] == 19
    assert a["checks"]["reported_tenderers"]["denominator"] == 20
    assert a["checks"]["reported_tenderers"]["result"] == "pass"
    other = tmp_path / "under"
    other.mkdir()
    records[1]["tender"]["numberOfTenderers"] = None
    b = quality.assess(intake(other, records), per_stratum=25)
    assert b["checks"]["reported_tenderers"]["result"] == "fail"
    assert a["analytics"]["status"] == b["analytics"]["status"] == "blocked"


def test_reported_count_difference_is_diagnostic_only():
    r = row(1)
    r["tender"]["numberOfTenderers"] = 9
    a = quality.relation(r)
    assert a["reported_vs_unique_tenderers"] == "different"
    assert a["reported_vs_bid_participants"] == "different"
    assert "irregularity" not in json.dumps(a)


def test_frame_binding_catches_replaced_bytes_and_name(tmp_path):
    out = intake(tmp_path, [row(1)])
    original = next(out.glob("*.raw"))
    data = original.read_bytes().replace(b"SYN-1", b"SYN-2")
    import hashlib

    replacement = out / ("000001-" + hashlib.sha256(data).hexdigest() + ".raw")
    original.unlink()
    replacement.write_bytes(data)
    with pytest.raises(ValueError, match="expanded_frame_hash_mismatch"):
        quality.assess(out)

"""Invented canonical records; no DNCP acquisition."""

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from civictrace.canonical import award_totals, field, normalize, serialize
from civictrace.synthetic import assess_record

PROVENANCE = dict(
    snapshot_sha256="a" * 64,
    record_sha256="b" * 64,
    collected_at="2026-10-28T10:00:00+01:00",
    source_reference="synthetic:canonical/1",
    license="Apache-2.0",
    attribution="Invented organizations only",
    privacy_review="Synthetic; no natural persons",
    adapter_version="synthetic/1",
)


def sample():
    return dict(
        ocid="SYN-PROCESS",
        id="notice-1",
        date="2026-10-28T10:00:00+01:00",
        tender=dict(status="complete", numberOfTenderers=1),
        parties=[dict(id="supplier-a"), dict(id="supplier-b")],
        awards=[
            dict(
                id="award-1",
                status="active",
                value=dict(amount="9007199254740993.01", currency="EUR"),
                suppliers=[dict(id="supplier-a"), dict(id="supplier-b")],
            )
        ],
        contracts=[
            dict(
                id="contract-1",
                awardID="award-1",
                value=dict(amount="9007199254740993.01", currency="EUR"),
            )
        ],
    )


def test_exact_totals_joint_awards_and_contracts_not_double_counted():
    model = normalize([sample()], PROVENANCE)
    assert len(model["award_suppliers"]) == 2
    assert award_totals(model, [model["releases"][0]["id"]]) == dict(
        totals={"EUR": "9007199254740993.01"}, excluded_awards=[], supplier_allocation="unavailable"
    )
    assert model["releases"][0]["bid_count"]["state"] == "absent"


def test_history_cancellation_explicit_selection_and_stable_ids():
    first = sample()
    amended = deepcopy(first)
    amended["id"] = "notice-2"
    amended["awards"][0]["status"] = "cancelled"
    before = deepcopy([first, amended])
    model = normalize(before, PROVENANCE)
    assert before == [first, amended]
    assert serialize(model) == serialize(normalize(list(reversed(before)), PROVENANCE))
    assert model["awards"][0]["id"] == model["awards"][1]["id"]
    selected = next(r["id"] for r in model["releases"] if r["source_id"] == "notice-2")
    assert award_totals(model, [selected])["totals"] == {}
    with pytest.raises(ValueError, match="one version"):
        award_totals(model, [r["id"] for r in model["releases"]])
    assert (
        normalize([first], {**PROVENANCE, "snapshot_sha256": "c" * 64})["releases"][0]["id"]
        != normalize([first], PROVENANCE)["releases"][0]["id"]
    )


def test_integrity_rejects_duplicates_and_dangling_links():
    row = sample()
    with pytest.raises(ValueError, match="duplicate release"):
        normalize([row, row], PROVENANCE)
    for mutation in (
        lambda r: r["contracts"][0].update(awardID="missing"),
        lambda r: r["awards"][0]["suppliers"].append(dict(id="missing")),
        lambda r: r["awards"].append(deepcopy(r["awards"][0])),
        lambda r: r["contracts"][0].pop("id"),
    ):
        changed = deepcopy(row)
        mutation(changed)
        with pytest.raises(ValueError):
            normalize([changed], PROVENANCE)


def test_field_states_boundaries_offsets_and_precision():
    for raw, state in [
        ({}, "absent"),
        ({"x": None}, "null"),
        ({"x": 0}, "present"),
        ({"x": True}, "invalid"),
        ({"x": -1}, "invalid"),
    ]:
        assert field(raw, "x", "/x", "count")["state"] == state
    for amount in [0.1, True, "NaN", "Infinity", "-0.01", "1e10000"]:
        assert field({"x": amount}, "x", "/x", "amount")["state"] == "invalid"
    assert field({"x": "0.00"}, "x", "/x", "amount")["value"] == "0.00"
    assert field({"x": "ZZZ"}, "x", "/x", "currency")["state"] == "unsupported"
    assert (
        field({"x": "2026-10-28T10:00:00+01:00"}, "x", "/x", "date")["value"]
        == "2026-10-28T09:00:00+00:00"
    )
    assert field({"x": "2026-10-28"}, "x", "/x", "date")["state"] == "invalid"
    row = sample()
    row["tender"]["tenderPeriod"] = dict(
        startDate="2026-10-28T10:00:00Z", endDate="2026-10-28T09:00:00Z"
    )
    row["awards"][0]["value"] = None
    model = normalize([row], PROVENANCE)
    assert model["releases"][0]["period_reversed"]
    assert award_totals(model, [model["releases"][0]["id"]])["totals"] == {}


def test_all_37_existing_cases_bridge_count_and_period_states():
    """Reuse fixture facts without treating legacy demo rows as OCDS or inventing bids."""
    path = Path(__file__).resolve().parents[1] / "examples/synthetic_edge_cases.json"
    cases = json.loads(path.read_bytes())["cases"]
    assert len(cases) == 37
    for case in cases:
        for original in case["records"]:
            row = sample()
            tender = row["tender"]
            tender.pop("numberOfTenderers")
            if "reported_tenderer_count" in original:
                tender["numberOfTenderers"] = original["reported_tenderer_count"]
            tender["tenderPeriod"] = {}
            for source, dest in [("tender_start", "startDate"), ("tender_end", "endDate")]:
                if source in original:
                    tender["tenderPeriod"][dest] = original[source]
            raw = json.dumps(original, sort_keys=True).encode()
            model = normalize([row], {**PROVENANCE, "record_sha256": sha256(raw).hexdigest()})
            release = model["releases"][0]
            assert release["bid_count"]["state"] == "absent"
            assert release["source_record"] == row
            assert serialize(model) == serialize(
                normalize([row], {**PROVENANCE, "record_sha256": sha256(raw).hexdigest()})
            )
            try:
                assessed = assess_record(original)
            except ValueError:
                continue
            assert (
                release["reported_tenderer_count"]["state"]
                == assessed["reported_tenderer_count_state"]
            )
            assert (
                release["reported_tenderer_count"]["value"] == assessed["reported_tenderer_count"]
            )


def test_currency_cohorts_exact_addition_unknown_status_and_pointer():
    row = sample()
    extra = deepcopy(row["awards"][0])
    extra.update(id="award-2", value=dict(amount="0.09", currency="EUR"))
    row["awards"].append(extra)
    third = deepcopy(extra)
    third.update(id="award-3", value=dict(amount="12.34", currency="USD"))
    row["awards"].append(third)
    model = normalize([row], PROVENANCE)
    selection = [model["releases"][0]["id"]]
    assert award_totals(model, selection)["totals"] == {
        "EUR": "9007199254740993.10",
        "USD": "12.34",
    }
    assert model["contracts"][0]["date"]["pointer"] == "/contracts/0/dateSigned"
    for status in [None, "cancelled", "pending", "unsuccessful", "unrecognized"]:
        row["tender"]["status"] = status
        model = normalize([row], PROVENANCE)
        result = award_totals(model, [model["releases"][0]["id"]])
        assert result["totals"] == {} and len(result["excluded_awards"]) == 3
    with pytest.raises(ValueError, match="selection"):
        award_totals(model, ["nonexistent"])

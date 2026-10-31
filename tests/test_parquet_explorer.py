"""Static projection regressions against real local synthetic Parquet, no source download."""

import json
from unittest.mock import patch

import pytest
from civictrace.parquet_explorer import MAX_BYTES, export_snapshot
from test_analytics import snapshot
from test_dncp import release


def test_exact_repeatable_missing_zero_and_excluded(tmp_path):
    rows = [release() for _ in range(4)]
    for n, r in enumerate(rows):
        r["ocid"] += str(n)
    rows[1]["awards"][0]["value"]["amount"] = "0"
    rows[1].pop("date", None)
    rows[2]["awards"][0]["value"]["amount"] = None
    rows[3]["awards"][0]["value"]["amount"] = "1e58"
    directory, pin = snapshot(tmp_path, rows)
    raw = export_snapshot(directory, expected_snapshot_id=pin)
    assert raw == export_snapshot(directory, expected_snapshot_id=pin)
    data = json.loads(raw)
    assert len(raw.encode()) < MAX_BYTES
    assert not data["analytics_enabled"] and data["synthetic"]
    assert data["lineage"]["snapshot_id"] == pin
    assert data["lineage"]["artifacts"] and data["lineage"]["original_file_sha256"]
    awards = [r["awards"][0] for r in data["records"]]
    assert "9007199254740993.010000000000000000" in [a["amount"] for a in awards]
    assert "0.000000000000000000" in [a["amount"] for a in awards]
    assert any(a["canonical"]["money"]["amount"]["state"] == "null" for a in awards)
    assert any(a["projection_exclusion"] for a in awards)
    assert any(r["release"]["canonical"]["date"]["state"] == "absent" for r in data["records"])


def test_wrong_pin_and_corruption(tmp_path):
    directory, pin = snapshot(tmp_path)
    with pytest.raises(ValueError):
        export_snapshot(directory, expected_snapshot_id="0" * 64)
    target = next(directory.rglob("*.parquet"))
    target.write_bytes(target.read_bytes() + b"tampered")
    with pytest.raises(ValueError):
        export_snapshot(directory, expected_snapshot_id=pin)


def test_reject_symlink_and_copy_budget(tmp_path):
    directory, pin = snapshot(tmp_path)
    (directory / "link").symlink_to(directory / "manifest.json")
    with pytest.raises(ValueError):
        export_snapshot(directory, expected_snapshot_id=pin)
    (directory / "link").unlink()
    with (directory / "oversize").open("wb") as stream:
        stream.truncate(8 * 1024**2 + 1)
    with pytest.raises(ValueError):
        export_snapshot(directory, expected_snapshot_id=pin)


def test_record_limit(tmp_path):
    rows = [release() for _ in range(101)]
    for n, r in enumerate(rows):
        r["ocid"] += str(n)
    directory, pin = snapshot(tmp_path, rows)
    with pytest.raises(ValueError):
        export_snapshot(directory, expected_snapshot_id=pin)


def test_byte_limit_no_truncation(tmp_path):
    rows = [release() for _ in range(8)]
    for n, r in enumerate(rows):
        r["ocid"] += str(n)
        r["description"] = "".join(
            __import__("hashlib").sha256(str(i).encode()).hexdigest() for i in range(300)
        )
    directory, pin = snapshot(tmp_path, rows)
    with pytest.raises(ValueError):
        export_snapshot(directory, expected_snapshot_id=pin)


def test_bad_pin_and_wall_limit():
    with patch("civictrace.parquet_explorer.subprocess.run") as child:
        with pytest.raises(ValueError):
            export_snapshot("missing", expected_snapshot_id=None)
        child.assert_not_called()
    import subprocess

    with patch(
        "civictrace.parquet_explorer.subprocess.run",
        side_effect=subprocess.TimeoutExpired("worker", 30),
    ):
        with pytest.raises(ValueError, match="wall limit"):
            export_snapshot("missing", expected_snapshot_id="a" * 64)


def test_rejected_source_rows_and_quarantined_children_retained(tmp_path):
    row = release()
    row["contracts"].append({"id": "broken", "awardID": "unknown", "value": {}})
    directory, pin = snapshot(tmp_path, [row, {"bad": "record"}])
    result = json.loads(export_snapshot(directory, expected_snapshot_id=pin))
    assert result["import_summary"]["rejected"] == 1
    assert len(result["records"]) == 1
    assert len(result["exclusion_ledger"]) == 2
    assert result["exclusion_ledger"][0]["quarantined"][0]["reason"] == "contract_linkage"
    assert result["exclusion_ledger"][1]["status"] == "rejected"
    assert result["records"][0]["contracts"][0]["canonical"]["money"]["amount"]["raw"] == "0"


def test_synthetic_gate_with_consistent_rehashed_manifest(tmp_path):
    import hashlib

    from civictrace.canonical import serialize
    from civictrace.snapshots import verify_snapshot

    directory, _ = snapshot(tmp_path)
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["source"]["source_url"] = "https://example.org/unreviewed-real-source"
    manifest.pop("snapshot_id")
    manifest["snapshot_id"] = hashlib.sha256(serialize(manifest).encode()).hexdigest()
    raw = serialize(manifest).encode()
    (directory / "manifest.json").write_bytes(raw)
    (directory / "manifest.sha256").write_text(hashlib.sha256(raw).hexdigest())
    assert verify_snapshot(directory) == manifest
    with pytest.raises(ValueError):
        export_snapshot(directory, expected_snapshot_id=manifest["snapshot_id"])


def test_search_identity_links_and_minimized_unknowns(tmp_path):
    row = release()
    row["buyer"] = {"id": "buyer-1", "name": "Same name", "address": {"secret": True}}
    row["parties"] = [
        {"id": "p1", "name": "Same name"},
        {"id": "p2", "name": "Same name", "roles": ["tenderer"]},
        {"id": "unlinked", "name": "Same name"},
    ]
    row["contracts"][0]["title"] = "Synthetic contract"
    directory, pin = snapshot(tmp_path, [row])
    raw = export_snapshot(directory, expected_snapshot_id=pin)
    assert raw == export_snapshot(directory, expected_snapshot_id=pin)
    result = json.loads(raw)["records"][0]
    search = result["search"]
    assert search["buyers"][0]["source_id"]["value"] == "buyer-1"
    assert {p["source_id"]["value"] for p in search["suppliers"]} == {"p1", "p2"}
    assert search["contracts"][0]["name"]["value"] == "Synthetic contract"
    assert search["contracts"][0]["canonical_id"] == result["contracts"][0]["canonical"]["id"]
    assert "secret" not in raw
    for items in search.values():
        for item in items:
            assert item["record_sha256"] == result["release"]["record_sha256"]
            assert item["source_file"] == result["release"]["source_file"]


@pytest.mark.parametrize("buyer,state", [(None, "null"), ([], "invalid"), ({}, "absent")])
def test_search_missing_buyer_and_contract_title(tmp_path, buyer, state):
    row = release()
    row["buyer"] = buyer
    row["parties"][0]["name"] = None
    directory, pin = snapshot(tmp_path, [row])
    search = json.loads(export_snapshot(directory, expected_snapshot_id=pin))["records"][0][
        "search"
    ]
    assert search["buyers"][0]["source_id"]["state"] == state
    assert search["contracts"][0]["name"]["state"] == "absent"
    assert any(p["name"]["state"] == "null" for p in search["suppliers"])


def test_quarantined_contract_title_never_guessed(tmp_path):
    row = release()
    row["contracts"].insert(0, {"id": "bad", "awardID": "missing", "value": {}})
    row["contracts"][1]["title"] = "Kept title"
    row["contracts"].append(dict(row["contracts"][1], title="Conflicting title"))
    directory, pin = snapshot(tmp_path, [row])
    data = json.loads(export_snapshot(directory, expected_snapshot_id=pin))
    assert data["records"][0]["search"]["contracts"][0]["name"]["state"] == "unsupported"
    assert len(data["exclusion_ledger"][0]["quarantined"]) == 2

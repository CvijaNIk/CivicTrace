"""Invented DNCP-shaped bytes only; no network fixtures."""

import gzip
import hashlib
import json

import pytest
from civictrace.dncp import IntakeError, Limits, import_file


def release():
    return {
        "ocid": "ocds-03ad3f-INVENTED",
        "id": "r1",
        "tag": ["compiled"],
        "date": "2025-01-01T02:00:00+02:00",
        "tender": {"id": "t1", "status": "complete"},
        "parties": [{"id": "p1"}, {"id": "p2"}],
        "awards": [
            {
                "id": "a1",
                "status": "active",
                "value": {"amount": "9007199254740993.01", "currency": "PYG"},
                "suppliers": [{"id": "p1"}, {"id": "p2"}],
            }
        ],
        "contracts": [{"id": "c1", "awardID": "a1", "value": {"amount": 0, "currency": "PYG"}}],
    }


def setup(tmp_path, raw=None, compressed=None):
    raw = raw if raw is not None else (json.dumps(release()) + "\n").encode()
    compressed = compressed if compressed is not None else gzip.compress(raw, mtime=0)
    source = tmp_path / "sample.jsonl.gz"
    source.write_bytes(compressed)
    m = {
        k: "synthetic-example"
        for k in (
            "adapter_version intermediary source_url resolved_url snapshot_version "
            "partition selection "
            "terms_evidence attribution changes exclusions privacy_review registry_unknown_reason"
        ).split()
    }
    m.update(
        contract_version="dncp-local/1",
        publisher="DNCP",
        publication_id="63",
        retrieved_at="2026-01-01T00:00:00Z",
        registry_retrieved_at=None,
        compressed_sha256=hashlib.sha256(compressed).hexdigest(),
        expanded_sha256=hashlib.sha256(raw).hexdigest(),
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        redistribution_decision="local-only",
        access_review="confirmed",
    )
    return source, m


def test_reproducible_mapping(tmp_path):
    src, m = setup(tmp_path)
    for name in ("a", "b"):
        assert import_file(src, tmp_path / name, m)["accepted"] == 1
    a, b = tmp_path / "a", tmp_path / "b"
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {
        p.name: p.read_bytes() for p in b.iterdir()
    }
    model = json.loads(next(a.glob("*.canonical.json")).read_text())
    assert model["awards"][0]["money"]["amount"]["value"] == "9007199254740993.01"
    assert len(model["award_suppliers"]) == 2
    assert model["releases"][0]["bid_count"]["state"] == "absent"
    assert model["releases"][0]["date"]["value"] == "2025-01-01T00:00:00+00:00"
    assert model["contracts"][0]["date"]["state"] == "absent"


@pytest.mark.parametrize("mode", ["garbage", "truncated", "crc", "concat", "trailing"])
def test_bad_gzip(tmp_path, mode):
    data = gzip.compress(b"{}\n", mtime=0)
    bad = {
        "garbage": b"bad",
        "truncated": data[:-1],
        "crc": data[:-8] + b"xxxxxxxx",
        "concat": data + data,
        "trailing": data + b"x",
    }[mode]
    src, m = setup(tmp_path, b"{}\n", bad)
    with pytest.raises(IntakeError):
        import_file(src, tmp_path / "out", m)
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".dncp-*"))


@pytest.mark.parametrize("limit", ["compressed", "expanded", "rows", "line"])
def test_limits(tmp_path, limit):
    src, m = setup(tmp_path, (json.dumps(release()) + "\n").encode() * 2)
    with pytest.raises(IntakeError):
        import_file(src, tmp_path / "out", m, Limits(**{limit: 1}))
    assert not (tmp_path / "out").exists()


def test_rejects_and_quarantine(tmp_path):
    r = release()
    r["contracts"].insert(0, {"value": {"amount": 1}})
    raw = (json.dumps(r) + "\n" + json.dumps(r) + "\n" + '{"ocid":1}\n' + "{bad\n").encode()
    src, m = setup(tmp_path, raw)
    assert import_file(src, tmp_path / "out", m) == {
        "rows": 4,
        "accepted": 1,
        "rejected": 3,
        "compressed_bytes": src.stat().st_size,
        "expanded_bytes": len(raw),
        "limits": vars(Limits()),
    }
    model = json.loads(next((tmp_path / "out").glob("*.canonical.json")).read_text())
    assert model["contracts"][0]["pointer"] == "/contracts/1"
    assert len(model["releases"][0]["source_record"]["contracts"]) == 2


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":1,"x":2}\n',
        b'{"x":NaN}\n',
        b"\xff\n",
        b"[" * 33 + b"]" * 33 + b"\n",
        b'{"n":' + b"9" * 129 + b"}\n",
    ],
)
def test_invalid_json(tmp_path, raw):
    src, m = setup(tmp_path, raw)
    assert import_file(src, tmp_path / "out", m)["rejected"] == 1


def test_hash_and_rights(tmp_path):
    src, m = setup(tmp_path)
    m["expanded_sha256"] = "0" * 64
    with pytest.raises(IntakeError):
        import_file(src, tmp_path / "out", m)
    m["access_review"] = "unknown"
    with pytest.raises(IntakeError):
        import_file(src, tmp_path / "out", m)


def test_symlink(tmp_path):
    src, m = setup(tmp_path)
    link = tmp_path / "link.jsonl.gz"
    link.symlink_to(src)
    with pytest.raises(OSError):
        import_file(link, tmp_path / "out", m)


def test_exact_boundaries(tmp_path):
    raw = (json.dumps(release()) + "\n").encode()
    src, m = setup(tmp_path, raw)
    limits = Limits(compressed=src.stat().st_size, expanded=len(raw), line=len(raw), rows=1)
    assert import_file(src, tmp_path / "out", m, limits)["accepted"] == 1


def test_ratio_and_depth_limits(tmp_path):
    src, m = setup(tmp_path, b" " * 10000)
    with pytest.raises(IntakeError):
        import_file(src, tmp_path / "out", m, Limits(ratio=1))
    with pytest.raises(IntakeError):
        import_file(src, tmp_path / "out", m, Limits(depth=33))


def test_streaming_memory(tmp_path):
    import tracemalloc

    records = []
    for i in range(2000):
        r = release()
        r["ocid"] += hashlib.sha256(str(i).encode()).hexdigest()
        records.append(json.dumps(r) + "\n")
    src, m = setup(tmp_path, "".join(records).encode())
    tracemalloc.start()
    import_file(src, tmp_path / "out", m)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 16 * 1024 * 1024

"""Resource harness contracts; performance values are observations, never CI thresholds."""

import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_dncp import Case, cases, generate, line, run_case  # noqa: E402
from civictrace.dncp import Limits, import_file  # noqa: E402


def test_generator_deterministic_stream(tmp_path):
    case = Case("invented", 7, 10000)
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    assert generate(a, case) == generate(b, case)
    assert (a / "synthetic.jsonl.gz").read_bytes() == (b / "synthetic.jsonl.gz").read_bytes()
    raw = gzip.decompress((a / "synthetic.jsonl.gz").read_bytes())
    assert len(raw) == 70000
    assert len({json.loads(r)["ocid"] for r in raw.splitlines()}) == 7
    assert all(len(line(case, i)) == 10000 for i in range(7))
    assert b"SYNTHETIC" in raw and b"INVENTED" in raw


@pytest.mark.parametrize("mode", ["valid", "missing", "malformed", "corrupt"])
def test_worker_results(tmp_path, mode):
    error = "invalid_gzip" if mode == "corrupt" else None
    result = run_case(tmp_path / "run", Case(mode, 3, mode=mode, expected_error=error))
    assert len(result["measurements"]) == 2
    for m in result["measurements"]:
        assert m["elapsed_seconds"] > 0
        assert m["rss_hwm_bytes"] >= m["rss_baseline_bytes"] > 0
        assert (m["python_peak_bytes"] is not None) == m["traced"]
        assert m["disk_output_high_water"]["files"] > 0
        assert m["disk_output_high_water"]["allocated_bytes"] > 0
        assert not m["private_orphans"]
        assert m["published"] == (error is None)
        assert m["throughput_is_complete_import"] == m["published"]


def test_missing_values_remain_unknown(tmp_path):
    generate(tmp_path, Case("missing", 1, mode="missing"))
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    summary = import_file(tmp_path / "synthetic.jsonl.gz", tmp_path / "out", manifest)
    assert summary["accepted"] == 1
    model = json.loads(next((tmp_path / "out").glob("*.canonical.json")).read_text())
    assert model["releases"][0]["date"]["state"] == "absent"
    assert not model["awards"]
    assert model["intake"]["quarantined"][0]["reason"] == "child_value"


def test_suite_has_independent_hard_boundaries():
    full = {c.name: c for c in cases(True)}
    assert full["unique-row-boundary"].rows == Limits().rows
    assert full["row-overflow"].rows == Limits().rows + 1
    assert full["long-line-boundary"].width == Limits().line
    assert full["long-line-overflow"].width == Limits().line + 1
    assert full["expanded-boundary"].width * full["expanded-boundary"].rows == Limits().expanded
    assert full["expanded-overflow"].width * full["expanded-overflow"].rows > Limits().expanded
    assert {"compressed-boundary", "compressed-overflow"} <= full.keys()


def test_harness_refuses_wrong_expectation(tmp_path):
    with pytest.raises(RuntimeError, match="unexpected result"):
        run_case(tmp_path / "run", Case("wrong", 1, expected_error="row_limit"))


def test_line_overflow_and_cleanup(tmp_path):
    result = run_case(
        tmp_path / "run", Case("line-overflow", 1, Limits().line + 1, expected_error="line_limit")
    )
    assert all(not m["published"] for m in result["measurements"])


def test_exact_compressed_header_padding(tmp_path):
    from benchmark_dncp import pad_gzip_header

    generate(tmp_path, Case("header", 1))
    source = tmp_path / "synthetic.jsonl.gz"
    raw = gzip.decompress(source.read_bytes())
    target = source.stat().st_size + 70000
    pad_gzip_header(source, target)
    assert source.stat().st_size == target
    assert gzip.decompress(source.read_bytes()) == raw
    with pytest.raises(ValueError, match="too_large"):
        pad_gzip_header(source, 1)


def test_fanout_is_bounded_but_structurally_dense():
    raw = line(Case("dense", 1, mode="fanout"), 0)
    assert len(raw) < Limits().line
    assert len(json.loads(raw)["awards"]) == 4000


def test_expanded_boundary_recipe_does_not_hit_other_ceilings_first():
    # One maximum-size row is enough to catch a poorly compressing full recipe,
    # without a multi-GiB fixture in ordinary CI.
    case = next(c for c in cases(True) if c.name == "expanded-boundary")
    raw = line(case, 0)
    compressed_size = len(gzip.compress(raw, compresslevel=case.compression, mtime=0))
    assert compressed_size * case.rows < Limits().compressed
    assert len(raw) < compressed_size * Limits().ratio

"""Offline provenance replay for five reviewed synthetic records and two demo findings."""

import argparse
import json
from pathlib import Path

from civictrace.lineage import fixture_passports, verify_fixture_passports

ROOT = Path(__file__).resolve().parents[1]
PIN = "bb30164c2944433984b29855a5416be52e640fd94a48916ef9327ed9697bcef2"
TIME = "2026-10-10T00:00:00Z"  # asserted demo time, not an authenticated acquisition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New private JSON bundle, never overwritten")
    args = parser.parse_args()
    raw = (ROOT / "examples/synthetic_procurement.json").read_bytes()
    kwargs = dict(expected_sha256=PIN, collected_at=TIME)
    passports = fixture_passports(raw, **kwargs)
    assert passports == fixture_passports(raw, **kwargs)
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(passports, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
    print(json.dumps(verify_fixture_passports(passports, raw, **kwargs), sort_keys=True))


if __name__ == "__main__":
    main()

"""Regenerate the compiled synthetic finding preview; never accepts external input."""

import argparse
import json
from pathlib import Path

from civictrace.evidence import single_bid_findings
from civictrace.lineage import fixture_passports, migrate_passport, verify_fixture_passports
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
PIN = "bb30164c2944433984b29855a5416be52e640fd94a48916ef9327ed9697bcef2"
TIME = "2026-10-10T00:00:00Z"


def example():
    raw = (ROOT / "examples/synthetic_procurement.json").read_bytes()
    bundle = fixture_passports(raw, expected_sha256=PIN, collected_at=TIME)
    verify_fixture_passports(bundle, raw, expected_sha256=PIN, collected_at=TIME)
    legacy = single_bid_findings(json.loads(raw), snapshot_hash=PIN, collected_at=TIME)[0]
    findings = [legacy, migrate_passport(legacy)] + [
        row["result"] for row in bundle if row["result_kind"] == "finding"
    ]
    for finding in findings:
        schema = json.loads(
            (
                ROOT / f"schemas/evidence-passport-{finding['schema_version']}.schema.json"
            ).read_text()
        )
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(finding)
    return dict(synthetic=True, analytics_enabled=False, findings=findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "frontend/src/passport-example.json"
    current = example()
    if args.check:
        saved = json.loads(path.read_text())
        # Verification-time environment is host-dependent; all other evidence is exact.
        for data in (current, saved):
            for finding in data["findings"]:
                if finding.get("lineage", {}).get("environment") is not None:
                    finding["lineage"]["environment"] = None
        if current != saved:
            raise SystemExit("Synthetic finding example differs; review and regenerate")
    else:
        path.write_text(json.dumps(current, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print("4 synthetic previews: legacy, migrated-incomplete, 2 complete; analytics_enabled: false")


if __name__ == "__main__":
    main()

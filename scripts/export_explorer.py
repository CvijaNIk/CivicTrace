"""Export only the reviewed five-row invented fixture; never accepts an input path."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from civictrace.evidence import validate_record

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "frontend/public/data/synthetic-v1.json"


def export():
    raw = (ROOT / "examples/synthetic_procurement.json").read_bytes()
    if sha256(raw).hexdigest() != (
        "bb30164c2944433984b29855a5416be52e640fd94a48916ef9327ed9697bcef2"
    ):
        raise ValueError("fixture changed; review synthetic content and update the trusted pin")
    records = json.loads(raw)
    if len(records) != 5:
        raise ValueError("review fixture changes before exporting")
    for index, record in enumerate(records, 1):
        validate_record(record)
        identity = f"SYN-{index:03d}"
        if record["record_id"] != identity or record["source_reference"] != f"synthetic:{identity}":
            raise ValueError("only reviewed synthetic identities may be exported")
    result = {
        "schema_version": "civictrace-explorer/1",
        "synthetic": True,
        "analytics_enabled": False,
        "source": {
            "name": "CivicTrace invented procurement fixture",
            "path": "examples/synthetic_procurement.json",
            "sha256": sha256(raw).hexdigest(),
            "license": "Apache-2.0",
            "attribution": "CivicTrace contributors; invented organizations only",
            "privacy_review": "Synthetic fixture; no natural persons or client data",
        },
        "limitations": [
            "Invented examples, not evidence about real procurement or wrongdoing.",
            "Reported bid counts only; missing values are unknown, never zero.",
            "No dates, amounts, procedure status, lots or source-authentication evidence supplied.",
            "No production indicators, risk scores, live queries or DuckDB execution "
            "in the browser.",
        ],
        "records": [
            {
                **{
                    key: row[key]
                    for key in (
                        "record_id",
                        "buyer_id",
                        "supplier_id",
                        "source_reference",
                        "bid_count",
                    )
                },
                "data_status": "missing" if row["bid_count"] is None else "reported",
            }
            for row in records
        ],
    }
    return json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = export()
    if args.check:
        if TARGET.read_text() != text:
            raise SystemExit("Explorer fixture is stale; run scripts/export_explorer.py")
    else:
        TARGET.write_text(text)


if __name__ == "__main__":
    main()

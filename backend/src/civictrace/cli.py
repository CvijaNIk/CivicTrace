"""Explicit local-file input/output; never fetches or uploads data."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from .evidence import serialize_findings, single_bid_findings


def main():
    parser = argparse.ArgumentParser(description="CivicTrace synthetic procurement demo")
    parser.add_argument("input", type=Path, help="Synthetic procurement JSON array")
    parser.add_argument("--collected-at", required=True, help="ISO 8601 timestamp with timezone")
    parser.add_argument("--output", type=Path, required=True, help="New local output file")
    args = parser.parse_args()
    raw = args.input.read_bytes()
    records = json.loads(raw)
    if not isinstance(records, list):
        parser.error("input must be a JSON array")
    try:
        findings = single_bid_findings(
            records, snapshot_hash=sha256(raw).hexdigest(), collected_at=args.collected_at
        )
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    with args.output.open("x", encoding="utf-8") as output:
        output.write(serialize_findings(findings))
    print(f"Wrote {len(findings)} synthetic indicators to {args.output}")


if __name__ == "__main__":
    main()

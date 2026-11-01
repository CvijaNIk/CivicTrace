"""Compile only the pinned invented report using the existing calculation and integrity gate."""

import argparse
import json
from pathlib import Path

from civictrace.submission_period import digest, encoded, report

ROOT = Path(__file__).resolve().parents[1]


def artifacts():
    raw = (ROOT / "examples/synthetic_submission_period.json").read_bytes()
    config = (ROOT / "examples/synthetic_submission_benchmarks.json").read_bytes()
    payload = encoded(report(raw, config))
    if len(payload) > 65536:
        raise ValueError("preview exceeds existing 64 KiB loader bound")
    return {
        ROOT / "frontend/public/data/submission-period-v1.json": payload,
        ROOT / "frontend/src/submission-pin.json": encoded({"sha256": digest(payload)}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, payload in artifacts().items():
        if args.check:
            if path.read_bytes() != payload:
                raise SystemExit(f"Synthetic report differs: {path.name}; review and regenerate")
        else:
            path.write_bytes(payload)
    print(json.dumps({"records": 10, "synthetic": True, "analytics_enabled": False}))


if __name__ == "__main__":
    main()

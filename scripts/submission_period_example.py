"""Print a deterministic, synthetic-only report; accept no source/population argument."""

import argparse
from pathlib import Path

from civictrace.submission_period import encoded, report

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "examples/synthetic_submission_benchmarks.json"
    )
    args = parser.parse_args()
    # Bound the read, including a sentinel byte, before parsing a custom configuration.
    with args.config.open("rb") as stream:
        config = stream.read(65537)
    raw = (ROOT / "examples/synthetic_submission_period.json").read_bytes()
    print(encoded(report(raw, config)).decode(), end="")


if __name__ == "__main__":
    main()

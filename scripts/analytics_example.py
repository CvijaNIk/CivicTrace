"""Create three invented records via the existing snapshot example, check exact diagnostics."""

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

from civictrace.analytics import Cohort, query_snapshot
from civictrace.snapshots import verify_snapshot


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/analytics_example.py NEW_PRIVATE_DIRECTORY")
    directory = Path(sys.argv[1])
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("snapshot_example.py")),
            str(directory),
            "--rows",
            "3",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    snapshot = directory / "snapshot-a"
    # This pin is trusted here only because this script just generated the reviewed fixture.
    identity = verify_snapshot(snapshot)["snapshot_id"]
    cohort = Cohort("PYG", "2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z", "complete")
    result = query_snapshot(snapshot, expected_snapshot_id=identity, cohort=cohort)
    assert query_snapshot(snapshot, expected_snapshot_id=identity, cohort=cohort) == result
    assert result["included_rows"] == 3 and result["excluded_rows"] == 0
    assert Decimal(result["exact_amount_sum"]) == Decimal("27021597764222979.03")
    assert result["analytics_enabled"] is False
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

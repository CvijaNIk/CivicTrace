"""Reproducible invented local snapshot and resource measurement; no network access."""

import argparse
import gzip
import hashlib
import json
import resource
import time
from pathlib import Path

from civictrace.dncp import OutputBudget, import_file
from civictrace.snapshots import build_snapshot, verify_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New private output directory")
    parser.add_argument("--rows", type=int, default=100)
    parser.add_argument(
        "--preview-fixture", action="store_true", help="Invented zero/missing/excluded cases"
    )
    args = parser.parse_args()
    if not 1 <= args.rows <= 10000:
        parser.error("rows must be 1..10000")
    args.directory.mkdir(mode=0o700)
    source = args.directory / "invented.jsonl.gz"
    expanded = hashlib.sha256()
    with (
        source.open("xb") as stream,
        gzip.GzipFile(fileobj=stream, mode="wb", mtime=0, filename="") as gz,
    ):
        for n in range(args.rows):
            record = {
                "ocid": f"ocds-03ad3f-SYN-{n:06d}",
                "id": "compiled-1",
                "tag": ["compiled"],
                "date": "2026-01-01T01:00:00+01:00",
                "tender": {"id": f"SYN-{n}", "status": "complete"},
                "parties": [{"id": "SYN-SUPPLIER"}],
                "awards": [
                    {
                        "id": "SYN-AWARD",
                        "status": "active",
                        "value": {"amount": "9007199254740993.01", "currency": "PYG"},
                        "suppliers": [{"id": "SYN-SUPPLIER"}],
                    }
                ],
                "contracts": [
                    {
                        "id": "SYN-CONTRACT",
                        "awardID": "SYN-AWARD",
                        "value": {"amount": "0.000000000000000001", "currency": "PYG"},
                    }
                ],
            }
            if args.preview_fixture:
                if n != 2:
                    record["buyer"] = {"id": f"SYN-BUYER-{n}", "name": "Invented Council"}
                    record["parties"].append(dict(record["buyer"], roles=["buyer"]))
                    record["parties"][0].update(
                        id=f"SYN-SUPPLIER-{n}", name="Invented Works", roles=["supplier"]
                    )
                    record["awards"][0]["suppliers"][0]["id"] = f"SYN-SUPPLIER-{n}"
                    record["contracts"][0].update(
                        id=f"SYN-CONTRACT-{n}", title="Invented maintenance"
                    )
                else:
                    record["buyer"] = None
                    record["parties"][0]["name"] = None
                if n == 1:
                    record.pop("date")
                    record["tender"]["status"] = "cancelled"
                    record["awards"][0]["value"] = {"amount": "0", "currency": "USD"}
                elif n == 2:
                    record["awards"][0]["value"] = {"amount": None}
                elif n == 3:
                    record["awards"][0]["value"]["amount"] = "1e58"
            raw = (json.dumps(record, sort_keys=True) + "\n").encode()
            expanded.update(raw)
            gz.write(raw)
    manifest = {
        k: "synthetic-only"
        for k in (
            "adapter_version intermediary source_url resolved_url snapshot_version "
            "partition selection "
            "terms_evidence attribution changes exclusions privacy_review registry_unknown_reason"
        ).split()
    }
    manifest.update(
        contract_version="dncp-local/1",
        publisher="DNCP",
        publication_id="63",
        retrieved_at="2026-01-01T00:00:00Z",
        registry_retrieved_at=None,
        compressed_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        expanded_sha256=expanded.hexdigest(),
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        redistribution_decision="local-only",
        access_review="confirmed",
    )
    budget = OutputBudget(max_bytes=1024**3, max_files=100000)
    intake = args.directory / "intake"
    import_file(source, intake, manifest, budget=budget)
    started = time.monotonic()
    first = build_snapshot(intake, args.directory / "snapshot-a", budget=budget)
    elapsed = time.monotonic() - started
    second = build_snapshot(intake, args.directory / "snapshot-b", budget=budget)
    assert first == second
    assert verify_snapshot(args.directory / "snapshot-a") == first
    files = list((args.directory / "snapshot-a").rglob("*"))
    print(
        json.dumps(
            {
                "synthetic_rows": args.rows,
                "snapshot_id": first["snapshot_id"],
                "replay_identical": True,
                "analytics_enabled": False,
                "tables": first["tables"],
                "snapshot_seconds": round(elapsed, 3),
                "process_peak_rss_kib_linux": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "logical_bytes": sum(p.stat().st_size for p in files if p.is_file()),
                "allocated_bytes": sum(p.stat().st_blocks * 512 for p in files),
                "files": sum(p.is_file() for p in files),
                "directories": sum(p.is_dir() for p in files),
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

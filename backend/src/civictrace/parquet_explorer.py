"""Versioned offline projection; no browser database or analytical indicators."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .analytics import QueryBudget
from .canonical import field

VERSION = "civictrace-parquet-explorer/2"
MAX_BYTES = 65536
MAX_RECORDS = 100
BUDGET = QueryBudget(max_files=1000, max_bytes=8 * 1024**2, max_rows=1000, wall_seconds=30)


def search_projection(release, parties, links, contracts):
    """Project only replay-verified canonical evidence; never resolve entities by name."""
    c = release["canonical"]
    source = c["source_record"]

    def item(obj, pointer, evidence, canonical_id=None, pointer_scope="release_source_record"):
        # No raw object/addresses/contacts exposed by this minimized projection.
        def minimized(key):
            value = field(obj, key, pointer + "/" + key)
            return {k: value[k] for k in ("state", "value", "pointer")}

        return dict(
            source_id=minimized("id"),
            name=minimized("name"),
            pointer=pointer,
            pointer_scope=pointer_scope,
            canonical_id=canonical_id,
            source_file=evidence["source_file"],
            record_sha256=evidence["record_sha256"],
        )

    buyer = source.get("buyer")
    buyers = [item(buyer if isinstance(buyer, dict) else {}, "/buyer", release)]
    if "buyer" in source and not isinstance(buyer, dict):
        state = "null" if buyer is None else "invalid"
        for key in ("source_id", "name"):
            buyers[0][key] = dict(state=state, value=None)
    suppliers = []
    linked = {r["canonical"]["party_id"] for r in links}
    for party in parties:
        pc = party["canonical"]
        roles = pc["source"].get("roles", [])
        if pc["id"] in linked or (
            isinstance(roles, list) and any(r in ("supplier", "tenderer") for r in roles)
        ):
            # Canonical party source is preserved independently of quarantined children.
            suppliers.append(item(pc["source"], "/source", party, pc["id"], "party_canonical"))
    projected_contracts = []
    originals = source.get("contracts", [])
    for contract in contracts:
        cc = contract["canonical"]
        matches = [
            (i, r)
            for i, r in enumerate(originals)
            if isinstance(r, dict) and r.get("id") == cc["source_id"]
        ]
        entry = item({"id": cc["source_id"]}, "/", contract, cc["id"], "contract_canonical")
        entry["source_id"]["pointer"] = "/source_id"
        if len(matches) == 1:
            i, original = matches[0]
            entry["pointer"] = f"/contracts/{i}"
            entry["pointer_scope"] = "release_source_record"
            entry["source_id"]["pointer"] = f"/contracts/{i}/id"
            title = field(original, "title", f"/contracts/{i}/title")
            entry["name"] = {k: title[k] for k in ("state", "value", "pointer")}
        elif len(matches) > 1:
            entry["name"] = dict(state="unsupported", value=None)
        projected_contracts.append(entry)
    return dict(buyers=buyers, suppliers=suppliers, contracts=projected_contracts)


def export_snapshot(directory, *, expected_snapshot_id):
    """Require an operator-reviewed synthetic pin. Fail closed instead of truncating."""
    if not isinstance(expected_snapshot_id, str) or not re.fullmatch(
        r"[a-f0-9]{64}", expected_snapshot_id
    ):
        raise ValueError("independent snapshot pin required")
    with tempfile.TemporaryDirectory(prefix="civictrace-preview-") as private:
        request = dict(
            directory=str(Path(directory).absolute()),
            private=private,
            snapshot_id=expected_snapshot_id,
        )
        try:
            child = subprocess.run(
                [sys.executable, "-m", "civictrace.parquet_explorer"],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                timeout=30,
                env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", TMPDIR=private),
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("preview wall limit") from exc
    if child.returncode or len(child.stdout.encode()) > MAX_BYTES:
        raise ValueError("preview rejected: integrity, synthetic or resource boundary")
    return child.stdout


def _worker(request):
    import resource

    from .analytics import _copy_snapshot, _deny_network, _load_tables

    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_FSIZE, (BUDGET.max_bytes, BUDGET.max_bytes))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    _deny_network()
    import pyarrow.parquet as pq

    from .lineage import snapshot_record_lineage
    from .snapshots import verify_snapshot

    private = Path(request["private"])
    _copy_snapshot(request["directory"], private, BUDGET)
    manifest = verify_snapshot(private)
    if manifest["snapshot_id"] != request["snapshot_id"]:
        raise ValueError("snapshot pin mismatch")
    # Validate all six existing schemas/counts and the total row budget before replay.
    _load_tables(private, manifest, BUDGET)
    if manifest["tables"]["releases"] > MAX_RECORDS:
        raise ValueError("preview record limit")
    # Reuse full importer/writer replay, original hashes, rights and pointers from #38.
    lineage = snapshot_record_lineage(private, expected_snapshot_id=request["snapshot_id"])
    tables = {
        name: [] for name in ("releases", "awards", "contracts", "parties", "award_suppliers")
    }
    for entry in manifest["files"]:
        parts = Path(entry["path"]).parts
        if entry["path"].endswith(".parquet") and parts[1] in tables:
            table = parts[1]
            for batch in pq.ParquetFile(private / entry["path"]).iter_batches(
                batch_size=100,
                columns=[
                    "canonical_json",
                    "record_sha256",
                    "source_file",
                    "amount",
                    "projection_exclusion",
                ],
                use_threads=False,
            ):
                for row in batch.to_pylist():
                    canonical = json.loads(row.pop("canonical_json"))
                    if "money" in canonical:
                        raw_amount = canonical["money"]["amount"].get("raw")
                        if raw_amount is not None:
                            canonical["money"]["amount"]["raw"] = str(raw_amount)
                    row["amount"] = (
                        format(row["amount"], "f") if row["amount"] is not None else None
                    )
                    tables[table].append(dict(canonical=canonical, **row))
    records = []
    for release in sorted(tables["releases"], key=lambda r: r["canonical"]["id"]):
        canonical = release["canonical"]
        children = {}
        for table in ("awards", "contracts"):
            children[table] = sorted(
                [
                    r
                    for r in tables[table]
                    if r["canonical"]["release_id"] == canonical["id"]
                    and r["canonical"]["process_id"] == canonical["process_id"]
                ],
                key=lambda r: r["canonical"]["id"],
            )

        def scoped(table):
            return [
                r
                for r in tables[table]
                if r["canonical"]["release_id"] == canonical["id"]
                and r["canonical"]["process_id"] == canonical["process_id"]
            ]

        search = search_projection(
            release, scoped("parties"), scoped("award_suppliers"), children["contracts"]
        )
        canonical["source_record"] = {k: canonical["source_record"][k] for k in ("ocid", "id")}
        records.append(dict(release=release, search=search, **children))
    result = dict(
        schema_version=VERSION,
        synthetic=True,
        analytics_enabled=False,
        snapshot_id=manifest["snapshot_id"],
        snapshot_version=manifest["snapshot_version"],
        canonical_schema_version=manifest["canonical_schema_version"],
        lineage=lineage,
        import_summary=manifest["import_summary"],
        validation_field_states=manifest["validation_field_states"],
        quality_gate=manifest["quality_gate"],
        projection_exclusions=manifest["projection_exclusions"],
        exclusion_ledger=[
            json.loads(line)
            for line in (private / "evidence/validation.jsonl").read_text().splitlines()
        ],
        records=records,
        limitations=[
            "Invented records only; no real analytical indicators or risk scores.",
            "All imported release versions; no latest-version inference, totals or FX.",
            "Missing, null, invalid and unsupported states remain explicit.",
            "Projection exclusions are retained; importer rejections remain in summary.",
            "Checksums and replay prove consistency, not source truth or publication rights.",
        ],
    )
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if len(raw.encode()) > MAX_BYTES:
        raise ValueError("preview byte limit; no silent truncation")
    return raw


if __name__ == "__main__":
    sys.stdout.write(_worker(json.loads(sys.stdin.read(65536))))

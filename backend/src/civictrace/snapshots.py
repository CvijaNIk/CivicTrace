"""Local immutable Parquet projections of verified DNCP evidence; never enables analytics."""

import argparse
import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
from dataclasses import asdict
from decimal import Decimal, localcontext
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .canonical import SCHEMA_VERSION, serialize
from .dncp import (
    IntakeError,
    Limits,
    OutputBudget,
    _destination,
    _publisher,
    _ResourceGuard,
    import_file,
)
from .synthetic import instant

VERSION = "civictrace-parquet/1"
TABLES = ("processes", "releases", "parties", "awards", "contracts", "award_suppliers")
MAX_METADATA = 32 * 1024 * 1024
MAX_MODEL = 64 * 1024 * 1024
MAX_FILES = 400_000
SCHEMA = pa.schema(
    [
        (k, pa.string())
        for k in (
            "id",
            "ocid",
            "process_id",
            "release_id",
            "source_id",
            "award_id",
            "party_id",
            "status",
            "currency",
            "amount_state",
            "currency_state",
            "date_state",
            "projection_exclusion",
            "record_sha256",
            "source_file",
            "canonical_json",
        )
    ]
    + [("date", pa.timestamp("us", tz="UTC")), ("amount", pa.decimal256(76, 18))],
    metadata={b"snapshot_schema": VERSION.encode(), b"canonical_schema": SCHEMA_VERSION.encode()},
)


class _BudgetSink(io.RawIOBase):
    """Check every Arrow write before disk allocation; no whole-Parquet memory buffer."""

    def __init__(self, stream, guard):
        self.stream, self.guard = stream, guard

    def writable(self):
        return True

    def tell(self):
        return self.stream.tell()

    def write(self, data):
        self.guard.write_chunk(self.stream, data)
        return len(data)


def digest(path):
    h = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise IntakeError("regular_file_required")
        while chunk := stream.read(65536):
            h.update(chunk)
    return h.hexdigest()


def read_bytes(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise IntakeError("regular_file_required")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise IntakeError("metadata_limit")
    return raw


def read_json(path, limit=MAX_METADATA):
    return json.loads(read_bytes(path, limit))


def inventory(root):
    result = []
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(parent) / name
            mode = path.lstat().st_mode
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise IntakeError("unsafe_snapshot_entry")
        for name in files:
            path = Path(parent) / name
            result.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": digest(path),
                }
            )
            if len(result) > MAX_FILES:
                raise IntakeError("inventory_file_limit")
    return sorted(result, key=lambda x: x["path"])


def projection(row, provenance, source_file):
    result = {
        k: row.get(k)
        for k in ("id", "ocid", "process_id", "release_id", "source_id", "award_id", "party_id")
    }
    result.update(
        record_sha256=provenance["record_sha256"],
        source_file=source_file,
        canonical_json=serialize(row).strip(),
    )
    date = row.get("date", {})
    result["date_state"] = date.get("state")
    result["date"] = instant(date["value"]) if date.get("state") == "present" else None
    result["status"] = row.get("status", {}).get("value")
    money = row.get("money", {})
    amount, currency = money.get("amount", {}), money.get("currency", {})
    result.update(
        amount_state=amount.get("state"),
        currency_state=currency.get("state"),
        currency=currency.get("value"),
        amount=None,
        projection_exclusion=None,
    )
    if amount.get("state") == "present":
        value = Decimal(amount["value"])
        with localcontext() as ctx:
            ctx.prec = 512
            # No rounding, float conversion or implicit currency conversion is permitted.
            if value < Decimal(10) ** 58 and value == value.quantize(Decimal("1e-18")):
                result["amount"] = value
            else:
                result["projection_exclusion"] = "amount_outside_decimal256_76_18"
    return result


def _sync_tree(root):
    # Closed writers followed by file + directory fsync, before the atomic rename.
    for parent, dirs, files in os.walk(root, topdown=False):
        for name in files:
            fd = os.open(Path(parent) / name, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def build_snapshot(intake, output, *, budget):
    """Replay the bounded importer, verify every evidence byte, project one model at a time.

    Parent directories must be operator-controlled. A killed process can leave private
    .parquet-* staging; it cannot expose a partial final snapshot. Linux no-replace only.
    """
    if (
        not isinstance(budget, OutputBudget)
        or any(type(v) is not int for v in asdict(budget).values())
        or budget.max_bytes < 1
        or not 1 <= budget.max_files <= MAX_FILES
        or min(budget.min_free_bytes, budget.min_free_inodes) < 0
    ):
        raise IntakeError("invalid_snapshot_budget")
    intake = Path(os.path.abspath(intake))
    for component in (intake, *intake.parents):
        if not stat.S_ISDIR(component.lstat().st_mode):
            raise IntakeError("unsafe_intake_directory")
    output = _destination(output)
    publish = _publisher()
    source_manifest = read_json(intake / "manifest.json", 65536)
    summary = read_json(intake / "summary.json", 65536)
    limits = Limits(**summary["limits"])
    stage = Path(tempfile.mkdtemp(prefix=".parquet-", dir=output.parent))
    try:
        evidence = stage / "evidence"
        import_file(intake / "source.jsonl.gz", evidence, source_manifest, limits, budget=budget)
        # Replay checks compressed/expanded hashes, identity rules, quarantine and field states.
        # Comparing the full inventory also detects canonical/report/summary tampering.
        evidence_inventory = inventory(evidence)
        if evidence_inventory != inventory(intake):
            raise IntakeError("intake_replay_mismatch")
        guard = _ResourceGuard(stage, budget)
        for entry in evidence_inventory:
            guard.reserve(entry["bytes"], 1)
            guard.wrote(entry["bytes"], 1)
        guard.write_file(stage / "schema.arrow", SCHEMA.serialize().to_pybytes())
        counts = dict.fromkeys(TABLES, 0)
        projection_exclusions = 0
        validation_counts = {}
        for path in sorted(evidence.glob("*.canonical.json")):
            model = read_json(path, MAX_MODEL)
            if model["schema_version"] != SCHEMA_VERSION:
                raise IntakeError("canonical_schema_version")
            provenance = model["releases"][0]["provenance"]
            date = model["releases"][0]["date"]
            year = str(instant(date["value"]).year) if date["state"] == "present" else "unknown"
            # Only year and fixed table names enter paths; unknown dates remain explicit.
            for table in TABLES:
                if not model[table]:
                    continue
                rows = [projection(row, provenance, path.name) for row in model[table]]
                projection_exclusions += sum(r["projection_exclusion"] is not None for r in rows)
                target = stage / "tables" / table / f"release_year={year}"
                target.mkdir(parents=True, exist_ok=True, mode=0o700)
                guard.reserve(add_files=1)
                with (target / (path.name.removesuffix(".canonical.json") + ".parquet")).open(
                    "xb"
                ) as f:
                    guard.wrote(add_files=1)
                    sink = _BudgetSink(f, guard)
                    pq.write_table(
                        pa.Table.from_pylist(rows, schema=SCHEMA),
                        sink,
                        compression="NONE",
                        use_dictionary=False,
                        write_statistics=True,
                        version="2.6",
                        row_group_size=4096,
                    )
                counts[table] += len(rows)
        with (evidence / "validation.jsonl").open() as report:
            for line in report:
                record = json.loads(line)
                for field in record.get("fields", []):
                    state = field["state"]
                    validation_counts[state] = validation_counts.get(state, 0) + 1
        manifest = {
            "snapshot_version": VERSION,
            "canonical_schema_version": SCHEMA_VERSION,
            "arrow_schema": "schema.arrow",
            "writer": {"pyarrow": pa.__version__, "compression": "NONE", "parquet": "2.6"},
            "source": source_manifest,
            "import_summary": summary,
            "selection": "all imported versions; no latest selection or analytical cohort",
            "partitions": {"key": "release_year", "basis": "UTC release date", "null": "unknown"},
            "tables": counts,
            "validation_field_states": validation_counts,
            "projection_exclusions": projection_exclusions,
            "exclusion_ledger": "evidence/validation.jsonl plus per-row projection_exclusion",
            "analytics_enabled": False,
            "quality_gate": "DNCP semantics/population unconfirmed",
            "limits": asdict(budget),
            "files": inventory(stage),
        }
        payload = serialize(manifest).encode()
        manifest["snapshot_id"] = hashlib.sha256(payload).hexdigest()
        encoded = serialize(manifest).encode()
        if len(encoded) > MAX_METADATA:
            raise IntakeError("manifest_limit")
        guard.write_file(stage / "manifest.json", encoded)
        guard.write_file(stage / "manifest.sha256", hashlib.sha256(encoded).hexdigest().encode())
        verify_snapshot(stage)
        _sync_tree(stage)
        publish(stage, output)
        stage = None
        fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return manifest
    finally:
        if stage is not None:
            shutil.rmtree(stage)


def verify_snapshot(directory):
    """Verify inventory and manifest identity. Hashes detect corruption, not authenticity."""
    directory = Path(directory)
    manifest = read_json(directory / "manifest.json")
    if (
        manifest.get("snapshot_version") != VERSION
        or manifest.get("canonical_schema_version") != SCHEMA_VERSION
        or manifest.get("analytics_enabled") is not False
    ):
        raise IntakeError("snapshot_contract")
    if (
        read_bytes(directory / "manifest.sha256", 64)
        != digest(directory / "manifest.json").encode()
    ):
        raise IntakeError("manifest_hash")
    identity = dict(manifest)
    snapshot_id = identity.pop("snapshot_id")
    if hashlib.sha256(serialize(identity).encode()).hexdigest() != snapshot_id:
        raise IntakeError("snapshot_identity")
    actual = [
        e for e in inventory(directory) if e["path"] not in {"manifest.json", "manifest.sha256"}
    ]
    if manifest["files"] != actual:
        raise IntakeError("snapshot_inventory")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-bytes", required=True, type=int)
    parser.add_argument("--max-files", required=True, type=int)
    parser.add_argument("--min-free-bytes", type=int, default=0)
    parser.add_argument("--min-free-inodes", type=int, default=0)
    args = parser.parse_args()
    result = build_snapshot(
        args.intake,
        args.output,
        budget=OutputBudget(
            args.max_bytes, args.max_files, args.min_free_bytes, args.min_free_inodes
        ),
    )
    print(json.dumps({"snapshot_id": result["snapshot_id"], "analytics_enabled": False}))


if __name__ == "__main__":
    main()

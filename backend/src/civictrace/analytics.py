"""Bounded synthetic cohort diagnostics. No arbitrary SQL or real indicators."""

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path


class AnalyticsError(ValueError):
    pass


@dataclass(frozen=True)
class Cohort:
    currency: str
    start: str
    end: str
    status: str
    table: str = "awards"

    def validate(self):
        if self.table not in {"awards", "contracts"}:
            raise AnalyticsError("unauthorized_table")
        if not isinstance(self.currency, str) or not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise AnalyticsError("explicit_currency_required")
        if not isinstance(self.status, str) or not re.fullmatch(r"[a-z]{1,32}", self.status):
            raise AnalyticsError("explicit_process_status_required")
        a, b = _utc(self.start), _utc(self.end)
        if a >= b:
            raise AnalyticsError("invalid_period")
        return a, b


def _utc(value):
    try:
        if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})",
            value,
        ):
            raise ValueError
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise AnalyticsError("explicit_zoned_period_required") from exc


@dataclass(frozen=True)
class QueryBudget:
    max_files: int = 10000
    max_bytes: int = 128 * 1024**2
    max_rows: int = 25000  # across all six tables, not just the requested table
    wall_seconds: int = 30

    def validate(self):
        for key, maximum in (
            ("max_files", 10000),
            ("max_bytes", 128 * 1024**2),
            ("max_rows", 25000),
            ("wall_seconds", 30),
        ):
            value = getattr(self, key)
            if type(value) is not int or not 1 <= value <= maximum:
                raise AnalyticsError("invalid_query_budget")


def query_snapshot(directory, *, expected_snapshot_id, cohort, query="cohort_summary", budget=None):
    """Run one fixed SELECT in a disposable Linux child; require an independently pinned ID.

    The caller must have reviewed the invented fixture. Synthetic metadata is a guard, not
    proof of data origin. Parent paths must be operator-controlled throughout the copy.
    """
    if query != "cohort_summary":
        raise AnalyticsError("unauthorized_query")
    if not isinstance(cohort, Cohort):
        raise AnalyticsError("cohort_required")
    cohort.validate()
    budget = budget if budget is not None else QueryBudget()
    if not isinstance(budget, QueryBudget):
        raise AnalyticsError("invalid_query_budget")
    budget.validate()
    if not isinstance(expected_snapshot_id, str) or not re.fullmatch(
        "[a-f0-9]{64}", expected_snapshot_id
    ):
        raise AnalyticsError("pinned_snapshot_id_required")
    request = dict(
        directory=os.path.abspath(directory),
        expected_snapshot_id=expected_snapshot_id,
        cohort=asdict(cohort),
        budget=asdict(budget),
    )
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", ARROW_NUM_THREADS="1")
    # Parent owns cleanup even if the worker is killed on CPU, memory or wall limits.
    with tempfile.TemporaryDirectory(prefix="civictrace-query-") as private:
        request["private_directory"] = private
        try:
            child = subprocess.run(
                [sys.executable, "-m", "civictrace.analytics"],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                timeout=budget.wall_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise AnalyticsError("worker_wall_limit") from exc
    if child.returncode != 0:
        raise AnalyticsError("worker_resource_or_execution_failure")
    try:
        reply = json.loads(child.stdout)
    except ValueError as exc:
        raise AnalyticsError("invalid_worker_reply") from exc
    if "error" in reply:
        raise AnalyticsError(reply["error"])
    return reply


def _deny_network():
    """Linux syscall deny-list, inherited by engine threads; fail closed if unavailable."""
    import ctypes
    import ctypes.util
    import errno

    name = ctypes.util.find_library("seccomp")
    if sys.platform != "linux" or not name:
        raise AnalyticsError("linux_libseccomp_required")
    lib = ctypes.CDLL(name, use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = lib.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not ctx:
        raise AnalyticsError("network_isolation_failed")
    try:
        # No inherited network descriptors: subprocess.run closes all non-stdio FDs.
        for call in (
            "socket",
            "socketpair",
            "connect",
            "bind",
            "listen",
            "accept",
            "accept4",
            "sendto",
            "sendmsg",
            "sendmmsg",
            "recvfrom",
            "recvmsg",
            "recvmmsg",
        ):
            number = lib.seccomp_syscall_resolve_name(call.encode())
            if number < 0 or lib.seccomp_rule_add(ctx, 0x00050000 | errno.EPERM, number, 0) != 0:
                raise AnalyticsError("network_isolation_failed")
        if lib.seccomp_load(ctx) != 0:
            raise AnalyticsError("network_isolation_failed")
    finally:
        lib.seccomp_release(ctx)


def _connection():
    import duckdb

    con = duckdb.connect(
        config={
            "enable_external_access": "false",
            "autoload_known_extensions": "false",
            "autoinstall_known_extensions": "false",
            "allow_community_extensions": "false",
            "allow_unsigned_extensions": "false",
            "threads": "1",
            "memory_limit": "64MB",
            "temp_directory": "",
        }
    )
    con.execute("SET lock_configuration = true")
    return con


def _copy_snapshot(source, target, budget):
    from .snapshots import read_bytes

    source = Path(source)
    for part in (source, *source.parents):
        if not stat.S_ISDIR(part.lstat().st_mode):
            raise AnalyticsError("unsafe_snapshot_directory")
    total, count = 0, 0
    for parent, dirs, files in os.walk(source, followlinks=False):
        for name in dirs:
            if not stat.S_ISDIR((Path(parent) / name).lstat().st_mode):
                raise AnalyticsError("unsafe_snapshot_entry")
        for name in sorted(files):
            path = Path(parent) / name
            if not stat.S_ISREG(path.lstat().st_mode):
                raise AnalyticsError("unsafe_snapshot_entry")
            count += 1
            size = path.stat().st_size
            if count > budget.max_files or total + size > budget.max_bytes:
                raise AnalyticsError("snapshot_copy_budget")
            # Limit the read even if the source file grows concurrently.
            data = read_bytes(path, min(budget.max_bytes - total, 32 * 1024**2))
            total += len(data)
            dest = target / path.relative_to(source)
            dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            dest.write_bytes(data)
    return count, total


def _load_tables(directory, manifest, budget):
    import pyarrow as pa
    import pyarrow.parquet as pq

    from .snapshots import SCHEMA, TABLES

    if set(manifest["tables"]) != set(TABLES):
        raise AnalyticsError("table_contract")
    columns = [
        "id",
        "process_id",
        "release_id",
        "status",
        "currency",
        "amount_state",
        "currency_state",
        "date_state",
        "projection_exclusion",
        "date",
        "amount",
    ]
    rows = {table: [] for table in TABLES}
    seen = 0
    for entry in manifest["files"]:
        if not entry["path"].endswith(".parquet"):
            continue
        parts = Path(entry["path"]).parts
        if len(parts) != 4 or parts[0] != "tables" or parts[1] not in TABLES:
            raise AnalyticsError("parquet_path_contract")
        table = parts[1]
        pf = pq.ParquetFile(directory / entry["path"])
        if pf.schema_arrow != SCHEMA:
            raise AnalyticsError("parquet_schema_contract")
        seen += pf.metadata.num_rows
        if seen > budget.max_rows:
            raise AnalyticsError("snapshot_row_budget")
        # Projection prunes large canonical_json, but preserves all exact amount digits.
        for batch in pf.iter_batches(batch_size=256, columns=columns, use_threads=False):
            for row in batch.to_pylist():
                row["amount"] = str(row["amount"]) if row["amount"] is not None else None
                rows[table].append(row)
    if any(len(rows[t]) != manifest["tables"][t] for t in TABLES):
        raise AnalyticsError("table_count_contract")
    # DuckDB cannot represent decimal256. Pass a decimal string, never a float/DECIMAL(38).
    schema = pa.schema(
        [(c, pa.timestamp("us", tz="UTC") if c == "date" else pa.string()) for c in columns]
    )
    return {t: pa.Table.from_pylist(rows[t], schema=schema) for t in TABLES}


# Fixed table substitution is restricted by Cohort.validate; every cohort value is bound.
_SQL = """
SELECT a.amount,
 CASE WHEN r.id IS NULL THEN 'missing_release'
      WHEN r.status IS NULL THEN 'missing_process_status'
      WHEN r.status <> ? THEN 'different_process_status'
      WHEN r.date IS NULL THEN 'missing_release_date'
      WHEN r.date < ? OR r.date >= ? THEN 'outside_period'
      WHEN a.currency IS NULL THEN 'missing_currency'
      WHEN a.currency <> ? THEN 'different_currency'
      WHEN a.projection_exclusion IS NOT NULL THEN 'projection_exclusion'
      WHEN a.amount IS NULL THEN 'missing_amount'
      ELSE 'included' END AS disposition,
 a.amount_state, a.currency_state, r.date_state, a.projection_exclusion
FROM {table} a LEFT JOIN releases r
 ON a.release_id = r.id AND a.process_id = r.process_id
ORDER BY a.id, a.release_id
"""


def _summarize(tables, cohort):
    start, end = cohort.validate()
    with _connection() as con:
        for name, table in tables.items():
            con.register(name, table)
        # Fail closed against join amplification; no implicit amendment/latest selection.
        if con.execute("SELECT count(*) <> count(DISTINCT id) FROM releases").fetchone()[0]:
            raise AnalyticsError("duplicate_release_identity")
        result = con.execute(
            _SQL.format(table=cohort.table), [cohort.status, start, end, cohort.currency]
        ).fetchall()
    counts, states = {}, {k: {} for k in ("amount", "currency", "release_date", "projection")}
    with localcontext() as ctx:
        ctx.prec = 128  # 76 input digits + ceil(log10(25000)) headroom; exact addition
        total = Decimal(0)
        for amount, reason, ast, cst, dst, projection in result:
            counts[reason] = counts.get(reason, 0) + 1
            for key, value in zip(states, (ast, cst, dst, projection)):
                label = value or "not_applicable"
                states[key][label] = states[key].get(label, 0) + 1
            if reason == "included":
                total += Decimal(amount)
    included = counts.pop("included", 0)
    return dict(
        total_rows=len(result),
        included_rows=included,
        excluded_rows=len(result) - included,
        exclusions=dict(sorted(counts.items())),
        field_states=states,
        exact_amount_sum=str(total) if included else None,
    )


def _worker(request):
    import resource

    # Process-wide bounds also cover native Arrow allocations and verification/copy work.
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    _deny_network()
    from .snapshots import verify_snapshot

    budget = QueryBudget(**request["budget"])
    budget.validate()
    resource.setrlimit(resource.RLIMIT_FSIZE, (budget.max_bytes, budget.max_bytes))
    cohort = Cohort(**request["cohort"])
    cohort.validate()
    directory = Path(request["private_directory"])
    files, size = _copy_snapshot(request["directory"], directory, budget)
    manifest = verify_snapshot(directory)
    if manifest["snapshot_id"] != request["expected_snapshot_id"]:
        raise AnalyticsError("snapshot_pin_mismatch")
    source = manifest["source"]
    if any(
        source.get(k) not in {"synthetic-only", "synthetic-example"}
        for k in ("source_url", "resolved_url", "selection", "privacy_review")
    ):
        raise AnalyticsError("synthetic_only")
    tables = _load_tables(directory, manifest, budget)
    summary = _summarize(tables, cohort)
    return dict(
        query_version="civictrace-cohort/1",
        snapshot_id=manifest["snapshot_id"],
        analytics_enabled=False,
        synthetic_only=True,
        cohort=asdict(cohort),
        period_basis="release date UTC; start inclusive, end exclusive",
        version_policy="all imported versions; no latest inference or FX",
        source=source,
        quality_gate=manifest["quality_gate"],
        import_summary=manifest["import_summary"],
        validation_field_states=manifest["validation_field_states"],
        resources=dict(copied_files=files, copied_bytes=size, budget=asdict(budget)),
        **summary,
    )


def main():
    try:
        request = json.loads(sys.stdin.read(16385))
        reply = _worker(request)
    except AnalyticsError as exc:
        reply = {"error": str(exc)}
    except Exception:
        # Do not leak source contents or filesystem details in errors.
        reply = {"error": "snapshot_or_worker_invalid"}
    print(json.dumps(reply, sort_keys=True))


if __name__ == "__main__":
    main()

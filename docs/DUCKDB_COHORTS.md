# Isolated synthetic DuckDB cohorts

Implemented for the synthetic diagnostic portion of issue #12. Stacked on PR #35 at
`d9c53b1c3ed4eb17133c2f5fc4e4f67f4121d9ce`, reusing its six-table
[Parquet contract and verifier](PARQUET_SNAPSHOTS.md) and PR #29's
[canonical model](DATA_MODEL.md). All remote branches and open PRs were inspected on
2026-10-31; there was no existing DuckDB implementation. Nothing was merged.

**Real indicators remain blocked.** Every accepted manifest and result must retain
`analytics_enabled: false`. No single-bid, concentration, HHI, fraud score or other real
indicator is added. This API accepts only operator-reviewed invented snapshots: the pinned
snapshot ID must match, and source_url, resolved_url, selection and privacy_review must each
be `synthetic-only` or `synthetic-example`. These labels are defensive guards, not proof that
records are invented. Keep the trusted ID independently; do not relabel real data to pass this
check. The caller is trusted to choose a reviewed synthetic fixture.

## Reproduce

Linux with libseccomp.so.2 is mandatory; unsupported environments fail closed. Ubuntu's
`libseccomp2` package supplies the library. Python 3.11–3.13; tested dependencies are pinned:
PyArrow 23.0.1 and DuckDB 1.4.3. No extension download is required.

```sh
python -m pip install -e '.[dev,analytics]'
python -m pytest tests/test_analytics.py -q
python scripts/analytics_example.py /tmp/new-invented-cohort
```

The example reuses the snapshot generator rather than a second importer or canonical mapping.
It invents three PYG awards of `9007199254740993.01` and three release dates at
2026-01-01T00:00:00Z with process status `complete`. It asserts repeated byte-equivalent JSON
results, included rows 3, excluded rows 0, and exact sum `27021597764222979.03`.
The output directory must be absent. No real source data is read.

Library interface:

```python
from civictrace.analytics import Cohort, QueryBudget, query_snapshot

result = query_snapshot(
    "/private/reviewed-invented-snapshot",
    expected_snapshot_id="<independently trusted 64-character snapshot ID>",
    cohort=Cohort(
        currency="PYG",
        start="2026-01-01T00:00:00Z",
        end="2027-01-01T00:00:00Z",
        status="complete",
        table="awards",
    ),
    budget=QueryBudget(max_files=10000, max_bytes=128 * 1024**2, max_rows=25000),
)
```

Only query name `cohort_summary` and tables `awards` / `contracts` are authorized. The four
cohort filters are mandatory; currency/status are bound parameters, never SQL fragments.
Raw SQL, file paths as table names and indicator names are rejected before spawning a worker.
No public HTTP service or configurable SQL console is provided.

## Cohort meaning and precision

Period uses the associated **release date in UTC**, start inclusive and end exclusive. It is
neither award date nor signing date nor fiscal year. Status is the canonical **process/tender
status on that release**, not award/contract status. Both process_id and release_id link each
amount to its release. Duplicate release IDs fail closed to prevent join amplification.
All imported versions are retained; there is no inferred latest release, amendment resolution,
exchange rate conversion, supplier allocation or interpretation of award/contract lifecycle.
A sum is a raw synthetic projection diagnostic, not reviewed final procurement expenditure.

Each row receives exactly one disposition, in this order: missing release; missing process status;
different process status; missing release date; outside period; missing currency; different
currency; projection exclusion; missing amount; included. Exclusions are disjoint, reconcile to
excluded_rows, and included_rows + excluded_rows = total_rows. Independent field-state counts
for amount, currency, release date and projection report all target-table rows, including those
excluded earlier. Null/absent/invalid/unsupported values stay distinct; they are not zeros.
No included amount yields a null sum; a genuine included zero yields an exact decimal zero.
Importer rejected counts and validation states are separately retained from the manifest and
are not silently counted as projected rows. Source rights/privacy metadata, quality gate,
snapshot identity and full filter parameters accompany each result.

DuckDB cannot natively represent Arrow decimal256(76,18). The trusted adapter reads the exact
Parquet decimals and registers decimal strings with DuckDB, pruning canonical_json. DuckDB
executes a fixed parameterized SELECT and classifications; Python Decimal sums only included
strings under precision 128. The 25,000-total-row ceiling needs at most five extra integer
digits beyond the 76-digit input type. No float, rounding or narrowing to DECIMAL(38) occurs.
Overflow/fractional projection exclusions remain null with their original ledger untouched.

## Isolation and resource contract

The public API starts a new disposable worker with piped stdio and closed inherited descriptors.
Before Arrow/DuckDB import, Linux seccomp denies socket creation and network send/receive/connect
syscalls, including on subsequently created engine threads. If enforcement cannot load, the
worker fails. DuckDB disables external access, extension auto-install/auto-load, unsigned and
community extensions. Configuration is locked; no exceptions/allowed paths are installed.
Its filesystem readers, COPY and ATTACH are denied. Only in-memory registered Arrow views are
available to fixed SELECTs. No persistent database or DuckDB spill directory is used.
See [DuckDB security guidance](https://duckdb.org/docs/1.4/operations_manual/securing_duckdb/overview).

The trusted Python adapter copies a bounded source tree into a mode-0700 parent-owned temporary
directory; symlinks, FIFOs, nonregular files and symlink ancestors are rejected. Only this private
copy is verified and read. It reuses verify_snapshot for manifest hash, snapshot identity,
contract/gate, complete inventory/byte hashes, then checks the trusted ID, synthetic guard,
Parquet schema, six table counts and row budget. Mutation of the source after copying cannot
change data queried. Corruption fails before any result is returned. Parent paths must remain
operator-controlled during copying; this is not a sandbox against hostile concurrent path owners.
Hashes establish identity, not publisher authentication or truth of source semantics.

| Bound | Default and hard maximum |
| --- | --- |
| Copied regular files, including evidence/manifests | 10,000 |
| Total logical copied bytes | 128 MiB |
| Individual copied file | 32 MiB |
| Rows across all six tables | 25,000 |
| Worker elapsed wall time, including imports/copy/verification | 30 seconds |
| Worker CPU time, OS RLIMIT_CPU | 20 seconds |
| Worker virtual address space, OS RLIMIT_AS | 2 GiB |
| Open file descriptors, OS RLIMIT_NOFILE | 64 |
| Worker core dump bytes | 0 |
| Individual worker output file, OS RLIMIT_FSIZE | configured copy-byte budget |
| DuckDB memory setting / threads | 64 MB / 1 |

Callers can lower copy/row/wall ceilings, never raise them above these maxima. The OS address
space limit covers native allocations; it is not an RSS promise. DuckDB's own memory setting is
not a complete native-memory cap. File budgets are logical bytes, not allocated disk/inodes;
operators still need space/quota headroom and a private local temp parent. Parent cleanup also
runs after worker timeout or OS termination. Parent crash/power loss can leave private temporary
files; stop workers, inspect and remove the specific directory manually. No automatic unbounded
retry or compaction occurs. Large or small-file-heavy snapshots fail closed; this is intentionally
below the importer's maximum workload. This library is not an OS filesystem sandbox for arbitrary
Python/native code; the trusted adapter retains normal process filesystem permissions.

## Validation

Deterministic tests cover repeated output and unchanged snapshots, decimal256 extrema and sums
above DuckDB precision, true zero, different currencies, missing/unsupported values, half-open
UTC boundaries, process status, empty cohorts, pinned-ID mismatch, corrupt Parquet, symlinks,
synthetic-only rejection even after a manifest is rehashed, byte/file/row budgets, timeout and
terminated-worker handling, SQL rejection, direct engine filesystem/network/extension/config
rejection, and OS socket syscall denial in a separate child. All records are invented.

The existing CI dev extra installs the pinned engine, so the full existing Python matrix executes
these tests without changing workflows or skipping the isolation tests. Exact hosted results are
reported in the PR after publication; local results alone do not establish hosted success.

Local verification, Python 3.12.14: **176 tests and 95 subtests passed**, zero skipped;
33 new analytical tests. Ruff lint/format, documentation links, whitespace and the three-row
example passed. A separate 1,000-invented-row snapshot query copied/verified 8,007 files and
67,902,310 logical bytes, returned 1,000 included / 0 excluded and exact sum
`9007199254740993010.000000000000000000` PYG. Observed elapsed query time including startup,
copy and cleanup was 4.530 seconds; child peak RSS was 176,340 KiB on Linux. Snapshot ID:
`3960b64175923ec38ef5f27c56bdcfb53ef6195b0a207b59336bcd6def332401`.
This is one synthetic local observation, not a maximum-workload or production performance claim.

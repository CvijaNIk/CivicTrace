# Architecture

## Boundaries
The foundation runs entirely offline with local JSON files. Public-data ingestion will be an
explicit CLI task, never an implicit browser upload. Connectors normalize source data; analytics
consume a canonical table; reporting produces Evidence Passports. Keep source bytes immutable.

| Boundary | Contract | First implementation |
| --- | --- | --- |
| connectors/ | Source-specific public adapters with licensed snapshots | DNCP bounded JSONL import |
| backend/src/civictrace/ | Canonical validation, orchestration, local CLI | Synthetic CLI exists |
| analytics/python/, analytics/sql/, analytics/r/ | Reviewed versioned rules | Python demo and SQL specification |
| reporting/ | Passport-to-report rendering | JSON serializer exists in backend |
| frontend/ | Static public explorer, later local workspace | Deferred to dedicated issue |
| cybersecurity/ | Passive public adapters and integrity tools | Deferred v0.5 |
| schemas/ | Versioned machine-readable contracts | Passport schema exists |

Do not create empty modules before useful code exists. Uncreated directories above are planned
boundaries, not installed capabilities. No initial HTTP API, microservices, job queue, Kubernetes,
managed database, secrets-bearing automation or user account model.

## Stack decisions
Python 3.11+ is the stable base. Add Polars for columnar transformations, Pydantic for typed
canonical ingestion and DuckDB for bounded analytical SQL. Keep precise monetary values as
Decimal/decimal columns; never aggregate across currencies without documented conversion.
Parquet snapshots are partitioned and accompanied by manifest hashes and methodology versions.
React/TypeScript/Vite produces static assets. Introduce DuckDB-Wasm only after local privacy,
worker lifecycle and memory profiling. Graphs use Cytoscape.js after v0.3 relationships exist.
R/Quarto integrate through explicit file contracts rather than executing arbitrary notebook code.

## Deployment and scale
Initial candidate: a static GitHub Pages deployment from this public repository, subject to
current provider limits and terms. No deployment configured or zero-cost guarantee made.
Public bounded extracts can be prepared offline and served as static artifacts when rights and
privacy review pass. Private data never belongs in public build artifacts. Browser processing
has hard memory limits: document measured limits, cancel queries and direct large files to CLI.
Use chunked ingestion, Polars lazy scans and DuckDB before considering distributed processing.

## Reproducibility
Record original bytes, acquisition time, source version, canonical schema version, connector
version, exclusion counts, rule version and parameters. Findings inherit a snapshot reference.
A content hash proves byte identity; it does not prove truth, authorship or collection time.
Environment dependency ranges are currently bounded but not fully locked. Add hashed lock files
before a real-data release and preserve environment metadata with exports.

## Measured local intake budgets

[ADR 0002](adr/0002-measured-dncp-workload-budgets.md) records the implemented DNCP CLI
ceilings, browser deferral and alternatives. The [synthetic resource experiment](DNCP_BENCHMARK.md)
measures process RSS, traced Python allocations, throughput and disk/file amplification separately.
Empirical measurements are not guaranteed memory limits; the browser has no DNCP importer yet.

## Local Parquet storage increment

[Versioned Parquet snapshots](PARQUET_SNAPSHOTS.md) implement six partitioned canonical projections
from byte-verified importer replay, with original private evidence, manifests, explicit Arrow schema,
exact decimal/UTC types and atomic no-replace publication. This is a storage layer with bounded
budgets, not an implemented DuckDB analytical service. General identity reconciliation remains
partial and DNCP source semantics/quality still block real indicators.

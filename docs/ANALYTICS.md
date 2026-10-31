# Analytical rules

[Isolated synthetic DuckDB cohorts](DUCKDB_COHORTS.md) now provide bounded exact projection
diagnostics over pinned Parquet snapshots. Real indicators below remain blocked;
`analytics_enabled: false` is required.

## Single bid (demo implemented, production planned)
Flag bid_count == 1. Unknown counts, zero, malformed and negative values must not be flags.
The demo rejects malformed counts and duplicate process/release identities. Optional cancellation
and joint-supplier guards exclude records conservatively; [edge-case diagnostics](SYNTHETIC_EDGE_CASES.md)
record the reason. Reported tenderers and bid detail rows never supply `bid_count`. Production must distinguish reported bids, bidders and valid
bids, account for procedure/stage/lot semantics, and expose denominator/exclusion counts.
Single participation may have lawful explanations; review tender terms, exceptions and market.

## Supplier concentration (planned)
For one buyer/period/currency/category cohort, sum comparable final award amounts per verified
supplier and divide by eligible total award value. Report top-supplier share and optionally HHI.
Disclose cohort, numerator, denominator, counts and exclusions. No arbitrary universal fraud
threshold. Exclude unallocated joint awards to avoid double counting; preserve withdrawn/cancelled
award treatment and test release amendments.

## Submission window (planned)
Elapsed UTC hours = tender end minus tender start. Show raw duration and a configurable,
justified peer/procedure benchmark. Missing or invalid timestamps are data-quality findings.
Separate calendar time from working days and local holidays; do not claim a legal violation.

## Research standards
Preregister test intent where useful, document sampling and multiple-testing effects, check
out-of-sample performance and sensitivity, and report unknown/missing/censored observations.
Benford and other distributions apply only to suitable populations and never prove fraud.
No generated fraud probabilities. Future models must have model cards, assumptions, diagnostics,
comparison groups, license evidence and synthetic regression fixtures.

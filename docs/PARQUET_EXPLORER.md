# Verified synthetic Parquet explorer

The opt-in local page `/?view=parquet` now displays four invented procedures from
an actual, verified Parquet snapshot. The original five-record explorer remains
at `/`. This is a bounded static preview, not a public-data release or indicator.

## Existing contracts reused

Stacked on PR #38, which includes #35–#37. The adapter reuses `verify_snapshot`,
the analytics module's bounded private copy and six-table schema/count loader,
and `snapshot_record_lineage` for complete importer/writer replay. It does not
create another importer, canonical model, SQL API or browser database. DuckDB
cohort summaries remain a separate offline diagnostic; they are not recomputed
or exposed by this page. `analytics_enabled: false` remains mandatory.

`civictrace-parquet-explorer/2` carries snapshot/canonical schema versions,
snapshot identity, original gzip and expanded hashes, source rights/privacy,
full hashed artifact inventory, original record/release IDs, source pointers,
writer and transformation hashes, verification environment, validation ledger,
import rejection/quarantine details and per-child projection exclusions. All
imported release versions are retained, without inferred latest selection.
Raw source bodies are not copied into browser release rows; original OCID/ID,
canonical fields, row hashes and evidence references are retained.

Financial projections use exact fixed-point strings, including 18 fractional
digits. Source amount fields remain strings too. Missing/absent/null/invalid/
unsupported canonical states remain explicit and never become zero. Amounts
outside decimal256(76,18) retain their canonical source amount and exclusion
reason; they are not rounded. No aggregation, FX, scoring or ranking is offered.
Awards and contracts are shown separately, not added as expenditure.

## Run locally

```sh
python -m pip install -e '.[dev]'
python scripts/export_parquet_explorer.py --check
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/?view=parquet`. Expected: four procedures, three
complete and one cancelled, PYG and USD, exact `9007199254740993.010000000000000000`,
exact zero, absent release date, null amount, missing currency, and one amount
projection exclusion (`1e58` source value). Dates retain their original offsets.
All award dates and contract signing dates are unknown in this invented fixture.
A source row is not a real finding. Filtering to cancelled returns one row.
Source/rights and exclusion details are expandable; static JSON is downloadable.

To regenerate the reviewed invented fixture and bundled SHA-256 pin:

```sh
python scripts/export_parquet_explorer.py
python scripts/export_parquet_explorer.py --check
```

This generates four reviewed invented rows through the existing snapshot example,
importer and writer in a private temporary directory. It accepts no input path.
`--check` compares all semantic output, snapshot identity, implementation/writer
hashes and the committed payload pin; only verification-time environment metadata
is excluded from cross-Python comparison. The exported environment remains recorded.
Review source changes and pins before accepting regenerated artifacts.

For other operator-reviewed synthetic snapshots only, the offline Python API is
`export_snapshot(path, expected_snapshot_id=independently_reviewed_pin)` in
`civictrace.parquet_explorer`. It returns UTF-8 JSON, never overwrites input, and
fails rather than truncates. It is not a browser or HTTP endpoint. A new UI
artifact must be reviewed and its bundled pin updated before use.

## Bounds and integrity

- Private copy: 1,000 files, 8 MiB total; existing regular-file/symlink checks.
- Six-table Arrow schema and declared counts checked; 1,000 total entity rows,
  at most 100 releases; final static UTF-8 JSON at most 64 KiB.
- Disposable Linux process: 30 seconds wall, 20 seconds CPU, 2 GiB virtual
  memory, 64 descriptors, 8 MiB per output file, no core dump; existing seccomp
  network denial. Linux/libseccomp is required. Parent cleans its temporary tree;
  replay temporaries are rooted beneath it through TMPDIR.
- Browser: fixed relative asset only, bounded streaming and strict runtime
  contract, 10-second timeout/abort, SHA-256 compared with a bundled build pin,
  no credentials/redirects. No SQL input, uploads or filesystem capability.
- Checksums/replay establish consistency, not source truth, authenticity,
  authenticated acquisition time, confidentiality or redistribution rights.
  Synthetic metadata is a guard; operators must review fixtures and pins.
  Trusted local Python/native code is not a filesystem sandbox. Recorded replay
  output budgets also apply; disk/inode headroom remains an operator requirement.

## Validation

```sh
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python scripts/check_docs.py
cd frontend
npm test
npm run build
npm run format:check
npx playwright install --with-deps chromium
npm run test:browser
```

New Python tests cover byte-identical export, exact amounts, null versus zero,
absent dates, excluded precision, corruption, wrong pins, synthetic gates,
symlinks, resource/record/byte limits, wall timeout and rejected/quarantined rows.
Frontend tests cover runtime rejection, exact rendering, filtering, provenance,
retry and cancellation. Browser tests cover keyboard operation, automated axe
checks, narrow viewport and tampered-payload rejection/recovery. Actual execution
results and any browser-download limitations are recorded in the draft PR.

No real data is downloaded or published. No merge, deployment, production
activation, issue closure or release-readiness claim is part of this change.

## Buyer, supplier/tenderer and contract filters (#19)

The incremental implementation is stacked on PR #40 (including #39), without merging
existing branches. The static asset path remains `data/parquet-v1.json`, while its
validated payload contract is now `civictrace-parquet-explorer/2`. Older payloads
fail closed; regenerate the payload and bundled checksum together.

Each release carries a minimized `search` projection with separate `buyers`,
`suppliers` and `contracts` arrays. Each entry preserves source ID/name field states,
source filename, original record SHA-256, canonical identity when available, and a
pointer with an explicit scope. `release_source_record` pointers address the original
record preserved in that release's canonical `source_record`; `party_canonical`
pointers address the identified party row; `contract_canonical` pointers address the
identified contract row. The filename identifies the replayed canonical model, and
the checksum is the original source-record hash, not a hash of the displayed text.

- Buyers use the explicitly reported original `buyer` object; no name-based join,
  inferred party role or registry/legal identity claim. An absent/null/malformed buyer
  retains explicit unknown states. A buyer's unresolved canonical party identity is
  shown as unknown even if its reported source ID is present.
- Supplier/tenderer entries come from canonical parties with an explicit `supplier`
  or `tenderer` role, or a canonical award-supplier link. Matching is scoped by BOTH
  release and process. Other parties are not assumed to be bidders; award links do
  not establish complete bid participation or supplier allocation.
- Contracts use only retained canonical contracts and their source IDs. A title is
  projected from the original contract only when its ID has one unambiguous original
  match. Duplicate IDs (including quarantined duplicates) leave the title unsupported.
  No tender/award title is substituted. Original pointers are recovered after child
  quarantine rather than assuming sanitized array indices still match.
- Only ID/name/title text is projected. Addresses, contacts and raw invalid values
  are not copied into search entries. The existing synthetic-only/replay/resource
  gates, source rights, inventory, exclusion ledger and all financial strings remain.

Exact ID filters compare the whole original string, including case and whitespace.
Name/title filters trim the query and perform a case-insensitive substring match;
there is no fuzzy matching, accent folding, normalization of IDs, deduplication or
entity resolution. ID and name in one category must match the SAME entry; categories,
source search and status combine with AND. Unknowns never match entered text, including
the displayed word `Unknown`; blank filters leave unknown records in the result.
Counts refer to imported release records, not unique legal entities or contracts.
Active filters, reset, loading/error/retry and no-results states use the existing UI;
all new controls have visible labels and native keyboard behavior. Data is filtered
in memory; filter values are not sent to an API or placed in URLs/storage.

Reproducible invented example at `/?view=parquet`:

| Filters | Expected release records |
| --- | --- |
| None | 4 |
| Buyer name contains `Invented Council` | 3 distinct buyer source IDs |
| Buyer exact ID `SYN-BUYER-0` | 1 (`SYN-000000`) |
| Buyer exact ID `syn-buyer-0` or `SYN-BUYER` | 0 |
| Supplier / tenderer name contains `Invented Works` | 3 distinct supplier source IDs |
| Contract title contains `maintenance` | 3 distinct contract source IDs |
| Buyer ID `SYN-BUYER-0` AND supplier ID `SYN-SUPPLIER-1` | 0 |
| Buyer ID `SYN-BUYER-0`, supplier ID `SYN-SUPPLIER-0`, contract ID `SYN-CONTRACT-0` | 1 |
| Buyer name `Invented Council` AND status `cancelled` | 1 (`SYN-000001`) |
| Source identifier contains `SYN-000002` | 1, buyer null and supplier name null |

The fourth complete record also shares those names with different IDs. The missing
record retains its existing source supplier/contract IDs and missing contract title.
Reset restores all four records. These are invented source-local identifiers, not
verified business-registration numbers. All output retains `analytics_enabled: false`.

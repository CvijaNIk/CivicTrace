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

`civictrace-parquet-explorer/1` carries snapshot/canonical schema versions,
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

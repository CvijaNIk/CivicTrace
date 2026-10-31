# Deterministic synthetic search exports (partial #20)

The existing `/?view=parquet` page retains its complete verified JSON download.
Separate links under **Export current search results** provide `results.json`,
`results.csv` and `manifest.json`. Save all three together. There is no server,
external export request, storage of filters, timestamp or real-data activation.
This change is stacked on #41 (`feat/entity-search`), not a replacement explorer.

## Reproduce and inspect

```sh
cd frontend
npm ci
npm test
npm run build
npx playwright install --with-deps chromium
npm run test:browser
npm run dev
```

Open `/?view=parquet`, enter buyer name `Invented Council`: 3 release records,
with distinct source IDs. Add supplier exact ID `SYN-SUPPLIER-0`: 1 record.
Add contract exact ID `SYN-CONTRACT-1`: 0 records. Reset: 4 records. Download
all three files at each step. A zero-result JSON contains `records: []`, CSV
has only its header, and the manifest has `result_count: 0`.

`results.json` schema `civictrace-filtered-records/1` retains complete selected
release projections, awards, contracts, search identities, source identifiers,
original decimal strings, availability states/nulls, original-record hashes,
source filenames, pointers and pointer scopes. Arrays retain source order.
There is no name-based joining, deduplication, summing or latest-version choice.
The displayed and exported release list uses the same selector; export also
checks the ordered identities against the current displayed list. A filter
change immediately replaces the export panel, cancels stale async publication
and revokes its object URLs. No stale download links survive the change.

## CSV codec and formula safety

CSV schema `civictrace-json-cells/1` is UTF-8 without BOM, RFC4180 quoting,
fixed columns, CRLF records. One row represents one release. `release`, `search`,
`awards` and `contracts` cells retain structured JSON instead of flattening
one-to-many relationships or losing unknown states. **Every data cell is a
JSON value**, including identifiers. After reading CSV, JSON-decode each cell.
This makes decimal strings and identifiers lossless even in spreadsheet tools:
a text cell starts with a literal JSON double quote, never `=`, `+`, `-`, `@`,
leading whitespace/control characters or their full-width variants. JSON escapes
embedded control characters. Merely quoting ordinary CSV text would be unsafe.
Do not strip the literal JSON string quotes before opening in a spreadsheet.

Example reader (Python standard library, downloaded files only):

```python
import csv
import hashlib
import json
from pathlib import Path

manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))
for name, expected in manifest["files"].items():
    raw = Path(name).read_bytes()
    assert len(raw) == expected["bytes"]
    assert hashlib.sha256(raw).hexdigest() == expected["sha256"]
with Path("results.csv").open(encoding="utf-8", newline="") as stream:
    rows = [{k: json.loads(v) for k, v in row.items()} for row in csv.DictReader(stream)]
records = json.loads(Path("results.json").read_text(encoding="utf-8"))["records"]
assert len(rows) == manifest["result_count"] == len(records)
assert [
    {k: row[k] for k in ("release", "search", "awards", "contracts")} for row in rows
] == records
```

## Manifest and limits

Manifest schema `civictrace-export-manifest/1` links both payload names, their
SHA-256 and exact UTF-8 byte lengths; records snapshot identity, all schema
versions, full entered filters (including exact-ID whitespace), ordered result
identities, source/rights metadata, gzip/expanded/artifact checksums, import
coverage, full exclusion ledger, projection exclusions and evidence limitations.
The verified preview pin refers to the original raw preview bytes, not a
reserialized JSON representation. Existing loader verification still checks
those bytes before presenting data. No hash claims to prove factual truth.
The unsigned manifest has no circular self-hash; verify its source pin against
trusted repository history before treating it as trusted evidence.

Input inherits the preview's 65,536-byte and 100-release bounds. Combined CSV,
JSON and manifest output is capped at 262,144 UTF-8 bytes; no silent truncation.
The final bound includes the manifest. Tests cover exact limit acceptance,
one-byte rejection, multibyte text and inclusion of the third file. Invalid
contracts, gates, filters or display mismatches fail closed without links.
Object keys sort lexically; arrays preserve verified input order. Same snapshot
and entered filters give identical bytes. Semantically equivalent differently
entered filters are deliberately recorded as entered, so manifests can differ.

## Validation and remaining scope

Local validation: 83 Vitest cases pass; strict TypeScript/Vite build and
Prettier pass. Existing Python checks and hosted browser results are recorded
in the PR. Seven local Playwright attempts failed before assertions because
Chromium was absent; installation returned a truncated/invalid ZIP. This is
not a successful browser run. Added browser coverage downloads and hashes all
three outputs and checks combined filters, empty results, reset, original
snapshot download and automated accessibility.

Only invented fixture data is used. All outputs retain
`analytics_enabled: false` and `synthetic: true`. Real-source indicators,
connector-to-indicator validation, real-source release acceptance, signed
exports and production activation remain outside this partial #20 change.
No issue closure, merge, deployment or release-readiness claim.

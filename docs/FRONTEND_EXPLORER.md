# Local synthetic research explorer

Issue #3 foundation, stacked on draft PR #36 at
`0f376f508638dbc9ca0539681f547e87896f794a`; dependencies remain unmerged.
All remote branches and open PRs were inspected before implementation; no React/TypeScript/Vite
frontend or package manifest existed. No existing development branch is changed.

## Run locally

Node 22.12+ (CI uses Node 24) and npm; Python 3.11+ for fixture reproducibility and backend checks.
From the repository root:

```sh
python -m pip install -e '.[dev]'
python scripts/export_explorer.py --check
cd frontend
npm ci
npm run dev
```

Open the loopback URL printed by Vite (normally http://127.0.0.1:5173).
Vite serves static assets for local development; no production/application server or accounts.
To build and inspect the compiled static assets locally: `npm run build`, then `npm run preview`.
Public hosting/deployment is outside this change.

```sh
# From frontend/
npm test
npm run build
npx playwright install --with-deps chromium
npm run test:browser
```

The browser suite exercises actual Chromium keyboard navigation, filtering, HTTP failure/retry,
automated axe WCAG A/AA checks, narrow-viewport overflow and desktop/mobile screenshots.
Automated checks are not a full accessibility certification: manual assistive-technology review,
additional browsers, localization and user testing remain future work.

## Stable boundary

The browser fetches only its bundled `data/synthetic-v1.json`, same origin, without credentials.
There are no external requests, analytics, file pickers, uploads, persistence or arbitrary query APIs.
The adapter exports only `examples/synthetic_procurement.json`, validates each row using the existing
Python `validate_record` contract and requires a reviewed source SHA-256 pin. It accepts no input
path; fixture changes fail closed until independently reviewed and pinned. Run
`python scripts/export_explorer.py` to reproduce the checked-in JSON. The `--check` mode and Python
regression compare exact bytes. Synthetic labels alone do not authenticate provenance.

`civictrace-explorer/1` is a deliberately small projection, not a canonical or DuckDB result format:

| Field | Contract |
| --- | --- |
| `schema_version` | Exact `civictrace-explorer/1` |
| `synthetic`, `analytics_enabled` | Exact `true`, `false`; otherwise reject |
| `source` | Fixture path, original SHA-256, name, license, attribution, privacy review |
| `limitations` | 1–10 nonempty strings, at most 512 characters each |
| `records` | 0–100 unique synthetic IDs, buyer/supplier IDs, synthetic source reference |
| `bid_count` | Null or nonnegative safe integer; zero stays zero |
| `data_status` | `missing` iff count is null; otherwise `reported` |

A 64 KiB UTF-8 ceiling is applied while streaming and before JSON parsing. Text fields are limited
to 512 characters; search input to 128. Unknown contract versions, inconsistent states, unsafe
counts and unsupported metadata fail closed. React renders source strings as text, never HTML or
executable links. The download contains only the fixed synthetic projection.

The upstream original source hash identifies the reviewed fixture bytes; it is not an independent
signature or an integrity verification of the browser payload. No dates, financial amounts,
procurement statuses or real-data quality assertions are fabricated. The filter is explicitly
bid-count availability, not procedure status. A future canonical/Parquet projection needs a new
reviewed adapter and tests, especially for exact decimal strings and exclusions. DuckDB workers,
local files and SQL are never exposed to the browser. Issue #18 remains broader future work.

## Expected example and limitations

Initial screen: five invented records, four reported counts and one missing count.
`SYN-003` displays **Unknown — not supplied**; `SYN-004` displays **0**.
Search `SYN-SUPPLIER-1`: three results. Missing-count filter alone: one result, `SYN-003`.
Combining that filter with `SYN-004`: zero matches and an explicit empty-results message.
Reset: five results. A valid zero-row fixture has a separate empty-dataset explanation.
HTTP/contract errors show no table and a retry button; loading is announced via a live status and fails visibly after ten seconds.

Source passport shows original fixture identity, checksum, rights, attribution, privacy notes,
contract version and interpretation limitations. No totals, fraud scores or real analytical
indicators are computed. `analytics_enabled: false` remains mandatory throughout.

Existing Python CI remains intact. The added frontend job runs locked installation, fixture drift
check, strict TypeScript build, component/contract tests and Chromium/axe browser checks. Python
jobs still execute their full matrix. No merge, production activation or release-readiness claim.

## Verification on 31 October 2026

Local Python 3.12: 178 tests and 95 subtests passed, zero skipped. Ruff lint/format,
documentation links, fixture byte comparison and strict TypeScript/Vite build passed.
Vitest: 19 component/contract tests passed. Locked `npm ci` reproduced installation.
Full npm audit reported zero vulnerabilities at verification time.

Two Chromium tests were attempted but **did not execute their browser assertions**: the executable
was absent and the browser CDN returned a 195-byte HTML response instead of an archive.
Full Chrome and headless-shell installation attempts failed. Keyboard behavior in jsdom is tested;
actual Chromium, axe contrast/accessibility assertions, visual screenshots and narrow-viewport
checks remain unverified locally. The frontend CI job keeps these checks mandatory; inspect its
exact-head outcome before treating them as passed. This is an explicit validation limit, not a
reason to disable or skip browser tests. No public deployment or production acceptance is claimed.

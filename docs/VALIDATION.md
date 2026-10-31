# Foundation validation

Local checks completed 2026-10-10 with Python 3.12.14:

- Editable installation with development dependencies succeeded.
- `pytest -q`: six tests passed, including JSON Schema validation; four count subtests passed.
- `ruff check .` and `ruff format --check .`: passed.
- `python scripts/check_docs.py`: required files and relative Markdown links passed.
- Installed CLI exported two synthetic findings twice; `cmp` confirmed byte-identical JSON.
- CLI tests verify existing output is not overwritten, invalid counts and duplicate IDs fail,
  collection timestamps include a timezone, and snapshot changes alter finding identity.

GitHub work: existing public repository inspected, Apache-2.0 and ignore file preserved;
dedicated foundation/civictrace branch created; issues #1–#20 created and returned by GitHub.
No pre-existing issues or open PRs were found. BACKLOG.md links every issue and its dependencies.
Native milestones could not be created because no milestone-write tool is available.

Foundation CI will run Python 3.11/3.12/3.13 lint, formatting, tests, docs and deterministic
CLI exports on the published head. Consult the PR checks for its exact live result; local
success is not a claim that remote checks have passed. No real-source pipeline, frontend,
provider deployment or security audit was executed. External links are research references,
not continuously crawled links. Publisher-terms and provisional-name limitations are documented.

## Issue #5 synthetic regression run — 2026-10-28

Base: `69e5b496247131899fc729053d0d074ad213448f` (main). PR #27 is a reviewed design
reference, not the base branch. Python 3.12.14; pytest 9.2.0; ruff 0.17.3;
jsonschema 4.26.0. Existing dev extra installed successfully.

- `python -m pytest -q`: **12 passed, 88 subtests passed**, including 37 edge-case
  datasets, all run twice through the CLI with exact expected results/errors.
- `python -m ruff check .`, `python -m ruff format --check .`,
  `python scripts/check_docs.py`, `git diff --check`: passed.
- Original demo exported twice with collection time `2026-10-10T00:00:00Z`;
  both runs produced two findings and `cmp` passed. Output SHA-256:
  `3acf378be9295e2eb4e4b557d078deef64ddcd96cbe3aafc1bd1b6876eb1f85a`.
- Edge corpus SHA-256:
  `3b89df85a45f30a62d8eb4d2178b688039b8ec65d08e625a6ff6ad3a67c5bfde`.

[Reproduction and case expectations](SYNTHETIC_EDGE_CASES.md). The tests use invented
organization IDs, no network and no raw DNCP rows. No real-source import, live indicator,
concentration calculation or production activation was performed. Hosted checks must be verified
on this PR's own commit; these local results do not inherit PR #27's CI results.

## Canonical v1 (#11)

`PYTHONPATH=backend/src python -m pytest -q` includes the canonical precision/history/linkage
tests and all 37 PR #28 edge cases. `scripts/canonical_example.py` asserts exact joint-award
totals and cancellation exclusion. No real data, source download or personal data is used.

Compatibility baseline: main `69e5b496247131899fc729053d0d074ad213448f`; PR #28
`c41436039e8a45e7d08f4f7e339f05825c08d6e4` is included via a separate merge commit.
PR #27 `415bda798e75f478cb06246a0efc0b744b922fc1` is a pinned design reference only.
PR #26 `5e63f4904607f7c71ad500d9aaeb34eb45f7f0db` remains separate; its intake protections
are not implied by canonical normalization. Compatibility rehearsal in an isolated worktree: PR #27 has one conflict in CURRENT_STATE prose;
retaining this branch's state description gives 22 passed and 95 subtests passed, lint/docs passed.
PR #26 conflicts in evidence.py imports and malformed-record wording inherited from #28.
Combining ingestion limits with synthetic guards and preserving both diagnostic substrings gives
35 passed and 103 subtests passed, lint/docs passed. These are rehearsal-only resolutions; neither
branch is merged here. Recheck when either PR head changes. No source probe was executed.
New hosted CI must be checked on this branch's own commit; other PRs' CI is not inherited.

## Issue #19 synthetic entity filters — 2026-10-31

Incremental base: PR #40, commit `83f24f7a6f60568dbabd6ca453d1e6ec4aed698f`.
Checked latest open PRs, remote branches and #19 before implementation. No existing
entity-search implementation was found; no merge performed.

Local execution on Python 3.12.14 / Node 24.22.1:

- 210 Python tests and 95 subtests passed, no skips (includes five new adapter cases).
- 61 Vitest tests passed (six new cases), including duplicate names/distinct exact IDs,
  case/whitespace/partial-ID negatives, same-entry matching, combined categories/status,
  missing/null data, invalid projections, evidence mismatch, active counts/reset and keyboard.
- Strict TypeScript/Vite build, locked npm ci, Prettier, Ruff lint/format, docs links,
  all three fixture regeneration checks and whitespace checks passed. npm audit: zero findings.
- Invented four-record Parquet fixture regenerated through existing importer, writer,
  full replay verifier and minimized version-2 adapter; bundled SHA-256/snapshot pins updated.
- Playwright suite was invoked: six browser launches failed because Chromium was absent;
  browser download returned an invalid/truncated ZIP. **No local page assertions executed.**
  The existing unchanged hosted CI must independently run the six browser tests, including
  new entity-filter keyboard, axe WCAG A/AA and 375px viewport assertions. Consult the
  draft PR for actual hosted results; this paragraph does not claim browser success.

Reproduce using the commands and exact filter expectations in
[Parquet explorer](PARQUET_EXPLORER.md#buyer-suppliertenderer-and-contract-filters-19).
Synthetic data only; all `analytics_enabled` flags remain false. No live data, merge,
production activation or release-readiness claim.

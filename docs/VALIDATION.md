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

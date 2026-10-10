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

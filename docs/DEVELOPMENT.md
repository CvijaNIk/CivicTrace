# Development
Python 3.11+ is required. Install editable package and dev extra from the root:
`python -m pip install -e ".[dev]"`. Create/activate `.venv` first; Windows PowerShell activation
is `.venv\Scripts\Activate.ps1`. Python-only runtime has no external dependencies.

Run `pytest -q`, `ruff check .`, `ruff format --check .`, `python scripts/check_docs.py`.
Without installed development packages, set PYTHONPATH to backend/src and use
`python -m unittest discover -s tests -v`; the JSON Schema check is skipped without jsonschema.
CI installs the dev extra and must run that check. Keep generated findings outside tracked files.

No frontend is initialized yet; Node tools, Vitest and Playwright are roadmap dependencies.
Do not add a backend HTTP service or accounts merely to show a synthetic demo. Optional data
extra lists future integrations only; its installation does not implement Parquet or DuckDB.
Dependency ranges are bounded; a hashed release lock/environment manifest remains required.

Local package layout, schema and CLI tests run offline after dependency installation. CI has
read-only repository permissions, pinned actions and no privileged fork-PR event. Dependabot
proposes updates; it does not merge them. Current CI checks lint/tests/docs, not a complete
security audit or external HTTP link crawler. Action versions and locks require routine review.

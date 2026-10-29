# DNCP local directory publication and recovery

This change is stacked on PR #30 head `6a35dd757f69a94944c021eefb95e9138dafbdd6`
(and transitively PR #29); neither dependency is merged here. It changes only local filesystem
publication, not public distribution. All fixtures are invented.

## Guarantee and platform boundary

Staging remains a unique private 0700 `.dncp-*` sibling of the intended destination. All evidence,
validation output, manifest and summary are written and closed before one directory rename.
Linux libc `renameat2` with `RENAME_NOREPLACE` publishes the whole directory on the same
filesystem. This operation either installs the complete tree or fails without installing it.
There is no final-directory creation and no individual file movement. A competing destination
entry (directory, file or symlink, even dangling) is never overwritten. Two importers targeting
one path can have at most one winner; the loser cleans only its own staging directory.

Python's portable `Path.rename`/`os.rename` can replace an existing empty directory on POSIX.
An existence check before rename has a race. Neither is an acceptable substitute. This importer
therefore deliberately refuses publication on non-Linux platforms or when libc lacks renameat2.
Kernel/filesystem rejection (including unsupported flags or cross-device errors) also fails closed,
without a fallback. Such a rejection may occur only after validation; staging is then cleaned.
Canonical/demo functionality is unaffected. Import support on Windows/macOS would require a
separately tested native no-replace primitive; this PR does not claim it.

Every existing output-parent component is checked with lstat and must be a directory, not a
symlink. Final links, including dangling ones, are rejected at entry and by the atomic primitive
if created later. Relative paths become absolute. Parents must already exist. The parent tree
must remain private, operator-controlled and stable during the operation. This is not protection
against a hostile same-user/root process replacing ancestor directories, mounts or staged files.
Use a local filesystem honoring Linux rename semantics; network/FUSE filesystem semantics are
not certified. No changes to input SHA-256 checks, gzip CRC/EOF/framing, resource ceilings,
row mapping, provenance, local-only manifest attestations or privacy rules are made.

## Crash states and safe recovery

- Failure or SIGKILL while writing or before rename: destination is absent (or an independently
  created competing entry is untouched). Private staging may remain, with arbitrary partial files
  or even a summary. It is never a completed import and must not be consumed or promoted.
- SIGKILL after rename: the destination contains the entire validated tree. The caller may not
  receive a success response. Inspect the requested destination before retrying; an existing result
  causes a retry to fail rather than overwrite it. A published result is never removed by cleanup.
- Ordinary precommit errors clean staging. If cleanup itself raises OSError, the importer reports
  `private_staging_cleanup_failed` and the exact staging path, with chained error context. It does
  not silently report success. Cleanup may have partially removed staging; it cannot affect final.

Recovery is explicitly manual: stop all writers for the parent, inspect the requested destination,
identify the exact orphan staging directory from the failure or local inspection, confirm it is
an owned directory rather than a symlink, then delete only that orphan under the local retention
policy. Never glob-delete `.dncp-*` while writers are running. Do not infer ownership or completion
from mtime, a staging summary or a filename alone. Do not resume/promote leftovers; rerun from
reviewed original bytes/manifest to a fresh absent destination. An orphan does not block a fresh
run; automatic scavenging is intentionally absent to avoid deleting another process's evidence.
Keep staging, reports and errors private; do not upload them to CI/public artifacts.

Atomic visibility is not power-loss durability. This implementation does not fsync every file and
parent directory; kernel panic, power loss, media corruption and nonconforming filesystem behavior
are outside the guarantee. No portable transactional disk durability is claimed.

## Reproduction and evidence

From the repository root on Linux with Python 3.11+ and installed dev dependencies:

```sh
PYTHONPATH=backend/src python -m pytest tests/test_dncp_publication.py -q
PYTHONPATH=backend/src python -m pytest -q -rs
python -m ruff check .
python -m ruff format --check .
python scripts/check_docs.py
PYTHONPATH=backend/src python scripts/canonical_example.py
```

Tests inject mkdir/open failures, partial raw/canonical/manifest/summary writes, final publication
failure, cleanup refusal, missing libc support and kernel/filesystem errors. They preserve existing
empty/complete directories, files and live/dangling links; simulate destination creation at commit;
reject a symlink parent; synchronize two concurrent importers at the commit boundary; and kill
real subprocesses with SIGKILL during a partial write, immediately before and immediately after
rename. No timing sleeps or actual source downloads are used. The standalone per-file-move
regression reproduces PR #30's partial-directory defect without a production fault hook.

Local results are recorded in [the validation log](DNCP_IMPORT_VALIDATION.md). Hosted matrix
results must be verified on this PR's exact commit; prior PR CI is not evidence for this change.

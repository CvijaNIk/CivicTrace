# DNCP offline synthetic resource experiment

This implements the measured-workload part of issue #1 on PR #31's exact importer
`f40b41f279f0ee9f81e8cdc86845dc5661458111`. No actual DNCP database is downloaded.
All records and observations concern invented workloads, not public procurement findings.
See [ADR 0002](adr/0002-measured-dncp-workload-budgets.md) for decisions and alternatives.

## Reproduce

Linux with `/proc`, Python 3.11+, a local filesystem supporting `renameat2(RENAME_NOREPLACE)`,
and a private operator-controlled work parent are required. Install the repository and dev
requirements as in [development](DEVELOPMENT.md). The benchmark itself uses only the standard
library. Do not run concurrent importers/tests while collecting comparison timings.

```sh
python -m pip install -e '.[dev]'
python scripts/benchmark_dncp.py --output /tmp/dncp-smoke-results.json
python scripts/benchmark_dncp.py --full --repeats 1 --timeout 900 --output /tmp/dncp-full-results.json
python scripts/benchmark_dncp.py --case small --case medium --repeats 3 --output /tmp/dncp-repeat-results.json
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python scripts/check_docs.py
```

`--case` can select any named workload; full-only names need `--full`. `--work-dir` selects an
existing private local parent; otherwise system temporary storage is used. Allow at least
12 GiB and 120,000 free inodes for this particular suite and review free space first. These are
experiment provisioning recommendations, not proven importer worst-case output budgets.
Fixtures and outputs are deleted between passes; only metrics/hashes/parameters are retained.
Each worker has a 900-second default timeout; a timeout/nonzero exit/unexpected result stops
the suite, cleans its temporary tree and leaves only the last completed-case checkpoint.
Large profiles are explicit opt-in and are not run as ordinary CI timing assertions.

## Method

The streaming generator builds one invented JSONL row at a time. Identifiers vary for every
row and child. Compact rows contain a party and award; missing-value rows omit the date and
award value and include a null tenderer count; malformed rows alternate invalid syntax and
duplicate keys. Dense rows have 4,000 parties and 4,000 linked awards each. Padded rows have
an exact byte width, including newline. A 16 KiB SHAKE-256-derived hexadecimal block repeats
inside an otherwise ignored field, balancing compression against the 200:1 expansion ceiling.
Gzip has an empty filename and mtime zero; expanded/compressed SHA-256 and exact byte counts
are recorded. Identical Python/zlib versions produce identical fixture bytes; gzip encoding
across library versions is not promised, so the expanded hash is also supplied.

The full expanded-boundary fixture is exactly 1,024 lines of 2 MiB, totaling 2 GiB; overflow
adds one line. The compressed fixtures use gzip level 0 and a legal FCOMMENT header to reach
exactly 256 MiB and 256 MiB + 1 byte without violating expanded/line/row limits. This tests
that compressed ceiling independently; it does not model a typical annual dataset. The
ratio-rejection case uses highly repeated padding. All other compression levels are in JSON.

Generation/hashing of fixtures is outside timing and outside the worker. A **fresh executable
Python subprocess for every pass** avoids generator allocations and previous-import high water.
The first untraced pass records `perf_counter` elapsed time around `import_file`, including
source snapshot copying/hashing, parse/mapping, output writes, publication and fatal cleanup.
Interpreter startup and successful-output disk enumeration are excluded. Linux `/proc/self/status`
`VmHWM` gives process-lifetime peak RSS in bytes (kernel KiB converted by 1,024); `VmRSS` before
import is the baseline. RSS includes interpreter/native/allocator memory, not filesystem cache,
whole-system usage or cgroup totals. No polling interval can miss a short RSS peak here; this
relies on the kernel's process high-water accounting. The harness has its own import overhead.

A separate fresh pass starts `tracemalloc` immediately before import and records peak traced
Python allocations. Its RSS/time are retained but never substituted for untraced performance.
Tracing adds memory and CPU cost and excludes untracked native allocations, pre-start objects,
kernel buffers and page cache. RSS minus traced bytes is not a reliable native-memory estimate.
No generator, fixture compression or fixture SHA calculation is part of reported import speed.

Disk accounting sums regular output-file `st_size` and `st_blocks * 512`, plus a separate
output-directory block count. This is filesystem allocation accounting, not physical device
writes, quota usage, inode metadata or a power-loss durability claim. Allocated blocks are
observed at those milestones, not continuously sampled physical peak allocation; filesystem
preallocation, delayed allocation, copy-on-write and shared extents can change their meaning. The importer only adds
files/appends before success/cleanup: successful output is measured after publication; fatal
output is measured immediately before `rmtree` via a benchmark-only wrapper. Failure timing
therefore includes this directory scan. Empty/no-staging failures may have no disk observation.
The source fixture is additional disk space (add `fixture.compressed_bytes`); it is not counted
twice in output metrics. The source snapshot retained inside output **is** included.

Successful throughput is expanded input MiB/s and input rows/s, including rejected JSON rows
when a complete validation report was published. Fatal rejections have no completed-import
throughput. No cold-cache procedure is used: generated input is warm and repeated trials
benefit from filesystem/allocator behavior. Single full-suite trials are observations, with
no statistical confidence interval, p95, linear-scaling assumption or hardware-independent SLA.

## Expected behavior

Small/medium/unique/long/dense/compressed/expanded valid cases accept every row. The missing
case accepts rows and quarantines each missing-value award while preserving unknown field
states. The malformed case publishes a complete report with all rows rejected. Corrupt gzip
returns `invalid_gzip`; exceeded rows/line/compressed size return `row_limit`, `line_limit`,
`compressed_limit`; expanded/ratio excess returns `expanded_limit`. Fatal cases publish no
final output and leave no private staging orphan. The runner checks these expectations in
both passes, and raises on unexpected publication, counts, errors or cleanup.

## Recorded observations

See [raw full-suite results](evidence/dncp-benchmark-2026-10-29/results.json) and the dated
[measurement report](evidence/dncp-benchmark-2026-10-29/README.md). Environment versions,
importer source digest, fixture digests, exact sizes, summaries, repeat indices and all raw
measurements are retained. Reported RSS is an empirical observation, never a guaranteed cap.

The benchmark does not replace source authenticity/legal review, actual-source quality
sampling, adversarial fuzzing, hosted Python-version CI, filesystem certification or a
production pilot. Existing [atomic publication limits](DNCP_PUBLICATION.md), privacy decisions
and provenance requirements still apply unchanged. No input limit is raised or lowered by
this change; see ADR 0002 for why the available measurements do not justify a universal cap.

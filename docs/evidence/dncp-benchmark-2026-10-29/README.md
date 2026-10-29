# Synthetic DNCP resource measurements — 2026-10-29

Only invented workloads; no DNCP source download, no actual procurement findings.
See [method and reproduction](../../DNCP_BENCHMARK.md) and [ADR 0002](../../adr/0002-measured-dncp-workload-budgets.md).

## Environment and execution

Python 3.12.14 (Clang 22.1.3), Linux 6.18.55 x86_64, glibc 2.39, zlib 1.3.2;
AMD EPYC 9V74, nine visible CPUs, cgroup CPU quota eight CPUs and memory ceiling 8 GiB.
Local overlay filesystem, 4 KiB pages. No CPU affinity, cold-cache reset or durability flush.
No other project tests/imports ran concurrently with the recorded trials; shared-host load is uncontrolled.
pytest 9.2.0, ruff 0.17.3, jsonschema 4.26.0 were used for validation. No benchmark dependencies added.

[Core raw observations](results.json): 11 cases, one fresh untraced and one fresh traced worker each.
The core harness is preserved at [commit cd1c4d2](https://github.com/CvijaNIk/CivicTrace/blob/cd1c4d2451907d746cb2365d84941096d08ad32c/scripts/benchmark_dncp.py).
[Byte-boundary observations](byte-boundaries.json): four additional cases using the refined level-6
expanded-byte recipe. [Repeated observations](repeats.json): three runs per mode for small/medium.
Each JSON stores its harness SHA-256, importer SHA-256, environment, parameters and fixture hashes.
These are separate runs totaling 15 distinct cases and 42 measured imports, not a single uninterrupted trial.
Importer code is unchanged from PR #31 commit `f40b41f279f0ee9f81e8cdc86845dc5661458111`.

## Duration and throughput

Times/rates below use only untraced passes. Fatal cases have no completed-import throughput.
Rates use expanded JSONL bytes and input rows, not compressed bytes or output bytes.

| Case | JSONL MiB | Result | Seconds | MiB/s | Rows/s |
| --- | ---: | --- | ---: | ---: | ---: |
| small | 0.033 | published | 0.074 | 0.45 | 1357.56 |
| medium | 1.716 | published | 2.966 | 0.58 | 1685.51 |
| child-fanout | 1.177 | published | 0.976 | 1.21 | 2.05 |
| ratio-overflow | 2.000 | expanded_limit | 0.003 | — | — |
| unique-row-boundary | 17.399 | published | 26.482 | 0.66 | 1888.10 |
| row-overflow | 17.400 | row_limit | 40.907 | — | — |
| missing | 0.291 | published | 0.902 | 0.32 | 1108.88 |
| malformed | 0.019 | published; all rows rejected | 0.115 | 0.16 | 8713.65 |
| long-line-boundary | 8.000 | published | 0.314 | 25.49 | 12.74 |
| long-line-overflow | 2.000 | line_limit | 0.017 | — | — |
| corrupt-gzip | 0.033 | invalid_gzip | 0.001 | — | — |
| expanded-boundary | 2048.000 | published | 78.216 | 26.18 | 13.09 |
| expanded-overflow | 2050.000 | expanded_limit | 78.368 | — | — |
| compressed-boundary | 255.875 | published | 11.246 | 22.75 | 11.38 |
| compressed-overflow | 255.875 | compressed_limit | 0.300 | — | — |

## Memory and disk

RSS is process-lifetime kernel VmHWM; Python peak is from a separate traced pass.
Allocated file space excludes directory blocks, inode metadata and the external fixture.
Directory block observations are separate in raw JSON. Fatal rows show private staging before
cleanup; all fatal cases ended without final output or private orphans. Failure observers can
add RSS/allocations/time, so their peaks are not clean importer-only measurements.

| Case | RSS untraced MiB | RSS traced MiB | Python peak MiB | Allocated files MiB | Files |
| --- | ---: | ---: | ---: | ---: | ---: |
| small | 18.00 | 18.38 | 0.71 | 1.25 | 204 |
| medium | 19.14 | 20.16 | 1.71 | 62.08 | 10,004 |
| child-fanout | 86.97 | 164.66 | 63.88 | 18.74 | 8 |
| ratio-overflow | 18.26 | 18.51 | 0.94 | 0.00 | 2 |
| unique-row-boundary | 24.59 | 29.61 | 6.32 | 620.76 | 100,004 |
| row-overflow | 44.59 | 67.94 | 25.11 | 620.75 | 100,002 |
| missing | 18.08 | 18.50 | 0.90 | 8.35 | 2,004 |
| malformed | 17.88 | 18.17 | 0.52 | 4.10 | 1,004 |
| long-line-boundary | 31.41 | 31.80 | 10.72 | 17.38 | 12 |
| long-line-overflow | 21.51 | 21.76 | 4.10 | 0.29 | 2 |
| corrupt-gzip | 17.55 | 17.82 | 0.13 | 0.00 | 2 |
| expanded-boundary | 34.01 | 37.88 | 11.43 | 4129.02 | 2,052 |
| expanded-overflow | 34.00 | 37.77 | 11.43 | 4125.02 | 2,048 |
| compressed-boundary | 31.51 | 33.79 | 11.24 | 768.60 | 260 |
| compressed-overflow | 17.47 | 17.75 | 0.15 | 256.00 | 1 |

## Repeat variability

Three samples are insufficient for a percentile/SLA claim. All inputs were recently generated
and therefore warm; compare like-for-like shapes and modes.

| Case | Untraced seconds min / median / max | Untraced RSS MiB min–max | Traced Python peak MiB max |
| --- | ---: | ---: | ---: |
| small | 0.101 / 0.105 / 0.109 | 18.00–18.00 | 0.71 |
| medium | 3.121 / 4.076 / 4.090 | 19.02–19.03 | 1.70 |

## Interpretation and decisions

- Exact 50,000 rows, 2 MiB lines, 256 MiB compressed and 2 GiB expanded inputs passed.
  Independent exceeded row/line/compressed/expanded/ratio cases failed with expected reasons.
  The compressed overflow is exactly one byte; the expanded overflow adds one 2 MiB line.
- The maximum expanded fixture has 1,024 accepted rows and produces 2,052 files occupying
  about 4.03 GiB of allocated file space, plus its 24.32 MiB external compressed fixture.
  Compact 50,000-row input produces 100,004 files and about 621 MiB allocated file space.
- Dense child graphs dominate successful RSS: about 87 MiB untraced, despite only 1.18 MiB
  of total JSONL input. Its traced Python peak is about 64 MiB; the old 2,000-row/16 MiB
  Python-allocation regression cannot be generalized to this shape or to RSS.
- Missing-value rows were accepted with awards quarantined and dates remaining absent.
  Malformed rows were all rejected while a complete validation report was published.
  Corrupt gzip and all resource-limit failures published nothing; orphan counts were zero.
- Keep existing input ceilings unchanged. These tested shapes and boundary rejections support
  the present experimental contract, not a worst-case RSS/disk proof. Input limits alone do
  not guarantee laptop safety for every legal structure. Preserve operator quotas/OS memory
  isolation where a hard budget is needed; browser DNCP intake remains unimplemented.
- Tracing overhead, warm caches, filesystem allocation semantics, single full trials, limited
  shape diversity and one OS/Python/hardware environment constrain interpretation. RSS excludes
  page cache and whole-cgroup memory. No real-source throughput or production SLA is claimed.

## Validation

Local final validation: 82 tests and 88 subtests passed with no skips, including 12 harness tests,
existing canonical/provenance tests and all atomic-publication/crash/concurrency regressions.
Ruff lint/format, relative documentation links, canonical example digest and diff checks passed.
The canonical example remains `7bff863869a9001715019ddf5e0ea3c906f760b9495d70749604fb292f33de40`.
Hosted CI must be checked independently on the final PR commit; local measurements do not
establish hosted performance or certify Python 3.11/3.13 resource usage.

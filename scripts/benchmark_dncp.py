"""Offline synthetic DNCP resource experiment (Linux, Python standard library only)."""

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import tracemalloc
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))
from civictrace import dncp  # noqa: E402


@dataclass(frozen=True)
class Case:
    name: str
    rows: int
    width: int = 0  # exact JSONL line bytes including newline; zero means natural size
    mode: str = "valid"
    compression: int = 1
    expected_error: str | None = None


def cases(full=False):
    result = [
        Case("small", 100),
        Case("medium", 5000),
        Case("child-fanout", 2, mode="fanout"),
        Case(
            "ratio-overflow",
            1,
            dncp.Limits().line,
            mode="compressible",
            compression=9,
            expected_error="expanded_limit",
        ),
        Case("unique-row-boundary", 50000),
        Case("row-overflow", 50001, expected_error="row_limit"),
        Case("missing", 1000, mode="missing"),
        Case("malformed", 1000, mode="malformed"),
        Case("long-line-boundary", 4, dncp.Limits().line),
        Case("long-line-overflow", 1, dncp.Limits().line + 1, expected_error="line_limit"),
        Case("corrupt-gzip", 100, mode="corrupt", expected_error="invalid_gzip"),
    ]
    if full:
        # 2 GiB exactly; only 1024 rows so the line and row ceilings are independent.
        result += [
            Case("expanded-boundary", 1024, dncp.Limits().line),
            Case("expanded-overflow", 1025, dncp.Limits().line, expected_error="expanded_limit"),
            # Level 0 plus an ignored whitespace suffix gives exact compressed sizes.
            Case("compressed-boundary", 128, dncp.Limits().line - 1024, mode="compressed"),
            Case(
                "compressed-overflow",
                128,
                dncp.Limits().line - 1024,
                mode="compressed-overflow",
                expected_error="compressed_limit",
            ),
        ]
    return result


def line(case, i):
    record = {
        "ocid": f"ocds-03ad3f-SYNTHETIC-{i:08d}",
        "id": f"INVENTED-r{i}",
        "tag": ["compiled"],
        "date": "2026-01-01T00:00:00Z",
        "tender": {"id": f"INVENTED-t{i}", "status": "complete"},
        "parties": [{"id": f"INVENTED-p{i}"}],
        "awards": [
            {
                "id": f"INVENTED-a{i}",
                "status": "active",
                "value": {"amount": "123.45", "currency": "PYG"},
                "suppliers": [{"id": f"INVENTED-p{i}"}],
            }
        ],
    }
    if case.mode == "fanout":
        record["parties"] = [{"id": f"INVENTED-p{i}-{j}"} for j in range(4000)]
        record["awards"] = [
            {
                "id": f"INVENTED-a{i}-{j}",
                "status": "active",
                "value": {"amount": "123.45", "currency": "PYG"},
                "suppliers": [{"id": f"INVENTED-p{i}-{j}"}],
            }
            for j in range(4000)
        ]
    if case.mode == "missing":
        record.pop("date")
        record["awards"][0].pop("value")  # child quarantine, never zero imputation
        record["tender"]["numberOfTenderers"] = None
    if case.mode == "malformed":
        return b'{"duplicate":1,"duplicate":2}\n' if i % 2 else b"{invalid\n"
    record["synthetic_padding"] = ""
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    if case.width:
        n = case.width - len(raw)
        if n < 0:
            raise ValueError("width_too_small")
        # A 16 KiB deterministic hex block repeats: <200:1 expansion even at 2 MiB.
        block = hashlib.shake_256(f"SYNTHETIC/{i}".encode()).hexdigest(8192).encode()
        padding = (block * ((n + len(block) - 1) // len(block)))[:n]
        if case.mode == "compressible":
            padding = b"A" * n
        raw = raw.replace(b'"synthetic_padding":""', b'"synthetic_padding":"' + padding + b'"')
    return raw


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def pad_gzip_header(source, target):
    size = source.stat().st_size
    # Insert FCOMMENT into the gzip header; streaming importer need not buffer it.
    gap = target - size
    if gap < 1:
        raise ValueError("compressed_fixture_too_large")
    temp = source.with_suffix(".header.tmp")
    with source.open("rb") as src, temp.open("wb") as dst:
        header = bytearray(src.read(10))
        header[3] |= 16
        dst.write(header)
        for start in range(0, gap - 1, 65536):
            dst.write(b"S" * min(65536, gap - 1 - start))
        dst.write(b"\0")
        shutil.copyfileobj(src, dst)
    temp.replace(source)


def generate(directory, case):
    source = directory / "synthetic.jsonl.gz"
    expanded_hash, expanded = hashlib.sha256(), 0
    with source.open("wb") as f:
        with gzip.GzipFile(
            filename="",
            fileobj=f,
            mode="wb",
            mtime=0,
            compresslevel=0 if case.mode.startswith("compressed") else case.compression,
        ) as gz:
            for i in range(case.rows):
                raw = line(case, i)
                gz.write(raw)
                expanded_hash.update(raw)
                expanded += len(raw)
    if case.mode.startswith("compressed"):
        target = dncp.Limits().compressed + (case.mode == "compressed-overflow")
        pad_gzip_header(source, target)
    if case.mode == "corrupt":
        with source.open("r+b") as f:
            f.seek(-8, 2)
            f.write(b"BAD!CRC!")
    manifest = {
        k: "SYNTHETIC benchmark; invented data, no source acquisition"
        for k in (
            "adapter_version intermediary snapshot_version partition selection terms_evidence "
            "attribution changes exclusions privacy_review registry_unknown_reason"
        ).split()
    }
    manifest.update(
        contract_version="dncp-local/1",
        publisher="DNCP",
        publication_id="63",
        source_url="urn:synthetic:dncp-benchmark",
        resolved_url="urn:synthetic:dncp-benchmark",
        retrieved_at="2026-01-01T00:00:00Z",
        compressed_sha256=digest(source),
        expanded_sha256=expanded_hash.hexdigest(),
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        redistribution_decision="local-only",
        access_review="confirmed",
    )
    (directory / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
    return {
        "compressed_bytes": source.stat().st_size,
        "expanded_bytes": expanded,
        "compressed_sha256": manifest["compressed_sha256"],
        "expanded_sha256": manifest["expanded_sha256"],
    }


def disk(path):
    result = {
        "logical_bytes": 0,
        "allocated_bytes": 0,
        "files": 0,
        "directory_allocated_bytes": path.stat().st_blocks * 512,
    }
    for p in path.iterdir():
        s = p.stat()
        result["logical_bytes"] += s.st_size
        result["allocated_bytes"] += s.st_blocks * 512
        result["files"] += 1
    return result


def proc_memory():
    values = dict(x.split(":", 1) for x in Path("/proc/self/status").read_text().splitlines())
    return {k: int(values[k].split()[0]) * 1024 for k in ("VmRSS", "VmHWM")}


def worker(directory, traced):
    source, output = directory / "synthetic.jsonl.gz", directory / "output"
    manifest = json.loads((directory / "manifest.json").read_text())
    baseline = proc_memory()
    usage = {}
    original = dncp.shutil.rmtree

    def cleanup(path, *args, **kwargs):
        usage.update(disk(Path(path)))  # all importer writes are append/create until cleanup
        return original(path, *args, **kwargs)

    dncp.shutil.rmtree = cleanup
    if traced:
        tracemalloc.start()
    started = time.perf_counter()
    error, summary = None, None
    try:
        summary = dncp.import_file(source, output, manifest)
    except dncp.IntakeError as exc:
        error = str(exc)
    elapsed = time.perf_counter() - started
    peak = tracemalloc.get_traced_memory()[1] if traced else None
    if traced:
        tracemalloc.stop()
    memory = proc_memory()
    if output.exists():
        usage = disk(output)
    result = {
        "traced": traced,
        "elapsed_seconds": elapsed,
        "python_peak_bytes": peak,
        "rss_baseline_bytes": baseline["VmRSS"],
        "rss_hwm_bytes": memory["VmHWM"],
        "disk_output_high_water": usage,
        "error": error,
        "summary": summary,
        "published": output.exists(),
        "private_orphans": len(list(directory.glob(".dncp-*"))),
    }
    print(json.dumps(result, sort_keys=True))


def run_case(directory, case, repeats=1, timeout=900):
    directory.mkdir(mode=0o700)
    fixture = generate(directory, case)
    measurements = []
    for traced in (False, True):
        for repeat in range(repeats):
            p = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--worker",
                    str(directory),
                    *(["--traced"] if traced else []),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
                env={**os.environ, "PYTHONHASHSEED": "0"},
            )
            m = json.loads(p.stdout)
            if m["error"] != case.expected_error or m["private_orphans"]:
                raise RuntimeError(f"unexpected result for {case.name}: {m}")
            if m["published"] != (case.expected_error is None):
                raise RuntimeError("publication expectation failed")
            if m["summary"]:
                expected = 0 if case.mode == "malformed" else case.rows
                if m["summary"]["accepted"] != expected or m["summary"]["rows"] != case.rows:
                    raise RuntimeError("accepted row expectation failed")
            m["repeat"] = repeat
            m["input_mib_per_second"] = (
                fixture["expanded_bytes"] / 2**20 / m["elapsed_seconds"] if m["published"] else None
            )
            m["input_rows_per_second"] = (
                case.rows / m["elapsed_seconds"] if m["published"] else None
            )
            m["throughput_is_complete_import"] = m["published"]
            measurements.append(m)
            if (directory / "output").exists():
                shutil.rmtree(directory / "output")
    return {"case": asdict(case), "fixture": fixture, "measurements": measurements}


def optional_text(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    p.add_argument("--traced", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--full", action="store_true")
    p.add_argument("--case", action="append", help="Run only these named cases")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--timeout", type=int, default=900, help="Seconds per worker")
    p.add_argument(
        "--work-dir", type=Path, help="Existing private local parent with free disk space"
    )
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if sys.platform != "linux":
        p.error("Linux /proc and atomic renameat2 required")
    if a.worker:
        worker(a.worker, a.traced)
        return
    if a.repeats < 1 or a.timeout < 1 or not a.output:
        p.error("positive repeats/timeout and --output required")
    selected = [c for c in cases(a.full) if not a.case or c.name in a.case]
    if not selected or (a.case and set(a.case) - {c.name for c in selected}):
        p.error("unknown case (full cases require --full)")
    result = {
        "schema": "dncp-synthetic-benchmark/1",
        "synthetic_only": True,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "zlib": zlib.ZLIB_RUNTIME_VERSION,
            "cpu_count": os.cpu_count(),
            "cpu_model": next(
                (
                    x.split(":", 1)[1].strip()
                    for x in Path("/proc/cpuinfo").read_text().splitlines()
                    if x.startswith("model name")
                ),
                None,
            ),
            "cgroup_memory_max": optional_text("/sys/fs/cgroup/memory.max"),
            "cgroup_cpu_max": optional_text("/sys/fs/cgroup/cpu.max"),
            "page_size": os.sysconf("SC_PAGE_SIZE"),
            "mem_total": next(
                (
                    x.split(":", 1)[1].strip()
                    for x in Path("/proc/meminfo").read_text().splitlines()
                    if x.startswith("MemTotal:")
                ),
                None,
            ),
            "packages": {n: importlib.metadata.version(n) for n in ("civictrace",)},
        },
        "importer_sha256": digest(Path(dncp.__file__)),
        "harness_sha256": digest(Path(__file__)),
        "limits": asdict(dncp.Limits()),
        "results": [],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    for case in selected:
        with tempfile.TemporaryDirectory(prefix="dncp-bench-", dir=a.work_dir) as tmp:
            result["results"].append(run_case(Path(tmp) / "case", case, a.repeats, a.timeout))
        # Checkpoint completed cases; interrupted suite never claims full completion.
        checkpoint = a.output.with_suffix(a.output.suffix + ".tmp")
        checkpoint.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        checkpoint.replace(a.output)
        print(case.name, "complete", flush=True)


if __name__ == "__main__":
    main()

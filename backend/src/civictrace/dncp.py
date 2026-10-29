"""Bounded, offline DNCP compiled-release intake. No network or publication capability."""

import argparse
import ctypes
import errno
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import zlib
from copy import deepcopy
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from .canonical import normalize, serialize
from .synthetic import instant


@dataclass(frozen=True)
class Limits:
    compressed: int = 256 * 1024 * 1024
    expanded: int = 2 * 1024 * 1024 * 1024
    rows: int = 50_000
    line: int = 2 * 1024 * 1024
    depth: int = 32
    ratio: int = 200


class IntakeError(ValueError):
    """Fatal intake error: no output directory is published."""


def validate_manifest(m):
    required = (
        "adapter_version publisher intermediary publication_id source_url resolved_url "
        "snapshot_version partition retrieved_at compressed_sha256 expanded_sha256 "
        "selection license_id license_url terms_evidence attribution changes exclusions "
        "privacy_review registry_unknown_reason"
    ).split()
    for key in required:
        if not m.get(key):
            raise IntakeError("manifest_missing_" + key)
    if m.get("contract_version") != "dncp-local/1":
        raise IntakeError("manifest_version")
    if m.get("redistribution_decision") != "local-only":
        raise IntakeError("local_only_required")
    if m.get("access_review") != "confirmed":
        raise IntakeError("access_review_required")
    if m["publisher"] != "DNCP" or str(m["publication_id"]) != "63":
        raise IntakeError("manifest_source")
    if m["license_id"] != "CC-BY-4.0":
        raise IntakeError("manifest_license")
    instant(m["retrieved_at"])
    if m.get("registry_retrieved_at") is not None:
        instant(m["registry_retrieved_at"])
    for key in ("compressed_sha256", "expanded_sha256"):
        if len(m[key]) != 64 or any(c not in "0123456789abcdef" for c in m[key]):
            raise IntakeError("manifest_hash")


def parse(raw, depth):
    # Check nesting before constructing Python objects (including hostile nested inputs).
    level, quoted, escaped = 0, False, False
    for c in raw.decode("utf-8"):
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c in "[{":
            level += 1
            if level > depth:
                raise ValueError("depth_limit")
        elif c in "]}":
            level -= 1

    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("duplicate_json_key")
            result[k] = v
        return result

    def number(s):
        if len(s) > 128:
            raise ValueError("numeric_limit")
        return Decimal(s)

    def integer(s):
        if len(s) > 128:
            raise ValueError("numeric_limit")
        return int(s)

    def constant(s):
        raise ValueError("nonfinite_number")

    return json.loads(
        raw, object_pairs_hook=pairs, parse_float=number, parse_int=integer, parse_constant=constant
    )


def prepare(record):
    if not isinstance(record, dict):
        raise ValueError("release_object_required")
    for value in (record.get("ocid"), record.get("id"), (record.get("tender") or {}).get("id")):
        if not isinstance(value, str) or not value.strip() or len(value) > 4096:
            raise ValueError("required_identity")
    if not record["ocid"].startswith("ocds-03ad3f-") or "compiled" not in record.get("tag", []):
        raise ValueError("compiled_dncp_required")
    result, rejects = deepcopy(record), []
    party_ids, award_ids = set(), set()
    for table in ("parties", "awards", "contracts"):
        children = result.get(table, [])
        if not isinstance(children, list):
            raise ValueError("child_array_required")
        kept, seen = [], set()
        for i, child in enumerate(children):
            reason = None
            cid = child.get("id") if isinstance(child, dict) else None
            if not isinstance(cid, str) or not cid.strip() or len(cid) > 4096:
                reason = "child_identity"
            elif cid in seen:
                reason = "duplicate_child"
            else:
                seen.add(cid)
                if table == "contracts" and child.get("awardID") not in award_ids:
                    reason = "contract_linkage"
                if table == "awards":
                    suppliers = child.get("suppliers", [])
                    if not isinstance(suppliers, list) or any(
                        not isinstance(s, dict) or s.get("id") not in party_ids for s in suppliers
                    ):
                        reason = "supplier_linkage"
                if table != "parties" and (
                    "value" not in child or not isinstance(child["value"], dict)
                ):
                    reason = "child_value"
            if reason:
                rejects.append({"pointer": f"/{table}/{i}", "reason": reason})
            else:
                kept.append(child)
                if table == "parties":
                    party_ids.add(cid)
                elif table == "awards":
                    award_ids.add(cid)
        result[table] = kept
    return result, rejects


def _publisher():
    """Return the Linux atomic no-replace primitive, or fail closed."""
    if sys.platform != "linux":
        raise IntakeError("atomic_publication_unsupported")
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise IntakeError("atomic_publication_unsupported")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int

    def publish(stage, output):
        # RENAME_NOREPLACE: one namespace operation; even an empty directory or
        # dangling symlink at the destination must never be replaced.
        if rename(-100, os.fsencode(stage), -100, os.fsencode(output), 1):
            code = ctypes.get_errno()
            if code in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
                raise IntakeError("atomic_publication_unsupported")
            raise OSError(code, os.strerror(code), str(output))

    return publish


def _destination(output):
    # Reject symlinks in every existing component, including dangling final links.
    # The parent must remain operator-controlled for the duration of the import.
    output = Path(os.path.abspath(output))
    for parent in reversed(output.parents):
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise IntakeError("output_parent_not_directory")
    if os.path.lexists(output):
        raise IntakeError("output_exists")
    return output


def import_file(source, output, manifest, limits=Limits()):
    """Publish a new private evidence directory only after full hash and gzip validation.

    Memory scales with one bounded line/model, not the annual file. Raw rows and each
    model are separate files; duplicate tracking is bounded by the hard row ceiling.
    """
    validate_manifest(manifest)
    if any(
        type(v) is not int or v < 1 or v > asdict(Limits())[k] for k, v in asdict(limits).items()
    ):
        raise IntakeError("invalid_limits")
    source, output = Path(source), _destination(output)
    publish = _publisher()
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stage = None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or not source.name.endswith(".jsonl.gz"):
            raise IntakeError("regular_jsonl_gzip_required")
        stage = Path(tempfile.mkdtemp(prefix=".dncp-", dir=output.parent))
        # Snapshot exact compressed bytes first; no TOCTOU between hashing and parsing.
        h, size = hashlib.sha256(), 0
        with (
            os.fdopen(fd, "rb", closefd=False) as src,
            (stage / "source.jsonl.gz").open("wb") as dst,
        ):
            while chunk := src.read(min(65536, limits.compressed - size + 1)):
                size += len(chunk)
                if size > limits.compressed:
                    raise IntakeError("compressed_limit")
                h.update(chunk)
                dst.write(chunk)
        if h.hexdigest() != manifest["compressed_sha256"]:
            raise IntakeError("compressed_hash")
        dec, expanded, pending = zlib.decompressobj(31), 0, b""
        eh, seen, rows, accepted = hashlib.sha256(), set(), 0, 0
        report = (stage / "validation.jsonl").open("w", encoding="utf-8")

        def row(raw):
            nonlocal rows, accepted
            rows += 1
            if rows > limits.rows:
                raise IntakeError("row_limit")
            rh = hashlib.sha256(raw).hexdigest()
            stem = f"{rows:06d}-{rh}"
            (stage / (stem + ".raw")).write_bytes(raw)
            entry = {"line": rows, "raw_sha256": rh}
            try:
                record = parse(raw, limits.depth)
                cleaned, rejects = prepare(record)
                if hashlib.sha256(record["ocid"].encode()).digest() in seen:
                    raise ValueError("duplicate_ocid")
                seen.add(hashlib.sha256(record["ocid"].encode()).digest())
                provenance = {
                    "snapshot_sha256": h.hexdigest(),
                    "record_sha256": rh,
                    "source_reference": manifest["resolved_url"],
                    "license": manifest["license_id"],
                    "attribution": manifest["attribution"],
                    "privacy_review": manifest["privacy_review"],
                    "adapter_version": manifest["adapter_version"],
                    "collected_at": manifest["retrieved_at"],
                    "line": rows,
                }
                model = normalize([cleaned], provenance)
                # Normalizer pointers refer to the sanitized view. Keep an explicit original
                # child pointer map so quarantine never silently shifts source provenance.
                model["releases"][0]["source_record"] = deepcopy(record)
                model["intake"] = {"quarantined": rejects, "raw_file": stem + ".raw"}
                for table in ("awards", "contracts"):
                    originals = record.get(table, [])
                    pointers = {}
                    for i, c in enumerate(originals):
                        if isinstance(c, dict) and isinstance(c.get("id"), str):
                            pointers.setdefault(c["id"], f"/{table}/{i}")
                    for child in model[table]:
                        old, new = child["pointer"], pointers[child["source_id"]]

                        def repoint(obj):
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    if key == "pointer" and isinstance(value, str):
                                        obj[key] = (
                                            new + value[len(old) :]
                                            if value.startswith(old)
                                            else value
                                        )
                                    else:
                                        repoint(value)
                            elif isinstance(obj, list):
                                for value in obj:
                                    repoint(value)

                        repoint(child)
                observations = []

                def observe(obj):
                    if isinstance(obj, dict):
                        if "state" in obj and "pointer" in obj:
                            observations.append(
                                {k: obj[k] for k in ("state", "pointer", "reason") if k in obj}
                            )
                        for value in obj.values():
                            observe(value)
                    elif isinstance(obj, list):
                        for value in obj:
                            observe(value)

                observe({k: v for k, v in model.items() if k != "intake"})
                entry["fields"] = observations
                (stage / (stem + ".canonical.json")).write_text(serialize(model), encoding="utf-8")
                entry.update(status="accepted", quarantined=rejects)
                accepted += 1
            except (ValueError, TypeError, AttributeError, KeyError, RecursionError) as exc:
                entry.update(status="rejected", reason=type(exc).__name__ + ":" + str(exc)[:160])
            report.write(json.dumps(entry, sort_keys=True) + "\n")

        try:
            with (stage / "source.jsonl.gz").open("rb") as src:
                while chunk := src.read(65536):
                    if dec.eof:
                        raise IntakeError("trailing_or_concatenated_gzip")
                    while chunk:
                        data = dec.decompress(chunk, min(65536, limits.expanded - expanded + 1))
                        chunk = dec.unconsumed_tail
                        expanded += len(data)
                        if expanded > limits.expanded or expanded > size * limits.ratio:
                            raise IntakeError("expanded_limit")
                        eh.update(data)
                        pending += data
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            if len(line) + 1 > limits.line:
                                raise IntakeError("line_limit")
                            row(line + b"\n")
                        if len(pending) > limits.line:
                            raise IntakeError("line_limit")
                        if dec.unused_data:
                            raise IntakeError("trailing_or_concatenated_gzip")
            if not dec.eof:
                raise IntakeError("truncated_gzip")
            if pending:
                row(pending)
            if eh.hexdigest() != manifest["expanded_sha256"]:
                raise IntakeError("expanded_hash")
        except zlib.error as exc:
            raise IntakeError("invalid_gzip") from exc
        finally:
            report.close()
        summary = {
            "rows": rows,
            "accepted": accepted,
            "rejected": rows - accepted,
            "compressed_bytes": size,
            "expanded_bytes": expanded,
            "limits": asdict(limits),
        }
        (stage / "manifest.json").write_text(serialize(manifest), encoding="utf-8")
        (stage / "summary.json").write_text(serialize(summary), encoding="utf-8")
        # All files are closed before the single atomic namespace transition.
        publish(stage, output)
        stage = None
        return summary
    finally:
        os.close(fd)
        if stage is not None:
            try:
                shutil.rmtree(stage)
            except OSError as exc:
                raise IntakeError(
                    f"private_staging_cleanup_failed: {stage}; "
                    "stop writers, inspect and remove this staging directory manually"
                ) from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    if manifest_path.stat().st_size > 65536:
        parser.error("manifest_limit")
    try:
        result = import_file(args.source, args.output, json.loads(manifest_path.read_text()))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Intake failed: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

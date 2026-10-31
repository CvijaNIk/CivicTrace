"""Deterministic Evidence Passports for a bounded synthetic single-bid demonstration."""

import json
from datetime import datetime
from hashlib import sha256

from .synthetic import assess_record, validate_release_identity


def validate_record(record):
    """Reject ambiguous identifiers/counts; preserve unknown counts as unknown."""
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    for key in ("record_id", "buyer_id", "supplier_id", "source_reference"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"{key} must be a nonempty string")
    count = record.get("bid_count")
    if count is not None and (type(count) is not int or count < 0):
        raise ValueError("bid_count must be a nonnegative integer or null")
    assess_record(record)
    return record


def validate_timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("collection timestamp must include a timezone")
    return value


def single_bid_findings(records, *, snapshot_hash, collected_at):
    """Demo count equals one; an indicator does not establish wrongdoing."""
    validate_timestamp(collected_at)
    if len(snapshot_hash) != 64 or any(c not in "0123456789abcdef" for c in snapshot_hash):
        raise ValueError("snapshot_hash must be a lowercase SHA-256 digest")
    findings = []
    seen = set()
    seen_processes, seen_releases = set(), set()
    for record in records:
        validate_record(record)
        if record["record_id"] in seen:
            raise ValueError("duplicate record_id; deduplicate before analysis")
        seen.add(record["record_id"])
        validate_release_identity(record, seen_processes, seen_releases)
        if not assess_record(record)["single_bid"]:
            continue
        identity = f"{snapshot_hash}:{record['record_id']}:single-bid:0.0.1"
        findings.append(
            {
                "schema_version": "0.1.0",
                "finding_id": sha256(identity.encode()).hexdigest(),
                "source": {
                    "name": "CivicTrace synthetic procurement fixture",
                    "reference": record["source_reference"],
                    "collected_at": collected_at,
                    "original_record_id": record["record_id"],
                    "original_file_sha256": snapshot_hash,
                    "snapshot_version": "synthetic-v1",
                    "license": "Apache-2.0",
                },
                "rule": {"id": "single-bid", "version": "0.0.1"},
                "facts": {"buyer_id": record["buyer_id"], "supplier_id": record["supplier_id"]},
                "computation": {
                    "expression": "bid_count == 1",
                    "parameters": {"threshold": 1},
                    "observed_result": record["bid_count"],
                },
                "benchmark": {
                    "description": "Exactly one reported bid; no peer baseline",
                    "value": 1,
                },
                "limitations": [
                    "Synthetic data",
                    "Count does not describe bidder eligibility or quality",
                ],
                "uncertainty": "Reported count only; no probability of fraud is estimated",
                "interpretation": (
                    "Single reported bid; review procurement context before any inference"
                ),
                "allegations": [],
                "verification_steps": [
                    "Verify original notice",
                    "Check competition and exemptions",
                ],
            }
        )
    return findings


def serialize_findings(findings):
    """Stable JSON makes reruns byte-identical for the same inputs and timestamp."""
    return json.dumps(findings, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def explorer_record(record):
    """Shared original-demo projection; keep unknown counts distinct from zero."""
    validate_record(record)
    return {
        **{
            key: record[key]
            for key in ("record_id", "buyer_id", "supplier_id", "source_reference", "bid_count")
        },
        "data_status": "missing" if record["bid_count"] is None else "reported",
    }

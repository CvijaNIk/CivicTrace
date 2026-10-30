"""Offline stratified quality assessment of a private dncp-local/1 import directory."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from civictrace.dncp import Limits, parse, validate_manifest
from review_dncp_sample import count_ok, date_ok, profile, state

STATUSES = ("complete", "cancelled", "unsuccessful", "unknown")
PERIODS = ("older", "recent", "unknown")
LOTS = ("single", "multiple", "unknown")


def objects(obj, key):
    value = obj.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise ValueError("invalid_collection")
    return value


def identity(value):
    return isinstance(value, str) and bool(value.strip())


def relation(record):
    """Keep entity counts separate; never interpret a discrepancy as misconduct."""
    tender = record.get("tender", {})
    lots = objects(tender, "lots")
    details = objects(record.get("bids") or {}, "details")
    tenderers = objects(tender, "tenderers")
    declared = tender.get("numberOfTenderers")
    lot_ids = [x.get("id") for x in lots or []]
    valid_lots = bool(lot_ids) and all(identity(x) for x in lot_ids)
    valid_lots = valid_lots and len(set(lot_ids)) == len(lot_ids)
    tenderer_ids = [x.get("id") for x in tenderers or []]
    valid_tenderers = tenderers is not None and all(identity(x) for x in tenderer_ids)
    bid_ids, bidder_ids, linked_lots = [], set(), set()
    per_lot = {x: set() for x in lot_ids} if valid_lots else {}
    linkage = "unknown" if details is None or not valid_lots else "valid"
    bidder_identity = "unknown" if details is None else "valid"
    for bid in details or []:
        bid_ids.append(bid.get("id"))
        parties = objects(bid, "tenderers")
        if not parties or any(not identity(x.get("id")) for x in parties):
            bidder_identity = "unknown"
        else:
            bidder_ids.update(x["id"] for x in parties)
        refs = bid.get("relatedLots")
        if not isinstance(refs, list) or not refs:
            linkage = "unknown" if linkage != "invalid" else linkage
        elif any(not identity(x) or x not in lot_ids for x in refs):
            linkage = "invalid"
        else:
            linked_lots.update(refs)
            if parties and all(identity(x.get("id")) for x in parties):
                for lot in refs:
                    if lot in per_lot:
                        per_lot[lot].update(x["id"] for x in parties)
    bid_id_state = "unknown" if details is None else "valid"
    if any(not identity(x) for x in bid_ids):
        bid_id_state = "invalid"
    elif len(set(bid_ids)) != len(bid_ids):
        bid_id_state = "duplicate"
    reported = declared if count_ok(declared) else None
    unique = len(set(tenderer_ids)) if valid_tenderers else None
    return {
        "reported_tenderers_state": state(tender, "numberOfTenderers", count_ok),
        "reported_tenderers": reported,
        "tenderer_entries": len(tenderers) if tenderers is not None else None,
        "unique_tenderers": unique,
        "bid_details": len(details) if details is not None else None,
        "bid_ids": bid_id_state,
        "unique_bid_participants": len(bidder_ids) if bidder_identity == "valid" else None,
        "bid_participant_identity": bidder_identity,
        "lots": len(lots) if lots is not None else None,
        "lot_ids": "valid" if valid_lots else "unknown",
        "bid_lot_linkage": linkage,
        "per_lot_unique_participants": (
            sorted(len(x) for x in per_lot.values())
            if linkage == "valid" and bidder_identity == "valid"
            else None
        ),
        "lots_with_bid_links": len(linked_lots) if linkage == "valid" else None,
        "reported_vs_unique_tenderers": (
            "unknown"
            if reported is None or unique is None
            else "equal"
            if reported == unique
            else "different"
        ),
        "reported_vs_bid_participants": (
            "unknown"
            if reported is None or bidder_identity != "valid"
            else "equal"
            if reported == len(bidder_ids)
            else "different"
        ),
    }


def observe(raw, cutoff):
    record = parse(raw, Limits().depth)
    # Run the existing profiler before importer child sanitization; preserve missing children.
    research = profile([raw])["records"][0]
    tender = record.get("tender", {})
    status = tender.get("status")
    status = status if status in STATUSES[:-1] else "unknown"
    release_date = (tender.get("tenderPeriod") or {}).get("startDate")
    year = (
        (datetime.fromisoformat(release_date.replace("Z", "+00:00")).astimezone(timezone.utc).year)
        if date_ok(release_date)
        else None
    )
    period = "unknown" if year is None else "older" if year < cutoff else "recent"
    rel = relation(record)
    lot_group = (
        ("multiple" if rel["lots"] > 1 else "single") if (rel["lot_ids"] == "valid") else "unknown"
    )
    # Only fixed enums, counts and field states leave the private directory.
    research.pop("ocid")
    research.pop("tender_status")
    research.pop("line")
    for group, statuses in [
        ("contracts", ("pending", "active", "cancelled", "terminated")),
        ("awards", ("pending", "active", "cancelled", "unsuccessful")),
    ]:
        for source, fields in zip(record.get(group, []), research[group]):
            fields["status"] = state(source, "status", lambda x: x in statuses)

    def minimize(obj):
        if isinstance(obj, dict):
            return {k: minimize(v) for k, v in obj.items() if k != "currency_code"}
        if isinstance(obj, list):
            return [minimize(x) for x in obj]
        return obj

    return (
        (status, period, lot_group),
        {
            "fields": minimize(research),
            "relationships": rel,
        },
        hashlib.sha256(record["ocid"].encode()).hexdigest(),
    )


def bounded_json(path, limit):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("metadata_limit")
    return parse(raw, 32)


def assess(directory, *, cutoff=2024, per_stratum=5, seed="dncp-quality-v1"):
    if type(cutoff) is not int or not 2000 <= cutoff <= 2100:
        raise ValueError("invalid_cutoff")
    if type(per_stratum) is not int or not 1 <= per_stratum <= 25:
        raise ValueError("invalid_quota")
    if not isinstance(seed, str) or not 1 <= len(seed) <= 128:
        raise ValueError("invalid_seed")
    directory = Path(directory)
    manifest = bounded_json(directory / "manifest.json", 65536)
    validate_manifest(manifest)
    summary = bounded_json(directory / "summary.json", 65536)
    counts, samples, failures = Counter(), {}, Counter()
    seen, ordinals, rows = set(), set(), 0
    # No raw source or canonical records are written. Directory is an immutable private intake.
    expanded_hash = hashlib.sha256()
    expanded_bytes = 0
    for path in sorted(directory.glob("*.raw")):
        rows += 1
        if rows > Limits().rows:
            raise ValueError("row_limit")
        if path.is_symlink() or not path.is_file():
            raise ValueError("regular_raw_required")
        ordinal = int(path.name[:6])
        if ordinal in ordinals:
            raise ValueError("duplicate_ordinal")
        ordinals.add(ordinal)
        with path.open("rb") as stream:
            raw = stream.read(Limits().line + 1)
        if len(raw) > Limits().line:
            raise ValueError("line_limit")
        expanded_bytes += len(raw)
        if expanded_bytes > Limits().expanded:
            raise ValueError("expanded_limit")
        expanded_hash.update(raw)
        digest = hashlib.sha256(raw).hexdigest()
        if path.name != f"{int(path.name[:6]):06d}-{digest}.raw":
            raise ValueError("raw_hash_mismatch")
        try:
            stratum, observation, unit = observe(raw, cutoff)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            failures["unsupported_or_invalid_raw_row"] += 1
            continue
        if unit in seen:
            # Repeated process versions would bias procedure-level inclusion probabilities.
            raise ValueError("duplicate_process_requires_predeclared_version_policy")
        seen.add(unit)
        counts[stratum] += 1
        rank = hashlib.sha256(f"{seed}:{unit}".encode()).hexdigest()
        bucket = samples.setdefault(stratum, [])
        bucket.append((rank, observation))
        bucket.sort(key=lambda x: (x[0], x[1]["fields"]["line_sha256"]))
        del bucket[per_stratum:]
    if rows != summary.get("rows") or ordinals != set(range(1, rows + 1)):
        raise ValueError("incomplete_intake_frame")
    if expanded_hash.hexdigest() != manifest["expanded_sha256"]:
        raise ValueError("expanded_frame_hash_mismatch")
    strata = []
    for status in STATUSES:
        for period in PERIODS:
            for lots in LOTS:
                key = (status, period, lots)
                selected = [x[1] for x in samples.get(key, [])]
                n, total = len(selected), counts[key]
                strata.append(
                    {
                        "status": status,
                        "period": period,
                        "lots": lots,
                        "frame_rows": total,
                        "selected_rows": n,
                        "inclusion_probability": {"numerator": n, "denominator": total},
                        "coverage": "empty"
                        if not total
                        else "shortfall"
                        if n < per_stratum
                        else "met",
                        "observations": selected,
                    }
                )
    observations = [x for s in strata for x in s["observations"]]
    checks = {}

    def check(name, outcomes):
        outcomes = list(outcomes)
        valid = sum(outcomes)
        checks[name] = {
            "valid": valid,
            "denominator": len(outcomes),
            "criterion": ">=95% valid in selected applicable objects",
            "result": (
                "insufficient_data"
                if not outcomes
                else "pass"
                if valid * 100 >= len(outcomes) * 95
                else "fail"
            ),
        }

    check(
        "reported_tenderers",
        (o["relationships"]["reported_tenderers_state"] == "valid" for o in observations),
    )
    check(
        "bid_lot_linkage",
        (
            o["relationships"]["bid_lot_linkage"] == "valid"
            for o in observations
            if o["relationships"]["lots"] is not None and o["relationships"]["lots"] > 1
        ),
    )
    check(
        "bid_identity",
        (
            o["relationships"]["bid_ids"] == "valid"
            for o in observations
            if o["relationships"]["bid_details"] is not None
        ),
    )
    check(
        "bid_participants",
        (
            o["relationships"]["bid_participant_identity"] == "valid"
            for o in observations
            if o["relationships"]["bid_details"] is not None
        ),
    )
    check("procedure_status", (s["status"] != "unknown" for s in strata for _ in s["observations"]))
    check(
        "tender_period",
        (
            o["fields"]["tender_start"] == "valid"
            and o["fields"]["tender_end"] == "valid"
            and o["fields"]["reversed_tender_period"] is False
            for o in observations
        ),
    )
    for group, field in [
        ("contracts", "id"),
        ("contracts", "date_signed"),
        ("awards", "date"),
        ("contracts", "status"),
        ("awards", "status"),
    ]:
        check(
            f"{group}_{field}",
            (x[field] == "valid" for o in observations for x in o["fields"][group]),
        )
    for group in ("contracts", "awards"):
        check(
            f"{group}_money",
            (
                x["value"].get("amount") == "valid" and x["value"].get("currency") == "valid"
                for o in observations
                for x in o["fields"][group]
            ),
        )
    for name, field in [("bid_dates", "bid_dates"), ("bid_values", "bid_values")]:
        check(
            name,
            (
                x == "valid"
                if name == "bid_dates"
                else x.get("amount") == "valid" and x.get("currency") == "valid"
                for o in observations
                for x in o["fields"][field]
            ),
        )
    return {
        "schema": "dncp-stratified-quality/1",
        "design": {
            "seed": seed,
            "cutoff_year_utc": cutoff,
            "date_basis": "tender.tenderPeriod.startDate (UTC year); no fallback",
            "quota": per_stratum,
            "method": "SHA256 bottom-k per process stratum",
            "frame": "supplied immutable importer cohort only",
            "snapshot_sha256": manifest["compressed_sha256"],
            "expanded_sha256": manifest["expanded_sha256"],
        },
        "frame_rows": rows,
        "profiled_rows": sum(counts.values()),
        "unprofiled": dict(failures),
        "strata": strata,
        "checks": checks,
        "analytics": {
            "status": "blocked",
            "reasons": [
                "publisher_bid_lot_status_semantics_unconfirmed",
                "population_frame_and_selection_not_verified",
                "field_coverage_is_descriptive_not_irregularity_evidence",
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=Path)
    parser.add_argument("--cutoff", type=int, default=2024)
    parser.add_argument("--per-stratum", type=int, default=5)
    parser.add_argument("--seed", default="dncp-quality-v1")
    args = parser.parse_args()
    try:
        result = assess(
            args.intake, cutoff=args.cutoff, per_stratum=args.per_stratum, seed=args.seed
        )
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Quality assessment failed: {type(exc).__name__}\n")
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

"""Pinned invented population only; no DNCP adapter or production analytics activation."""

import json
from collections import Counter
from decimal import Context, Decimal, InvalidOperation, localcontext
from hashlib import sha256
from pathlib import Path

from .synthetic import tender_period

FIXTURE_SHA256 = "920be0ed54d1994151a74d6a9a7f80b72b7811327df10a8f909a334b84235dec"
GROUP_FIELDS = ("procedure", "category", "value_band", "jurisdiction")
VERSION = "civictrace-synthetic-submission-period/1"


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()


def digest(raw):
    return sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("nonfinite JSON constant")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def group_key(group):
    if not isinstance(group, dict) or set(group) != set(GROUP_FIELDS):
        raise ValueError("group must supply exactly the four comparison dimensions")
    if any(not isinstance(group[k], str) or not group[k].strip() for k in GROUP_FIELDS):
        raise ValueError("comparison dimensions must be nonempty strings")
    return tuple(group[k] for k in GROUP_FIELDS)


def benchmarks(raw):
    if len(raw) > 65536:
        raise ValueError("benchmark configuration exceeds 64 KiB")
    config = strict_json(raw)
    if (
        not isinstance(config, dict)
        or config.get("contract") != "civictrace-submission-benchmarks/1"
    ):
        raise ValueError("unsupported benchmark contract")
    if set(config) != {"contract", "version", "benchmarks"}:
        raise ValueError("unexpected benchmark configuration fields")
    if not isinstance(config.get("version"), str) or not config["version"].strip():
        raise ValueError("benchmark version required")
    rows = config.get("benchmarks")
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError("at most 100 explicit benchmarks required")
    index, ids = {}, set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("benchmark must be an object")
        if set(row) != {"id", "basis", "reference", "elapsed_hours", "group"}:
            raise ValueError("unexpected or missing benchmark fields; elapsed hours only")
        for key in ("id", "basis", "reference", "elapsed_hours"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"benchmark {key} required as nonempty string")
        key = group_key(row.get("group"))
        if key in index or row["id"] in ids:
            raise ValueError("ambiguous benchmark group or ID")
        try:
            hours = Decimal(row["elapsed_hours"])
        except InvalidOperation as exc:
            raise ValueError("invalid benchmark hours") from exc
        if not hours.is_finite() or not 0 < hours <= 87600 or hours.as_tuple().exponent < -6:
            raise ValueError("benchmark hours must be positive, bounded, at most 6 decimals")
        index[key] = row
        ids.add(row["id"])
    return config, index


def number(value):
    return format(value.normalize(), "f")


def report(raw, config_raw):
    """Same exact fixture/config bytes and implementation yield the same output bytes.

    A caller-supplied synthetic flag cannot authorize a new population: only the reviewed
    fixture's exact SHA-256 is admitted. Configurations change comparison context only.
    """
    with localcontext(Context(prec=40)):
        return _report(raw, config_raw)


def _report(raw, config_raw):
    if digest(raw) != FIXTURE_SHA256:
        raise ValueError("only the pinned invented submission fixture is supported")
    source = strict_json(raw)
    config, index = benchmarks(config_raw)
    results = []
    for position, record in enumerate(source["records"]):
        state, seconds = tender_period(record)
        states = {
            k: "absent" if k not in record else "null" if record[k] is None else "supplied"
            for k in ("tender_start", "tender_end")
        }
        group = record["group"]
        unknown_group = any(group.get(k) is None for k in GROUP_FIELDS)
        benchmark = None if unknown_group else index.get(group_key(group))
        hours = None if seconds is None else Decimal(str(seconds)) / Decimal(3600)
        reason = (
            f"period_{state}"
            if state != "present"
            else "group_unknown"
            if unknown_group
            else "benchmark_unmatched"
            if benchmark is None
            else None
        )
        delta = None if reason else hours - Decimal(benchmark["elapsed_hours"])
        results.append(
            dict(
                record_id=record["record_id"],
                original_pointer=f"/records/{position}",
                source_reference=record["source_reference"],
                group=group,
                original_dates={k: record.get(k) for k in states},
                field_states=states,
                period_state=state,
                elapsed_seconds=seconds,
                elapsed_hours=None if hours is None else number(hours),
                calendar_days=None
                if seconds is None
                else number(Decimal(str(seconds)) / Decimal(86400)),
                working_days=None,
                working_days_state="not_computed_no_local_calendar",
                benchmark=benchmark,
                comparison_state="excluded" if reason else "compared",
                exclusion_reason=reason,
                deviation_hours=None if delta is None else number(delta),
                relation=None
                if delta is None
                else "below"
                if delta < 0
                else "above"
                if delta > 0
                else "equal",
                allegations=[],
            )
        )
    excluded = Counter(r["exclusion_reason"] for r in results if r["exclusion_reason"])
    compared = [r for r in results if r["comparison_state"] == "compared"]
    return dict(
        contract=VERSION,
        synthetic=True,
        analytics_enabled=False,
        time_basis="elapsed UTC seconds; calendar_days = seconds / 86400, not date boundaries",
        interpretation="Descriptive comparison only; no irregularity or legal violation inferred",
        limitations=[
            "Invented benchmarks, not representative peer statistics or legal minima",
            "No working-day/holiday calculation; no rounding before comparison",
            "No real DNCP inputs; hashes establish bytes, not factual truth",
        ],
        input_sha256=digest(raw),
        configuration_sha256=digest(config_raw),
        configuration=config,
        implementation_sha256={
            name: digest(Path(__file__).with_name(name + ".py").read_bytes())
            for name in ("submission_period", "synthetic")
        },
        rights=source["rights"],
        results=results,
        population_unit="one reviewed invented record; no release selection/amendment inference",
        denominators=dict(
            total_records=len(results),
            valid_duration_records=sum(r["period_state"] == "present" for r in results),
            comparison_records=len(compared),
            excluded_records=sum(excluded.values()),
        ),
        exclusions=dict(sorted(excluded.items())),
        comparison_counts={
            relation: sum(r["relation"] == relation for r in compared)
            for relation in ("below", "equal", "above")
        },
    )

"""Optional edge-case fields for the synthetic demo, not an OCDS adapter."""

import re
from datetime import datetime, timezone


def count_state(record, key):
    if key not in record:
        return "absent"
    value = record[key]
    if value is None:
        return "null"
    if type(value) is not int or value < 0:
        raise ValueError(f"{key} must be a nonnegative integer or null")
    return "present"


def instant(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value
    ):
        raise ValueError("timestamp must be RFC3339 with timezone")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def assess_record(record):
    """Return deterministic eligibility diagnostics without imputing source fields.

    Only the legacy explicit bid_count can trigger the demo. Reported tenderers,
    detail rows and supplier cardinality never supply a missing bid_count.
    """
    counts = {key: count_state(record, key) for key in ("bid_count", "reported_tenderer_count")}
    details = record.get("bid_details")
    if "bid_details" not in record:
        details_state = "absent"
    elif details is None:
        details_state = "null"
    elif not isinstance(details, list) or any(not isinstance(x, dict) for x in details):
        raise ValueError("bid_details must be an array of objects or null")
    else:
        details_state = "present"

    reasons = []
    for field, allowed in (
        ("procurement_status", {"active", "complete", "cancelled", "unsuccessful"}),
        ("award_status", {"pending", "active", "cancelled", "unsuccessful"}),
    ):
        if field in record:
            status = record[field]
            if not isinstance(status, str) or status not in allowed:
                reasons.append(f"{field}_unknown")
            elif status in {"cancelled", "unsuccessful", "pending"}:
                reasons.append(f"{field}_{status}")

    if "supplier_ids" in record:
        suppliers = record["supplier_ids"]
        if (
            not isinstance(suppliers, list)
            or not suppliers
            or any(not isinstance(x, str) or not x.strip() for x in suppliers)
            or len(set(suppliers)) != len(suppliers)
            or record["supplier_id"] not in suppliers
        ):
            raise ValueError("supplier_ids must be unique nonempty IDs including supplier_id")
        if len(suppliers) > 1:
            reasons.append("joint_suppliers_unallocated")

    duration = None
    period_state = "absent"
    if "tender_start" in record or "tender_end" in record:
        if record.get("tender_start") is None or record.get("tender_end") is None:
            period_state = "unknown"
        else:
            try:
                duration = (
                    instant(record["tender_end"]) - instant(record["tender_start"])
                ).total_seconds()
            except (ValueError, OverflowError):
                period_state = "invalid"
            else:
                period_state = "present"
                if duration < 0:
                    period_state = "reversed"
                    duration = None

    if counts["bid_count"] != "present":
        reasons.append("bid_count_unknown")
    return {
        "bid_count_state": counts["bid_count"],
        "reported_tenderer_count_state": counts["reported_tenderer_count"],
        "reported_tenderer_count": record.get("reported_tenderer_count"),
        "bid_details_state": details_state,
        "bid_details_count": len(details) if details_state == "present" else None,
        "tender_period_state": period_state,
        "tender_duration_seconds": duration,
        "exclusions": reasons,
        "single_bid": not reasons and record.get("bid_count") == 1,
    }


def validate_release_identity(record, seen_processes, seen_releases):
    """Fail closed on duplicate compiled processes/releases; never choose by order."""
    if "process_id" not in record and "release_id" not in record:
        return
    for field in ("process_id", "release_id"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError("process_id and release_id must both be nonempty strings")
    key = (record["process_id"], record["release_id"])
    if key in seen_releases:
        raise ValueError("duplicate release identity; explicit reconciliation required")
    if record["process_id"] in seen_processes:
        raise ValueError("duplicate process identity; explicit reconciliation required")
    seen_releases.add(key)
    seen_processes.add(record["process_id"])

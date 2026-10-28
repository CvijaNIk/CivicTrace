"""Versioned, offline canonical procurement tables. No source intake or implicit latest view."""

import json
import re
from copy import deepcopy
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256

from .synthetic import instant

SCHEMA_VERSION = "civictrace-canonical/1"
# Deliberately bounded supported ISO 4217 subset; other codes are unsupported, never inferred.
CURRENCIES = frozenset({"EUR", "USD", "GBP", "PYG", "RSD"})


def identity(*parts):
    """Length-safe, case-sensitive identity; independent of amounts and input ordering."""
    return sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()


def required(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("identity must be a nonempty string")
    return value


def field(obj, key, pointer, kind="text"):
    result = {"state": "absent", "value": None, "pointer": pointer}
    if key not in obj:
        return result
    value = obj[key]
    result["raw"] = deepcopy(value)
    if value is None:
        result["state"] = "null"
        return result
    try:
        if kind == "count":
            if type(value) is not int or value < 0:
                raise ValueError()
        elif kind == "date":
            value = instant(value).isoformat()
        elif kind == "amount":
            if isinstance(value, (float, bool)) or not isinstance(value, (str, int, Decimal)):
                raise ValueError()
            value = Decimal(value)
            if not value.is_finite() or value < 0 or len(value.as_tuple().digits) > 128:
                raise ValueError()
            if abs(value.as_tuple().exponent) > 128:
                raise ValueError()
            value = format(value, "f")
        elif kind == "currency":
            if value not in CURRENCIES:
                result.update(state="unsupported", reason="currency_not_in_v1_subset")
                return result
        elif not isinstance(value, str) or not value.strip():
            raise ValueError()
    except (ValueError, TypeError, InvalidOperation, OverflowError):
        result.update(state="invalid", reason=f"invalid_{kind}")
        return result
    result.update(state="present", value=value)
    return result


def money(obj, pointer):
    if obj is None:
        return {
            "amount": field({"amount": None}, "amount", pointer + "/amount", "amount"),
            "currency": field({"currency": None}, "currency", pointer + "/currency", "currency"),
        }
    if not isinstance(obj, dict):
        raise ValueError("value must be an object or null")
    return {k: field(obj, k, pointer + "/" + k, k) for k in ("amount", "currency")}


def normalize(releases, provenance):
    """Map an explicit OCDS-shaped subset atomically; retain immutable release versions.

    Callers supply exact-byte hashes, rights and source references. This is not a DNCP
    connector, OCDS validator, persistence engine or authority to redistribute source data.
    """
    for name in ("snapshot_sha256", "record_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", provenance.get(name, "")):
            raise ValueError("invalid provenance hash")
    for name in ("source_reference", "license", "attribution", "privacy_review", "adapter_version"):
        required(provenance.get(name))
    instant(provenance["collected_at"])
    tables = {
        k: []
        for k in ("processes", "releases", "parties", "awards", "contracts", "award_suppliers")
    }
    seen = set()
    processes = set()
    for release in releases:
        ocid, rid = required(release.get("ocid")), required(release.get("id"))
        pid = identity("process", ocid)
        version = identity("release", pid, rid, provenance["snapshot_sha256"])
        if version in seen:
            raise ValueError("duplicate release version; explicit reconciliation required")
        seen.add(version)
        if pid not in processes:
            tables["processes"].append({"id": pid, "ocid": ocid})
            processes.add(pid)
        base = {"process_id": pid, "release_id": version}
        tender = release.get("tender", {})
        if not isinstance(tender, dict):
            raise ValueError("tender must be an object")
        row = {
            **base,
            "id": version,
            "source_id": rid,
            "provenance": deepcopy(provenance),
            "date": field(release, "date", "/date", "date"),
            "status": field(tender, "status", "/tender/status"),
            "reported_tenderer_count": field(
                tender, "numberOfTenderers", "/tender/numberOfTenderers", "count"
            ),
            "bid_count": field({}, "bid_count", "/bids/statistics"),
            "source_record": deepcopy(release),
        }
        period = tender.get("tenderPeriod") or {}
        row["start"] = field(period, "startDate", "/tender/tenderPeriod/startDate", "date")
        row["end"] = field(period, "endDate", "/tender/tenderPeriod/endDate", "date")
        row["period_reversed"] = row["start"]["state"] == row["end"][
            "state"
        ] == "present" and instant(row["end"]["value"]) < instant(row["start"]["value"])
        tables["releases"].append(row)
        party_ids = set()
        for party in release.get("parties", []):
            source_id = required(party.get("id"))
            if source_id in party_ids:
                raise ValueError("duplicate party")
            party_ids.add(source_id)
            tables["parties"].append(
                {
                    **base,
                    "id": identity("party", pid, source_id),
                    "source_id": source_id,
                    "source": deepcopy(party),
                }
            )
        award_ids = {required(a.get("id")) for a in release.get("awards", [])}
        for table in ("awards", "contracts"):
            child_ids = set()
            for index, child in enumerate(release.get(table, [])):
                cid = required(child.get("id"))
                if cid in child_ids:
                    raise ValueError("duplicate child identity")
                child_ids.add(cid)
                pointer = f"/{table}/{index}"
                child_row = {
                    **base,
                    "id": identity(table, pid, cid),
                    "source_id": cid,
                    "status": field(child, "status", pointer + "/status"),
                    "money": money(child.get("value", {}), pointer + "/value"),
                    "date": field(
                        child,
                        "date" if table == "awards" else "dateSigned",
                        pointer + ("/date" if table == "awards" else "/dateSigned"),
                        "date",
                    ),
                    "pointer": pointer,
                }
                if table == "contracts":
                    aid = required(child.get("awardID"))
                    if aid not in award_ids:
                        raise ValueError("dangling contract awardID")
                    child_row["award_id"] = identity("awards", pid, aid)
                else:
                    suppliers = set()
                    for supplier in child.get("suppliers", []):
                        sid = required(supplier.get("id"))
                        if sid not in party_ids or sid in suppliers:
                            raise ValueError("dangling or duplicate award supplier")
                        suppliers.add(sid)
                        tables["award_suppliers"].append(
                            {
                                **base,
                                "award_id": child_row["id"],
                                "party_id": identity("party", pid, sid),
                            }
                        )
                tables[table].append(child_row)
    for rows in tables.values():
        rows.sort(key=lambda r: json.dumps(r, sort_keys=True, default=str))
    return {"schema_version": SCHEMA_VERSION, **tables}


def award_totals(model, selected_releases):
    """Exact active award totals, once per award, with explicit coverage exclusions.

    Selection is mandatory: no guessing latest amendments or adding contract values.
    Joint awards contribute once to process totals, never to supplier allocations.
    """
    releases = {r["id"]: r for r in model["releases"]}
    selected = set(selected_releases)
    if len(selected) != len(selected_releases) or not selected <= releases.keys():
        raise ValueError("invalid release selection")
    pids = [releases[r]["process_id"] for r in selected]
    if len(set(pids)) != len(pids):
        raise ValueError("select exactly one version per process")
    totals, excluded = {}, []
    with localcontext() as ctx:
        ctx.prec = 512
        for award in model["awards"]:
            if award["release_id"] not in selected:
                continue
            process_status = releases[award["release_id"]]["status"]["value"]
            value = award["money"]
            if (
                process_status not in {"active", "complete"}
                or award["status"]["value"] != "active"
                or any(f["state"] != "present" for f in value.values())
            ):
                excluded.append(award["id"])
                continue
            currency = value["currency"]["value"]
            totals[currency] = totals.get(currency, Decimal(0)) + Decimal(value["amount"]["value"])
    return {
        "totals": {k: format(v, "f") for k, v in sorted(totals.items())},
        "excluded_awards": sorted(excluded),
        "supplier_allocation": "unavailable",
    }


def serialize(model):
    return json.dumps(model, sort_keys=True, ensure_ascii=False, indent=2, default=str) + "\n"

"""Bounded research probe and offline field profiler; NOT an import connector."""

import argparse
import hashlib
import json
import re
import urllib.request
import zlib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

URL = "https://fastly.data.open-contracting.org/downloads/paraguay_dncp_records/4097/2025.jsonl.gz"
COMPRESSED_LIMIT = 262144
EXPANDED_LIMIT = 4 * 1024 * 1024
LINE_LIMIT = 1024 * 1024
ROW_LIMIT = 25


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def bad_constant(value):
    raise ValueError("nonfinite JSON number")


def load_line(raw):
    if len(raw) > LINE_LIMIT:
        raise ValueError("line byte limit exceeded")
    # Check depth before parsing, ignoring braces inside JSON strings.
    depth = 0
    quoted = escaped = False
    for char in raw.decode("utf-8"):
        if escaped:
            escaped = False
        elif quoted and char == "\\":
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            if char in "[{":
                depth += 1
                if depth > 32:
                    raise ValueError("JSON depth limit exceeded")
            elif char in "]}":
                depth -= 1
    value = json.loads(
        raw, object_pairs_hook=pairs, parse_float=Decimal, parse_constant=bad_constant
    )
    if not isinstance(value, dict) or "compiledRelease" in value or "records" in value:
        raise ValueError("expected one flat compiled release per JSONL line")
    return value


def decode_prefix(raw):
    if len(raw) > COMPRESSED_LIMIT:
        raise ValueError("compressed byte limit exceeded")
    decoder = zlib.decompressobj(31)
    expanded = decoder.decompress(raw, EXPANDED_LIMIT + 1)
    if len(expanded) > EXPANDED_LIMIT:
        raise ValueError("expanded byte limit exceeded")
    lines = expanded.split(b"\n")
    # Deliberately exclude an incomplete last line. A prefix has no full gzip CRC guarantee.
    complete = lines[:-1]
    if not complete or len(complete) > ROW_LIMIT:
        raise ValueError("complete row count outside research limit")
    return expanded, complete, len(lines[-1])


def state(obj, key, valid):
    if key not in obj:
        return "absent"
    if obj[key] is None:
        return "null"
    return "valid" if valid(obj[key]) else "invalid"


def date_ok(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)", value
    ):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def count_ok(value):
    return type(value) is int and value >= 0


def amount_ok(value):
    return type(value) in (int, Decimal) and Decimal(value).is_finite() and value >= 0


def value_profile(obj):
    value = obj.get("value")
    if not isinstance(value, dict):
        return {
            "value_state": (
                "absent" if "value" not in obj else "null" if value is None else "invalid"
            )
        }
    return {
        "amount": state(value, "amount", amount_ok),
        "currency": state(
            value,
            "currency",
            lambda x: isinstance(x, str) and re.fullmatch(r"[A-Z]{3}", x) is not None,
        ),
        "currency_code": value.get("currency"),
    }


def profile(lines):
    if not 1 <= len(lines) <= ROW_LIMIT:
        raise ValueError("row count outside research limit")
    rows = []
    seen = set()
    for number, raw in enumerate(lines, 1):
        obj = load_line(raw)
        ocid = obj.get("ocid")
        if not isinstance(ocid, str) or not re.fullmatch(r"ocds-03ad3f-[A-Za-z0-9-]+", ocid):
            raise ValueError("missing or unsupported DNCP OCID")
        if ocid in seen:
            raise ValueError("duplicate OCID in sample")
        seen.add(ocid)
        tender = obj.get("tender", {})
        if not isinstance(tender, dict):
            raise ValueError("tender must be an object")
        period = tender.get("tenderPeriod") or {}
        bids = obj.get("bids") or {}
        if not isinstance(period, dict) or not isinstance(bids, dict):
            raise ValueError("period and bids must be objects")
        collections = [obj.get("awards", []), obj.get("contracts", []), bids.get("details", [])]
        if any(
            not isinstance(xs, list) or any(not isinstance(x, dict) for x in xs)
            for xs in collections
        ):
            raise ValueError("invalid object collection")
        awards, contracts, details = collections
        start, end = period.get("startDate"), period.get("endDate")
        reversed_period = (
            (
                datetime.fromisoformat(start.replace("Z", "+00:00"))
                > datetime.fromisoformat(end.replace("Z", "+00:00"))
            )
            if (date_ok(start) and date_ok(end))
            else None
        )
        rows.append(
            {
                "line": number,
                "line_sha256": digest(raw),
                "ocid": ocid,
                "release_id": state(obj, "id", lambda x: isinstance(x, str) and bool(x)),
                "tender_id": state(tender, "id", lambda x: isinstance(x, str) and bool(x)),
                "release_date": state(obj, "date", date_ok),
                "tender_status": tender.get("status"),
                "number_of_tenderers": state(tender, "numberOfTenderers", count_ok),
                "reported_tenderer_count": (
                    tender.get("numberOfTenderers")
                    if count_ok(tender.get("numberOfTenderers"))
                    else None
                ),
                "bids_details_count": len(details),
                "bid_values": [value_profile(b) for b in details],
                "bid_dates": [state(b, "date", date_ok) for b in details],
                "bids_details_state": state(bids, "details", lambda x: isinstance(x, list)),
                "tender_start": state(period, "startDate", date_ok),
                "tender_end": state(period, "endDate", date_ok),
                "reversed_tender_period": reversed_period,
                "tender_value": value_profile(tender),
                "awards": [
                    {
                        "id": state(a, "id", lambda x: isinstance(x, str) and bool(x)),
                        "date": state(a, "date", date_ok),
                        "value": value_profile(a),
                    }
                    for a in awards
                ],
                "contracts": [
                    {
                        "id": state(c, "id", lambda x: isinstance(x, str) and bool(x)),
                        "date_signed": state(c, "dateSigned", date_ok),
                        "value": value_profile(c),
                    }
                    for c in contracts
                ],
            }
        )
    return {"schema": "dncp-research-profile/1", "rows": len(rows), "records": rows}


def fetch_prefix():
    request = urllib.request.Request(
        URL, headers={"Range": f"bytes=0-{COMPRESSED_LIMIT - 1}", "Accept-Encoding": "identity"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        expected = f"bytes 0-{COMPRESSED_LIMIT - 1}/"
        if (
            response.status != 206
            or response.url != URL
            or not (response.headers.get("Content-Range") or "").startswith(expected)
        ):
            raise ValueError("range or final URL mismatch; body not read")
        raw = response.read(COMPRESSED_LIMIT + 1)
        if len(raw) != COMPRESSED_LIMIT:
            raise ValueError("unexpected prefix length")
        manifest = {
            "url": URL,
            "final_url": response.url,
            "status": response.status,
            "content_range": response.headers.get("Content-Range"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "compressed_prefix_bytes": len(raw),
            "compressed_prefix_sha256": digest(raw),
            "full_snapshot_sha256": None,
        }
    return raw, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prefix", type=Path, help="local gzip prefix, at most 256 KiB")
    source.add_argument("--fetch-prefix", action="store_true", help="one fixed 256 KiB HTTP Range")
    parser.add_argument(
        "--save-prefix", type=Path, help="optional local research bytes; never commit"
    )
    args = parser.parse_args()
    if args.fetch_prefix:
        raw, manifest = fetch_prefix()
    else:
        with args.prefix.open("rb") as stream:
            raw = stream.read(COMPRESSED_LIMIT + 1)
        manifest = {"compressed_prefix_sha256": digest(raw), "full_snapshot_sha256": None}
    expanded, lines, tail = decode_prefix(raw)
    result = profile(lines)
    manifest.update(
        {
            "expanded_prefix_bytes": len(expanded),
            "discarded_tail_bytes": tail,
            "complete_lines": len(lines),
            "selection": "all complete prefix lines",
        }
    )
    result["acquisition"] = manifest
    if args.save_prefix:
        with args.save_prefix.open("xb") as stream:
            stream.write(raw)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

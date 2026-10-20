"""Bounded local JSON intake; no network access or parser side effects."""

import json
import math
import os
import stat
from pathlib import Path

MAX_INPUT_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_RECORDS = 10_000
MAX_NUMBER_CHARS = 128


def _reject_constant(_value):
    raise ValueError("nonfinite JSON constants are not allowed")


def _parse_number(value, conversion):
    if len(value) > MAX_NUMBER_CHARS:
        raise ValueError("JSON number token budget exceeded")
    result = conversion(value)
    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("nonfinite JSON numbers are not allowed")
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def parse_input(raw):
    """Reject excess bytes/depth before decoding; preserve original snapshot bytes."""
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds the 1 MiB size budget")
    # A byte-level depth scan is sufficient for JSON's ASCII delimiters and
    # avoids creating a recursive Python object before checking the budget.
    depth = 0
    quoted = False
    escaped = False
    for value in raw:
        if quoted:
            if escaped:
                escaped = False
            elif value == 92:
                escaped = True
            elif value == 34:
                quoted = False
        elif value == 34:
            quoted = True
        elif value in (91, 123):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ValueError("JSON depth budget exceeded")
        elif value in (93, 125):
            depth -= 1
    # UTF-8 is the input contract. json.loads(bytes) also auto-detects UTF-16/32,
    # which would make the byte-level depth guard ineffective.
    records = json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
        parse_int=lambda value: _parse_number(value, int),
        parse_float=lambda value: _parse_number(value, float),
    )
    if not isinstance(records, list):
        raise ValueError("input must be a JSON array")
    if len(records) > MAX_RECORDS:
        raise ValueError("input exceeds the 10000-record budget")
    return records


def load_input(path: Path):
    # Nonblocking open avoids waiting indefinitely when a selected path becomes
    # a FIFO. Validate the opened descriptor, not a racy path.stat() precheck.
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("input must be a regular file")
        if info.st_size > MAX_INPUT_BYTES:
            raise ValueError("input exceeds the 1 MiB size budget")
        raw = source.read(MAX_INPUT_BYTES + 1)
    return raw, parse_input(raw)

"""Synthetic-only checks for the research profiler; no network in CI."""

import importlib.util
import json
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "dncp_review", Path(__file__).resolve().parents[1] / "scripts/review_dncp_sample.py"
)
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


def line(ocid="ocds-03ad3f-SYN-1", **tender):
    return json.dumps({"ocid": ocid, "tender": tender}).encode()


def compress(raw):
    compressor = zlib.compressobj(wbits=31)
    return compressor.compress(raw) + compressor.flush()


class DncpReviewTests(unittest.TestCase):
    def test_explicit_expected_states_and_determinism(self):
        lines = [
            line(numberOfTenderers=1, value={"amount": 0, "currency": "PYG"}),
            line("ocds-03ad3f-SYN-2", numberOfTenderers=2),
            line("ocds-03ad3f-SYN-3", numberOfTenderers=None),
            line("ocds-03ad3f-SYN-4"),
        ]
        result = review.profile(lines)
        self.assertEqual(result, review.profile(lines))
        self.assertEqual(
            [r["number_of_tenderers"] for r in result["records"]],
            ["valid", "valid", "null", "absent"],
        )
        self.assertEqual(
            result["records"][0]["tender_value"],
            {"amount": "valid", "currency": "valid", "currency_code": "PYG"},
        )
        self.assertEqual(result["records"][0]["bids_details_state"], "absent")
        self.assertEqual(result["records"][0]["line_sha256"], review.digest(lines[0]))

    def test_invalid_counts_dates_and_values_are_not_validated(self):
        for value in [True, -1, "1", 1.5]:
            self.assertEqual(
                review.profile([line(numberOfTenderers=value)])["records"][0][
                    "number_of_tenderers"
                ],
                "invalid",
            )
        row = review.profile(
            [
                line(
                    value={"amount": -5, "currency": "pyg"},
                    tenderPeriod={"startDate": "2025-02-30T12:00:00Z", "endDate": None},
                )
            ]
        )["records"][0]
        self.assertEqual(row["tender_start"], "invalid")
        self.assertEqual(row["tender_end"], "null")
        self.assertEqual(row["tender_value"]["amount"], "invalid")
        self.assertEqual(row["tender_value"]["currency"], "invalid")
        row = review.profile(
            [
                line(
                    tenderPeriod={
                        "startDate": "2025-01-02T00:00:00Z",
                        "endDate": "2025-01-01T00:00:00Z",
                    }
                )
            ]
        )["records"][0]
        self.assertTrue(row["reversed_tender_period"])

    def test_duplicate_keys_identities_shapes_and_nonfinite_rejected(self):
        for raw in [
            b'{"ocid":"a","ocid":"b"}',
            b'{"x":NaN}',
            b"[]",
            b'{"records":[]}',
            b'{"ocid":null}',
            line(awards="not relevant", numberOfTenderers=0) + b"x",
            b'{"ocid":"ocds-03ad3f-SYN-1","awards":[null]}',
        ]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                review.profile([raw])
        with self.assertRaises(ValueError):
            review.profile([line(), line()])

    def test_prefix_excludes_partial_line_and_enforces_limits(self):
        expanded, lines, tail = review.decode_prefix(compress(line() + b'\n{"ocid":'))
        self.assertEqual(lines, [line()])
        self.assertEqual(tail, 8)
        self.assertTrue(expanded.endswith(b'{"ocid":'))
        with self.assertRaises(ValueError):
            review.decode_prefix(b"x" * (review.COMPRESSED_LIMIT + 1))
        with patch.object(review, "EXPANDED_LIMIT", 10), self.assertRaises(ValueError):
            review.decode_prefix(compress(line() + b"\n"))
        with patch.object(review, "LINE_LIMIT", len(line())):
            review.load_line(line())
            with self.assertRaises(ValueError):
                review.load_line(line() + b" ")
        for lines in [[], [line(f"ocds-03ad3f-SYN-{i}") for i in range(26)]]:
            with self.assertRaises(ValueError):
                review.profile(lines)
        with self.assertRaises(ValueError):
            review.load_line(b"[" * 33 + b"]" * 33)

    def test_range_failure_reads_no_body(self):
        class Response:
            status = 200
            url = review.URL
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, *args):
                self.fail_read = True
                raise AssertionError("must not read a non-range response")

        with patch.object(review.urllib.request, "urlopen", return_value=Response()):
            with self.assertRaisesRegex(ValueError, "body not read"):
                review.fetch_prefix()


if __name__ == "__main__":
    unittest.main()

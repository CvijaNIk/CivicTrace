import io
import json
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from civictrace.ingestion import MAX_INPUT_BYTES, MAX_JSON_DEPTH, load_input, parse_input


class InputSecurityTests(unittest.TestCase):
    def test_oversize_input_is_rejected_before_json_decode(self):
        with patch("civictrace.ingestion.json.loads") as decode:
            with self.assertRaisesRegex(ValueError, "size"):
                parse_input(b" " * (MAX_INPUT_BYTES + 1))
            decode.assert_not_called()

    def test_file_read_is_bounded_even_if_stat_size_is_wrong(self):
        class BoundedSpy(io.BytesIO):
            def fileno(self):
                return 123

            def read(self, size=-1):
                self_requested_sizes.append(size)
                return super().read(size)

        self_requested_sizes = []
        stream = BoundedSpy(b" " * (MAX_INPUT_BYTES + 100))
        with (
            patch("civictrace.ingestion.os.open", return_value=123),
            patch("civictrace.ingestion.os.fdopen", return_value=stream),
            patch(
                "civictrace.ingestion.os.fstat",
                return_value=SimpleNamespace(st_mode=stat.S_IFREG, st_size=0),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "size"):
                load_input(Path("synthetic.json"))
        self.assertEqual(self_requested_sizes, [MAX_INPUT_BYTES + 1])
        self.assertTrue(stream.closed)

    def test_depth_budget_rejects_before_json_decode(self):
        raw = ("[" * (MAX_JSON_DEPTH + 1) + "]" * (MAX_JSON_DEPTH + 1)).encode()
        with patch("civictrace.ingestion.json.loads") as decode:
            with self.assertRaisesRegex(ValueError, "depth"):
                parse_input(raw)
            decode.assert_not_called()

    def test_brackets_and_escaped_quotes_inside_strings_are_data(self):
        value = [{"note": '\\"' + "[{}]" * 100}]
        self.assertEqual(parse_input(json.dumps(value).encode()), value)

    def test_duplicate_keys_cannot_silently_replace_evidence(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_input(b'[{"bid_count": 2, "bid_count": 1}]')

    def test_nonfinite_constants_are_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity", "1e9999", "-1e9999"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "nonfinite"):
                    parse_input(f"[{value}]".encode())

    def test_numeric_token_budget_and_normal_numbers(self):
        with self.assertRaisesRegex(ValueError, "number token"):
            parse_input(("[" + "9" * 129 + "]").encode())
        self.assertEqual(parse_input(b"[1, -2, 1.25, 1e2]"), [1, -2, 1.25, 100.0])

    def test_other_encodings_cannot_bypass_byte_depth_scan(self):
        for encoding in ("utf-16", "utf-32"):
            with self.assertRaises(ValueError):
                parse_input(("[" * 100 + "]" * 100).encode(encoding))

    def test_invalid_encoding_json_and_top_level_are_rejected(self):
        for raw in (b"\xff", b"[", b"{}", b"null", b""):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    parse_input(raw)

    def test_exact_byte_budget_is_allowed(self):
        raw = b"[]" + b" " * (MAX_INPUT_BYTES - 2)
        self.assertEqual(parse_input(raw), [])

    def test_raw_snapshot_bytes_are_preserved_for_hashing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            original = b' [ {"bid_count": 1} ]\n'
            path.write_bytes(original)
            raw, records = load_input(path)
            self.assertEqual(raw, original)
            self.assertEqual(records, [{"bid_count": 1}])

    def test_nonregular_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((ValueError, OSError)):
                load_input(Path(directory))

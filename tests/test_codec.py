import unittest
import unicodedata

from bcm.codec import canonical_json_bytes, canonical_json_text, loads_json
from bcm.errors import CanonicalizationError, DecodeError


class CanonicalCodecTests(unittest.TestCase):
    def test_key_order_does_not_change_canonical_bytes(self) -> None:
        first = {"z": 1, "a": {"y": 2, "b": 3}}
        second = {"a": {"b": 3, "y": 2}, "z": 1}

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertEqual(canonical_json_text(first), '{"a":{"b":3,"y":2},"z":1}')

    def test_unicode_is_normalized_to_nfc(self) -> None:
        decomposed = "Filosofi\u0301a"
        composed = unicodedata.normalize("NFC", decomposed)

        self.assertEqual(
            canonical_json_bytes({"name": decomposed}),
            canonical_json_bytes({"name": composed}),
        )

    def test_duplicate_keys_are_rejected(self) -> None:
        with self.assertRaises(DecodeError):
            loads_json('{"block":1,"block":2}')

    def test_unicode_equivalent_keys_are_rejected(self) -> None:
        with self.assertRaises(DecodeError):
            loads_json('{"Filosofía":1,"Filosofi\\u0301a":2}')

    def test_floating_point_is_not_canonical(self) -> None:
        with self.assertRaises(CanonicalizationError):
            loads_json('{"value":1.5}')

    def test_nan_is_rejected(self) -> None:
        with self.assertRaises(DecodeError):
            loads_json('{"value":NaN}')


if __name__ == "__main__":
    unittest.main()


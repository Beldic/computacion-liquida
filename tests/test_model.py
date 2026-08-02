import unittest

from bcm.errors import DecodeError
from bcm.constants import MAX_INTEGER_BITS
from bcm.model import BCMBlock


def example_document() -> dict:
    return {
        "protocol": "BCM/0.1",
        "block": {
            "id": "modelo",
            "generation": 0,
            "owner": "local",
            "code": [{"op": "HALT", "args": []}],
            "state": {"pc": 0, "stack": [], "heap": {}, "registers": {}},
            "capabilities": [],
        },
    }


class ModelTests(unittest.TestCase):
    def test_document_round_trip(self) -> None:
        block = BCMBlock.from_document(example_document())
        rebuilt = BCMBlock.from_document(block.to_document())

        self.assertEqual(rebuilt.block_id, block.block_id)
        self.assertEqual(rebuilt.code, block.code)
        self.assertEqual(rebuilt.state.to_dict(), block.state.to_dict())

    def test_unknown_opcode_is_rejected(self) -> None:
        document = example_document()
        document["block"]["code"] = [{"op": "PYTHON_EVAL", "args": []}]

        with self.assertRaises(DecodeError):
            BCMBlock.from_document(document)

    def test_wrong_protocol_is_rejected(self) -> None:
        document = example_document()
        document["protocol"] = "BCM/9.9"

        with self.assertRaises(DecodeError):
            BCMBlock.from_document(document)

    def test_oversized_push_integer_is_rejected_while_decoding(self) -> None:
        document = example_document()
        document["block"]["code"] = [
            {"op": "PUSH", "args": [1 << MAX_INTEGER_BITS]},
            {"op": "HALT", "args": []},
        ]

        with self.assertRaises(DecodeError):
            BCMBlock.from_document(document)


if __name__ == "__main__":
    unittest.main()

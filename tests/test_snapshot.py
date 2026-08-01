import copy
import unittest
from dataclasses import replace

from bcm.errors import DecodeError, GenealogyError, IntegrityError
from bcm.isa import Opcode
from bcm.model import BCMBlock, Instruction, VMState
from bcm.snapshot import BlockSnapshot, create_snapshot, verify_parent
from bcm.vm import RunEvent, VirtualMachine


def migratable_block(block_id: str = "genealogia") -> BCMBlock:
    return BCMBlock(
        block_id=block_id,
        generation=0,
        owner="node-a",
        code=(
            Instruction(Opcode.PUSH, (2,)),
            Instruction(Opcode.PUSH, (2,)),
            Instruction(Opcode.YIELD),
            Instruction(Opcode.ADD),
            Instruction(Opcode.HALT),
        ),
    )


class SnapshotTests(unittest.TestCase):
    def test_genesis_snapshot_is_valid_and_has_no_parent(self) -> None:
        snapshot = create_snapshot(migratable_block())

        snapshot.verify()
        self.assertEqual(snapshot.generation, 0)
        self.assertIsNone(snapshot.parent_hash)
        self.assertEqual(len(snapshot.content_hash), 64)

    def test_snapshot_does_not_change_when_source_mutates(self) -> None:
        block = migratable_block()
        snapshot = create_snapshot(block)
        original_hash = snapshot.content_hash

        block.owner = "node-b"
        block.state.stack.append(99)
        block.state.heap[7] = 42

        snapshot.verify()
        self.assertEqual(snapshot.owner, "node-a")
        self.assertEqual(snapshot.state.stack, ())
        self.assertEqual(snapshot.content_hash, original_hash)

    def test_document_round_trip_preserves_identity(self) -> None:
        snapshot = create_snapshot(migratable_block())
        rebuilt = BlockSnapshot.from_document(snapshot.to_document())

        self.assertEqual(rebuilt, snapshot)
        self.assertEqual(rebuilt.content_hash, snapshot.content_hash)

    def test_payload_tampering_is_detected(self) -> None:
        snapshot = create_snapshot(migratable_block())
        tampered = copy.deepcopy(snapshot.to_document())
        tampered["payload"]["block"]["state"]["pc"] = 1

        with self.assertRaises(IntegrityError):
            BlockSnapshot.from_document(tampered)

    def test_unprotected_extra_fields_are_rejected(self) -> None:
        snapshot = create_snapshot(migratable_block())
        document = snapshot.to_document()
        document["payload"]["block"]["state"]["ghost"] = "value"

        with self.assertRaises(DecodeError):
            BlockSnapshot.from_document(document)

    def test_non_genesis_snapshot_requires_parent_hash(self) -> None:
        block = migratable_block()
        block.generation = 3

        with self.assertRaises(GenealogyError):
            create_snapshot(block)

    def test_successor_links_to_parent_and_can_be_restored(self) -> None:
        block = migratable_block()
        parent = create_snapshot(block)
        result = VirtualMachine().run(block)
        child = create_snapshot(block, parent=parent)

        verify_parent(child, parent)
        restored = child.thaw()

        self.assertEqual(result.event, RunEvent.YIELDED)
        self.assertEqual(child.generation, 1)
        self.assertEqual(child.parent_hash, parent.content_hash)
        self.assertEqual(restored.generation, 1)
        self.assertEqual(restored.state.stack, [2, 2])
        self.assertEqual(restored.state.pc, 3)

    def test_wrong_parent_is_rejected(self) -> None:
        block = migratable_block()
        parent = create_snapshot(block)
        VirtualMachine().run(block)
        child = create_snapshot(block, parent=parent)
        other_parent = create_snapshot(migratable_block("otra-genealogia"))

        with self.assertRaises(GenealogyError):
            verify_parent(child, other_parent)

    def test_code_change_cannot_become_a_successor(self) -> None:
        block = migratable_block()
        parent = create_snapshot(block)
        changed = BCMBlock(
            block_id=block.block_id,
            generation=0,
            owner=block.owner,
            code=(Instruction(Opcode.HALT),),
            state=VMState(),
        )

        with self.assertRaises(GenealogyError):
            create_snapshot(changed, parent=parent)

    def test_capabilities_cannot_change_silently(self) -> None:
        block = migratable_block()
        parent = create_snapshot(block)
        block.capabilities = frozenset({"NETWORK"})

        with self.assertRaises(GenealogyError):
            create_snapshot(block, parent=parent)

    def test_halted_snapshot_cannot_have_children(self) -> None:
        block = BCMBlock(
            block_id="final",
            generation=0,
            owner="node-a",
            code=(Instruction(Opcode.HALT),),
        )
        VirtualMachine().run(block)
        parent = create_snapshot(block)

        with self.assertRaises(GenealogyError):
            create_snapshot(parent.thaw(), parent=parent)

    def test_verification_rejects_descendant_of_halted_snapshot(self) -> None:
        block = migratable_block()
        genesis = create_snapshot(block)
        VirtualMachine().run(block)
        yielded = create_snapshot(block, parent=genesis)
        restored = yielded.thaw()
        VirtualMachine().run(restored)
        final = create_snapshot(restored, parent=yielded)

        forged = replace(
            final,
            generation=final.generation + 1,
            parent_hash=final.content_hash,
            content_hash="0" * 64,
        )
        forged = replace(forged, content_hash=forged.calculate_hash())

        with self.assertRaises(GenealogyError):
            verify_parent(forged, final)


if __name__ == "__main__":
    unittest.main()

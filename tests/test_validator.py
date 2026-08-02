import unittest

from bcm.errors import ValidationError
from bcm.isa import Opcode
from bcm.constants import MAX_INSTRUCTIONS_PER_QUANTUM, MAX_INTEGER_BITS
from bcm.model import BCMBlock, Instruction, Limits, VMState
from bcm.validator import validate_block


def block_with(*instructions: Instruction) -> BCMBlock:
    return BCMBlock(
        block_id="validation",
        generation=0,
        owner="local",
        code=instructions,
    )


class ValidatorTests(unittest.TestCase):
    def test_jump_must_target_program(self) -> None:
        block = block_with(
            Instruction(Opcode.JMP, (9,)),
            Instruction(Opcode.HALT),
        )

        with self.assertRaises(ValidationError):
            validate_block(block)

    def test_negative_heap_address_is_rejected(self) -> None:
        block = block_with(
            Instruction(Opcode.LOAD, (-1,)),
            Instruction(Opcode.HALT),
        )

        with self.assertRaises(ValidationError):
            validate_block(block)

    def test_state_limits_are_enforced(self) -> None:
        block = BCMBlock(
            block_id="limits",
            generation=0,
            owner="local",
            code=(Instruction(Opcode.HALT),),
            state=VMState(stack=[1, 2]),
            limits=Limits(max_stack_items=1),
        )

        with self.assertRaises(ValidationError):
            validate_block(block)

    def test_direct_construction_still_validates_identity(self) -> None:
        block = BCMBlock(
            block_id="",
            generation=-1,
            owner="",
            code=(Instruction(Opcode.HALT),),
        )

        with self.assertRaises(ValidationError):
            validate_block(block)

    def test_direct_construction_rejects_non_positive_limits(self) -> None:
        block = BCMBlock(
            block_id="limits",
            generation=0,
            owner="local",
            code=(Instruction(Opcode.HALT),),
            limits=Limits(max_instructions_per_quantum=0),
        )

        with self.assertRaises(ValidationError):
            validate_block(block)

    def test_direct_construction_rejects_oversized_integer(self) -> None:
        block = block_with(
            Instruction(Opcode.PUSH, (1 << MAX_INTEGER_BITS,)),
            Instruction(Opcode.HALT),
        )

        with self.assertRaises(ValidationError):
            validate_block(block)

    def test_initial_state_rejects_oversized_integer(self) -> None:
        block = BCMBlock(
            block_id="limits",
            generation=0,
            owner="local",
            code=(Instruction(Opcode.HALT),),
            state=VMState(stack=[-(1 << MAX_INTEGER_BITS)]),
        )

        with self.assertRaises(ValidationError):
            validate_block(block)

    def test_block_cannot_raise_protocol_resource_ceiling(self) -> None:
        block = BCMBlock(
            block_id="limits",
            generation=0,
            owner="local",
            code=(Instruction(Opcode.HALT),),
            limits=Limits(
                max_instructions_per_quantum=(
                    MAX_INSTRUCTIONS_PER_QUANTUM + 1
                )
            ),
        )

        with self.assertRaises(ValidationError):
            validate_block(block)


if __name__ == "__main__":
    unittest.main()

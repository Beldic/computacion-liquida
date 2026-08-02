import unittest

from bcm.constants import MAX_INTEGER_BITS
from bcm.errors import ExecutionError, ResourceLimitError, StackUnderflowError
from bcm.isa import Opcode
from bcm.model import BCMBlock, Instruction, Limits, VMState
from bcm.vm import RunEvent, VirtualMachine


def make_block(
    *instructions: Instruction,
    state: VMState | None = None,
    limits: Limits | None = None,
) -> BCMBlock:
    return BCMBlock(
        block_id="test",
        generation=0,
        owner="local",
        code=instructions,
        state=state or VMState(),
        limits=limits or Limits(),
    )


class VirtualMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vm = VirtualMachine()

    def test_sum_yields_and_resumes(self) -> None:
        block = make_block(
            Instruction(Opcode.PUSH, (2,)),
            Instruction(Opcode.PUSH, (2,)),
            Instruction(Opcode.YIELD),
            Instruction(Opcode.ADD),
            Instruction(Opcode.STORE, (0,)),
            Instruction(Opcode.HALT),
        )

        first = self.vm.run(block)
        second = self.vm.run(block)

        self.assertEqual(first.event, RunEvent.YIELDED)
        self.assertEqual(block.state.heap[0], 4)
        self.assertEqual(second.event, RunEvent.HALTED)
        self.assertTrue(block.state.halted)

    def test_quantum_stops_infinite_jump(self) -> None:
        block = make_block(
            Instruction(Opcode.JMP, (0,)),
            limits=Limits(max_instructions_per_quantum=5),
        )

        result = self.vm.run(block, quantum=5)

        self.assertEqual(result.event, RunEvent.QUANTUM_EXPIRED)
        self.assertEqual(result.executed, 5)
        self.assertEqual(block.state.pc, 0)

    def test_store_then_load(self) -> None:
        block = make_block(
            Instruction(Opcode.PUSH, (42,)),
            Instruction(Opcode.STORE, (7,)),
            Instruction(Opcode.LOAD, (7,)),
            Instruction(Opcode.HALT),
        )

        result = self.vm.run(block)

        self.assertEqual(result.event, RunEvent.HALTED)
        self.assertEqual(block.state.heap, {7: 42})
        self.assertEqual(block.state.stack, [42])

    def test_zero_condition_jumps(self) -> None:
        block = make_block(
            Instruction(Opcode.PUSH, (0,)),
            Instruction(Opcode.JZ, (4,)),
            Instruction(Opcode.PUSH, (99,)),
            Instruction(Opcode.HALT),
            Instruction(Opcode.PUSH, (7,)),
            Instruction(Opcode.HALT),
        )

        result = self.vm.run(block)

        self.assertEqual(result.event, RunEvent.HALTED)
        self.assertEqual(block.state.stack, [7])

    def test_stack_underflow_does_not_mutate_state(self) -> None:
        block = make_block(
            Instruction(Opcode.ADD),
            Instruction(Opcode.HALT),
            state=VMState(stack=[1]),
        )
        before = block.state.to_dict()

        with self.assertRaises(StackUnderflowError):
            self.vm.run(block)

        self.assertEqual(block.state.to_dict(), before)

    def test_division_by_zero_does_not_mutate_state(self) -> None:
        block = make_block(
            Instruction(Opcode.DIV),
            Instruction(Opcode.HALT),
            state=VMState(stack=[8, 0]),
        )
        before = block.state.to_dict()

        with self.assertRaises(ExecutionError):
            self.vm.run(block)

        self.assertEqual(block.state.to_dict(), before)

    def test_falling_off_program_raises_controlled_error(self) -> None:
        block = make_block(Instruction(Opcode.PUSH, (1,)))

        with self.assertRaises(ExecutionError):
            self.vm.run(block)

        self.assertEqual(block.state.stack, [1])
        self.assertEqual(block.state.pc, 1)
        self.assertEqual(block.state.executed_total, 1)

    def test_oversized_arithmetic_result_does_not_mutate_state(self) -> None:
        block = make_block(
            Instruction(Opcode.MUL),
            Instruction(Opcode.HALT),
            state=VMState(stack=[1 << (MAX_INTEGER_BITS - 1), 2]),
        )
        before = block.state.to_dict()

        with self.assertRaises(ResourceLimitError):
            self.vm.run(block)

        self.assertEqual(block.state.to_dict(), before)

    def test_repeated_squaring_is_stopped_by_integer_limit(self) -> None:
        instructions = [Instruction(Opcode.PUSH, (2,))]
        for _ in range(17):
            instructions.extend(
                (Instruction(Opcode.DUP), Instruction(Opcode.MUL))
            )
        instructions.append(Instruction(Opcode.HALT))
        block = make_block(*instructions)

        with self.assertRaises(ResourceLimitError):
            self.vm.run(block)

        self.assertLessEqual(
            max(abs(value).bit_length() for value in block.state.stack),
            MAX_INTEGER_BITS,
        )


if __name__ == "__main__":
    unittest.main()

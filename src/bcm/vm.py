"""Máquina virtual determinista del protocolo BCM/0.1."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import ExecutionError, ResourceLimitError, StackUnderflowError
from .isa import ARITHMETIC_OPCODES, Opcode
from .model import BCMBlock, VMState, VMValue
from .validator import validate_block


class RunEvent(str, Enum):
    HALTED = "halted"
    YIELDED = "yielded"
    QUANTUM_EXPIRED = "quantum_expired"


@dataclass(frozen=True, slots=True)
class RunResult:
    event: RunEvent
    executed: int
    pc: int


class VirtualMachine:
    """Ejecuta bloques BCM sin delegar código al intérprete de Python."""

    def run(self, block: BCMBlock, quantum: int | None = None) -> RunResult:
        validate_block(block)

        if block.state.halted:
            return RunResult(RunEvent.HALTED, executed=0, pc=block.state.pc)

        budget = (
            block.limits.max_instructions_per_quantum
            if quantum is None
            else quantum
        )
        if type(budget) is not int or budget <= 0:
            raise ResourceLimitError("el quantum debe ser un entero positivo")
        if budget > block.limits.max_instructions_per_quantum:
            raise ResourceLimitError(
                "el quantum solicitado excede max_instructions_per_quantum"
            )

        executed = 0
        while executed < budget:
            event = self._execute_one(block)
            executed += 1
            block.state.executed_total += 1
            if event is not None:
                return RunResult(event, executed=executed, pc=block.state.pc)

        return RunResult(
            RunEvent.QUANTUM_EXPIRED,
            executed=executed,
            pc=block.state.pc,
        )

    def _execute_one(self, block: BCMBlock) -> RunEvent | None:
        state = block.state
        instruction = block.code[state.pc]
        opcode = instruction.opcode

        if opcode is Opcode.PUSH:
            self._ensure_stack_capacity(block, 1)
            state.stack.append(instruction.args[0])
            state.pc += 1
            return None

        if opcode is Opcode.POP:
            self._require_stack(state, 1, opcode)
            state.stack.pop()
            state.pc += 1
            return None

        if opcode is Opcode.DUP:
            self._require_stack(state, 1, opcode)
            self._ensure_stack_capacity(block, 1)
            state.stack.append(state.stack[-1])
            state.pc += 1
            return None

        if opcode is Opcode.LOAD:
            address = self._address(instruction.args[0])
            if address not in state.heap:
                raise ExecutionError(f"LOAD accede a una celda inexistente: {address}")
            self._ensure_stack_capacity(block, 1)
            state.stack.append(state.heap[address])
            state.pc += 1
            return None

        if opcode is Opcode.STORE:
            self._require_stack(state, 1, opcode)
            address = self._address(instruction.args[0])
            if (
                address not in state.heap
                and len(state.heap) >= block.limits.max_heap_cells
            ):
                raise ResourceLimitError("STORE excedería max_heap_cells")
            value = state.stack[-1]
            state.heap[address] = value
            state.stack.pop()
            state.pc += 1
            return None

        if opcode in ARITHMETIC_OPCODES:
            self._execute_arithmetic(state, opcode)
            return None

        if opcode is Opcode.JMP:
            state.pc = self._address(instruction.args[0])
            return None

        if opcode is Opcode.JZ:
            self._require_stack(state, 1, opcode)
            condition = state.stack[-1]
            if type(condition) not in {int, bool}:
                raise ExecutionError("JZ requiere un entero o booleano en la pila")
            target = self._address(instruction.args[0])
            state.stack.pop()
            state.pc = target if condition == 0 else state.pc + 1
            return None

        if opcode is Opcode.YIELD:
            state.pc += 1
            return RunEvent.YIELDED

        if opcode is Opcode.HALT:
            state.pc += 1
            state.halted = True
            return RunEvent.HALTED

        raise ExecutionError(f"opcode sin implementación: {opcode.value}")

    def _execute_arithmetic(self, state: VMState, opcode: Opcode) -> None:
        self._require_stack(state, 2, opcode)
        left = state.stack[-2]
        right = state.stack[-1]
        if type(left) is not int or type(right) is not int:
            raise ExecutionError(f"{opcode.value} solo admite enteros")

        if opcode is Opcode.ADD:
            result: VMValue = left + right
        elif opcode is Opcode.SUB:
            result = left - right
        elif opcode is Opcode.MUL:
            result = left * right
        elif opcode is Opcode.DIV:
            if right == 0:
                raise ExecutionError("DIV no admite divisor cero")
            result = left // right
        else:  # pragma: no cover - protegido por ARITHMETIC_OPCODES
            raise ExecutionError(f"operación aritmética desconocida: {opcode.value}")

        state.stack[-2:] = [result]
        state.pc += 1

    @staticmethod
    def _require_stack(state: VMState, count: int, opcode: Opcode) -> None:
        if len(state.stack) < count:
            raise StackUnderflowError(
                f"{opcode.value} requiere {count} valores en la pila"
            )

    @staticmethod
    def _ensure_stack_capacity(block: BCMBlock, additional: int) -> None:
        if len(block.state.stack) + additional > block.limits.max_stack_items:
            raise ResourceLimitError("la operación excedería max_stack_items")

    @staticmethod
    def _address(value: VMValue) -> int:
        if type(value) is not int or value < 0:
            raise ExecutionError("la dirección debe ser un entero no negativo")
        return value

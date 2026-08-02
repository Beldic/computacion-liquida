"""Modelos transportables del protocolo BCM/0.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias

from .constants import (
    MAX_HEAP_CELLS,
    MAX_INSTRUCTIONS_PER_QUANTUM,
    MAX_INTEGER_BITS,
    MAX_REGISTERS,
    MAX_STACK_ITEMS,
)
from .errors import DecodeError
from .isa import Opcode

VMValue: TypeAlias = int | bool | str | None


def is_bounded_integer(value: object) -> bool:
    return type(value) is int and abs(value).bit_length() <= MAX_INTEGER_BITS


def is_vm_value(value: object) -> bool:
    return value is None or type(value) in {bool, str} or is_bounded_integer(value)


def _require_mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecodeError(f"{field_name} debe ser un objeto JSON")
    return value


def _require_non_negative_int(value: object, field_name: str) -> int:
    if not is_bounded_integer(value) or value < 0:
        raise DecodeError(f"{field_name} debe ser un entero no negativo")
    return value


def _require_positive_int(value: object, field_name: str) -> int:
    if not is_bounded_integer(value) or value <= 0:
        raise DecodeError(f"{field_name} debe ser un entero positivo")
    return value


@dataclass(frozen=True, slots=True)
class Instruction:
    opcode: Opcode
    args: tuple[VMValue, ...] = ()

    @classmethod
    def from_dict(cls, data: object) -> Instruction:
        raw = _require_mapping(data, "instruction")
        op = raw.get("op")
        if not isinstance(op, str):
            raise DecodeError("instruction.op debe ser una cadena")

        try:
            opcode = Opcode(op.upper())
        except ValueError as exc:
            raise DecodeError(f"opcode desconocido: {op!r}") from exc

        args = raw.get("args", [])
        if not isinstance(args, list):
            raise DecodeError("instruction.args debe ser una lista")
        if not all(is_vm_value(value) for value in args):
            raise DecodeError("instruction.args contiene un valor no admitido")

        return cls(opcode=opcode, args=tuple(args))

    def to_dict(self) -> dict[str, Any]:
        return {"op": self.opcode.value, "args": list(self.args)}


@dataclass(frozen=True, slots=True)
class Limits:
    max_instructions_per_quantum: int = MAX_INSTRUCTIONS_PER_QUANTUM
    max_stack_items: int = MAX_STACK_ITEMS
    max_heap_cells: int = MAX_HEAP_CELLS
    max_registers: int = MAX_REGISTERS

    @classmethod
    def from_dict(cls, data: object | None) -> Limits:
        if data is None:
            return cls()
        raw = _require_mapping(data, "block.limits")
        defaults = cls()
        return cls(
            max_instructions_per_quantum=_require_positive_int(
                raw.get(
                    "max_instructions_per_quantum",
                    defaults.max_instructions_per_quantum,
                ),
                "limits.max_instructions_per_quantum",
            ),
            max_stack_items=_require_positive_int(
                raw.get("max_stack_items", defaults.max_stack_items),
                "limits.max_stack_items",
            ),
            max_heap_cells=_require_positive_int(
                raw.get("max_heap_cells", defaults.max_heap_cells),
                "limits.max_heap_cells",
            ),
            max_registers=_require_positive_int(
                raw.get("max_registers", defaults.max_registers),
                "limits.max_registers",
            ),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "max_instructions_per_quantum": self.max_instructions_per_quantum,
            "max_stack_items": self.max_stack_items,
            "max_heap_cells": self.max_heap_cells,
            "max_registers": self.max_registers,
        }


@dataclass(slots=True)
class VMState:
    pc: int = 0
    registers: dict[str, VMValue] = field(default_factory=dict)
    stack: list[VMValue] = field(default_factory=list)
    heap: dict[int, VMValue] = field(default_factory=dict)
    halted: bool = False
    executed_total: int = 0

    @classmethod
    def from_dict(cls, data: object | None) -> VMState:
        if data is None:
            return cls()
        raw = _require_mapping(data, "block.state")

        registers_raw = raw.get("registers", {})
        registers = _require_mapping(registers_raw, "state.registers")
        if not all(
            isinstance(name, str) and is_vm_value(value)
            for name, value in registers.items()
        ):
            raise DecodeError("state.registers contiene una entrada no válida")

        stack = raw.get("stack", [])
        if not isinstance(stack, list) or not all(is_vm_value(value) for value in stack):
            raise DecodeError("state.stack debe ser una lista de valores BCM")

        heap_raw = _require_mapping(raw.get("heap", {}), "state.heap")
        heap: dict[int, VMValue] = {}
        for raw_address, value in heap_raw.items():
            try:
                address = int(raw_address)
            except (TypeError, ValueError) as exc:
                raise DecodeError("state.heap contiene una dirección no entera") from exc
            if address < 0 or not is_vm_value(value):
                raise DecodeError("state.heap contiene una celda no válida")
            heap[address] = value

        halted = raw.get("halted", False)
        if type(halted) is not bool:
            raise DecodeError("state.halted debe ser booleano")

        return cls(
            pc=_require_non_negative_int(raw.get("pc", 0), "state.pc"),
            registers=dict(registers),
            stack=list(stack),
            heap=heap,
            halted=halted,
            executed_total=_require_non_negative_int(
                raw.get("executed_total", 0), "state.executed_total"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pc": self.pc,
            "registers": dict(self.registers),
            "stack": list(self.stack),
            "heap": {str(address): value for address, value in sorted(self.heap.items())},
            "halted": self.halted,
            "executed_total": self.executed_total,
        }


@dataclass(slots=True)
class BCMBlock:
    block_id: str
    generation: int
    owner: str
    code: tuple[Instruction, ...]
    state: VMState = field(default_factory=VMState)
    capabilities: frozenset[str] = frozenset()
    limits: Limits = field(default_factory=Limits)

    @classmethod
    def from_document(cls, document: object) -> BCMBlock:
        root = _require_mapping(document, "document")
        protocol = root.get("protocol")
        if protocol != "BCM/0.1":
            raise DecodeError("protocol debe ser exactamente 'BCM/0.1'")

        raw = _require_mapping(root.get("block"), "block")
        block_id = raw.get("id")
        owner = raw.get("owner", "local")
        if not isinstance(block_id, str) or not block_id.strip():
            raise DecodeError("block.id debe ser una cadena no vacía")
        if not isinstance(owner, str) or not owner.strip():
            raise DecodeError("block.owner debe ser una cadena no vacía")

        code_raw = raw.get("code")
        if not isinstance(code_raw, list):
            raise DecodeError("block.code debe ser una lista")
        code = tuple(Instruction.from_dict(item) for item in code_raw)

        capabilities_raw = raw.get("capabilities", [])
        if not isinstance(capabilities_raw, list) or not all(
            isinstance(item, str) and item for item in capabilities_raw
        ):
            raise DecodeError("block.capabilities debe ser una lista de cadenas")

        return cls(
            block_id=block_id,
            generation=_require_non_negative_int(
                raw.get("generation", 0), "block.generation"
            ),
            owner=owner,
            code=code,
            state=VMState.from_dict(raw.get("state")),
            capabilities=frozenset(capabilities_raw),
            limits=Limits.from_dict(raw.get("limits")),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "protocol": "BCM/0.1",
            "block": {
                "id": self.block_id,
                "generation": self.generation,
                "owner": self.owner,
                "code": [instruction.to_dict() for instruction in self.code],
                "state": self.state.to_dict(),
                "capabilities": sorted(self.capabilities),
                "limits": self.limits.to_dict(),
            },
        }

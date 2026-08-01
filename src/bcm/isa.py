"""Conjunto mínimo de instrucciones de BCM/0.1-A."""

from enum import Enum


class Opcode(str, Enum):
    PUSH = "PUSH"
    POP = "POP"
    DUP = "DUP"
    LOAD = "LOAD"
    STORE = "STORE"
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    JMP = "JMP"
    JZ = "JZ"
    YIELD = "YIELD"
    HALT = "HALT"


ARITY: dict[Opcode, int] = {
    Opcode.PUSH: 1,
    Opcode.POP: 0,
    Opcode.DUP: 0,
    Opcode.LOAD: 1,
    Opcode.STORE: 1,
    Opcode.ADD: 0,
    Opcode.SUB: 0,
    Opcode.MUL: 0,
    Opcode.DIV: 0,
    Opcode.JMP: 1,
    Opcode.JZ: 1,
    Opcode.YIELD: 0,
    Opcode.HALT: 0,
}

ADDRESS_OPCODES = frozenset({Opcode.LOAD, Opcode.STORE})
JUMP_OPCODES = frozenset({Opcode.JMP, Opcode.JZ})
ARITHMETIC_OPCODES = frozenset(
    {Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV}
)


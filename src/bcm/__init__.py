"""Núcleo experimental de Computación Líquida y el Protocolo BCM."""

from .codec import canonical_json_bytes, canonical_json_text
from .errors import (
    BCMError,
    CanonicalizationError,
    ExecutionError,
    GenealogyError,
    IntegrityError,
    ResourceLimitError,
    ValidationError,
)
from .isa import Opcode
from .model import BCMBlock, Instruction, Limits, VMState
from .snapshot import BlockSnapshot, create_snapshot, verify_parent
from .vm import RunEvent, RunResult, VirtualMachine

__all__ = [
    "BCMBlock",
    "BCMError",
    "BlockSnapshot",
    "CanonicalizationError",
    "ExecutionError",
    "GenealogyError",
    "Instruction",
    "IntegrityError",
    "Limits",
    "Opcode",
    "ResourceLimitError",
    "RunEvent",
    "RunResult",
    "VMState",
    "ValidationError",
    "VirtualMachine",
    "canonical_json_bytes",
    "canonical_json_text",
    "create_snapshot",
    "verify_parent",
]

__version__ = "0.1.0b1"


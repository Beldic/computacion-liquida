"""Núcleo experimental de Computación Líquida y el Protocolo BCM."""

from .errors import BCMError, ExecutionError, ResourceLimitError, ValidationError
from .isa import Opcode
from .model import BCMBlock, Instruction, Limits, VMState
from .vm import RunEvent, RunResult, VirtualMachine

__all__ = [
    "BCMBlock",
    "BCMError",
    "ExecutionError",
    "Instruction",
    "Limits",
    "Opcode",
    "ResourceLimitError",
    "RunEvent",
    "RunResult",
    "VMState",
    "ValidationError",
    "VirtualMachine",
]

__version__ = "0.1.0a1"


"""Núcleo experimental de Computación Líquida y el Protocolo BCM."""

from .codec import canonical_json_bytes, canonical_json_text
from .constants import MAX_INTEGER_BITS
from .errors import (
    BCMError,
    CanonicalizationError,
    ExecutionError,
    GenealogyError,
    IntegrityError,
    RemoteRejectedError,
    ResourceLimitError,
    TransportError,
    ValidationError,
    WireProtocolError,
)
from .isa import Opcode
from .model import BCMBlock, Instruction, Limits, VMState
from .snapshot import BlockSnapshot, create_snapshot, verify_parent
from .transport import ReceivedTransfer, TransferReceipt, receive_one, send_snapshot
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
    "MAX_INTEGER_BITS",
    "Opcode",
    "ReceivedTransfer",
    "RemoteRejectedError",
    "ResourceLimitError",
    "RunEvent",
    "RunResult",
    "TransferReceipt",
    "TransportError",
    "VMState",
    "ValidationError",
    "VirtualMachine",
    "WireProtocolError",
    "canonical_json_bytes",
    "canonical_json_text",
    "create_snapshot",
    "receive_one",
    "send_snapshot",
    "verify_parent",
]

__version__ = "0.2.0a2"

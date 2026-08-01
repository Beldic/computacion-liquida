"""Snapshots inmutables y genealogía criptográfica de bloques BCM."""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass, replace
from typing import Any, ClassVar

from .codec import canonical_json_bytes, normalize_json_value
from .errors import DecodeError, GenealogyError, IntegrityError
from .model import BCMBlock, Instruction, Limits, VMState, VMValue
from .validator import validate_block

HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and HASH_PATTERN.fullmatch(value) is not None


def _require_exact_keys(
    value: object,
    expected: set[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecodeError(f"{label} debe ser un objeto JSON")
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise DecodeError(
            f"{label} no coincide con el esquema; faltan={missing}, sobran={extra}"
        )
    return value


@dataclass(frozen=True, slots=True)
class FrozenVMState:
    pc: int
    registers: tuple[tuple[str, VMValue], ...]
    stack: tuple[VMValue, ...]
    heap: tuple[tuple[int, VMValue], ...]
    halted: bool
    executed_total: int

    @classmethod
    def from_state(cls, state: VMState) -> FrozenVMState:
        return cls(
            pc=state.pc,
            registers=tuple(sorted(state.registers.items())),
            stack=tuple(state.stack),
            heap=tuple(sorted(state.heap.items())),
            halted=state.halted,
            executed_total=state.executed_total,
        )

    def thaw(self) -> VMState:
        return VMState(
            pc=self.pc,
            registers=dict(self.registers),
            stack=list(self.stack),
            heap=dict(self.heap),
            halted=self.halted,
            executed_total=self.executed_total,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pc": self.pc,
            "registers": dict(self.registers),
            "stack": list(self.stack),
            "heap": {str(address): value for address, value in self.heap},
            "halted": self.halted,
            "executed_total": self.executed_total,
        }


@dataclass(frozen=True, slots=True)
class BlockSnapshot:
    SNAPSHOT_FORMAT: ClassVar[str] = "BCM-SNAPSHOT/0.1"
    HASH_ALGORITHM: ClassVar[str] = "sha256"

    block_id: str
    generation: int
    parent_hash: str | None
    owner: str
    code: tuple[Instruction, ...]
    state: FrozenVMState
    capabilities: tuple[str, ...]
    limits: Limits
    content_hash: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "protocol": "BCM/0.1",
            "block": {
                "id": self.block_id,
                "generation": self.generation,
                "parent_hash": self.parent_hash,
                "owner": self.owner,
                "code": [instruction.to_dict() for instruction in self.code],
                "state": self.state.to_dict(),
                "capabilities": list(self.capabilities),
                "limits": self.limits.to_dict(),
            },
        }

    def to_document(self) -> dict[str, Any]:
        return {
            "snapshot_format": self.SNAPSHOT_FORMAT,
            "hash_algorithm": self.HASH_ALGORITHM,
            "content_hash": self.content_hash,
            "payload": self.to_payload(),
        }

    def thaw(self) -> BCMBlock:
        return BCMBlock(
            block_id=self.block_id,
            generation=self.generation,
            owner=self.owner,
            code=self.code,
            state=self.state.thaw(),
            capabilities=frozenset(self.capabilities),
            limits=self.limits,
        )

    def calculate_hash(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.to_payload())).hexdigest()

    def verify(self) -> None:
        if not _is_hash(self.content_hash):
            raise IntegrityError("content_hash no es un SHA-256 hexadecimal válido")
        if self.parent_hash is not None and not _is_hash(self.parent_hash):
            raise IntegrityError("parent_hash no es un SHA-256 hexadecimal válido")
        if self.generation == 0 and self.parent_hash is not None:
            raise IntegrityError("la generación cero no puede declarar progenitor")
        if self.generation > 0 and self.parent_hash is None:
            raise IntegrityError("una generación posterior a cero requiere parent_hash")

        validate_block(self.thaw())
        actual = self.calculate_hash()
        if not hmac.compare_digest(actual, self.content_hash):
            raise IntegrityError(
                f"hash incorrecto: se declaró {self.content_hash} y se calculó {actual}"
            )

    @classmethod
    def from_document(cls, document: object) -> BlockSnapshot:
        normalized = normalize_json_value(document)
        expected_keys = {
            "snapshot_format",
            "hash_algorithm",
            "content_hash",
            "payload",
        }
        root = _require_exact_keys(normalized, expected_keys, "snapshot")
        if root["snapshot_format"] != cls.SNAPSHOT_FORMAT:
            raise DecodeError("snapshot_format no es compatible")
        if root["hash_algorithm"] != cls.HASH_ALGORITHM:
            raise DecodeError("hash_algorithm no es compatible")

        claimed_hash = root["content_hash"]
        if not _is_hash(claimed_hash):
            raise DecodeError("content_hash no es un SHA-256 hexadecimal válido")

        payload = _require_exact_keys(
            root["payload"], {"protocol", "block"}, "payload"
        )
        block_raw = _require_exact_keys(
            payload["block"],
            {
                "id",
                "generation",
                "parent_hash",
                "owner",
                "code",
                "state",
                "capabilities",
                "limits",
            },
            "payload.block",
        )
        _require_exact_keys(
            block_raw["state"],
            {"pc", "registers", "stack", "heap", "halted", "executed_total"},
            "payload.block.state",
        )
        _require_exact_keys(
            block_raw["limits"],
            {
                "max_instructions_per_quantum",
                "max_stack_items",
                "max_heap_cells",
                "max_registers",
            },
            "payload.block.limits",
        )
        code_raw = block_raw["code"]
        if not isinstance(code_raw, list):
            raise DecodeError("payload.block.code debe ser una lista")
        for index, instruction in enumerate(code_raw):
            _require_exact_keys(
                instruction,
                {"op", "args"},
                f"payload.block.code[{index}]",
            )

        parent_hash = block_raw.get("parent_hash")
        if parent_hash is not None and not _is_hash(parent_hash):
            raise DecodeError("parent_hash no es un SHA-256 hexadecimal válido")

        block = BCMBlock.from_document(payload)
        validate_block(block)
        snapshot = cls(
            block_id=block.block_id,
            generation=block.generation,
            parent_hash=parent_hash,
            owner=block.owner,
            code=block.code,
            state=FrozenVMState.from_state(block.state),
            capabilities=tuple(sorted(block.capabilities)),
            limits=block.limits,
            content_hash=claimed_hash,
        )
        snapshot.verify()
        return snapshot


def _normalized_block(block: BCMBlock) -> BCMBlock:
    validate_block(block)
    document = normalize_json_value(block.to_document())
    normalized = BCMBlock.from_document(document)
    validate_block(normalized)
    return normalized


def create_snapshot(
    block: BCMBlock,
    parent: BlockSnapshot | None = None,
) -> BlockSnapshot:
    normalized = _normalized_block(block)

    if parent is None:
        if normalized.generation != 0:
            raise GenealogyError("un snapshot sin progenitor debe ser generación cero")
        generation = normalized.generation
        parent_hash = None
    else:
        parent.verify()
        if parent.state.halted:
            raise GenealogyError("un snapshot finalizado no puede tener descendencia")
        if normalized.block_id != parent.block_id:
            raise GenealogyError("el bloque y su progenitor tienen identidades distintas")
        if normalized.generation != parent.generation:
            raise GenealogyError(
                "el bloque mutable no procede de la generación del progenitor"
            )
        if normalized.code != parent.code:
            raise GenealogyError("el código cambió entre dos generaciones")
        if tuple(sorted(normalized.capabilities)) != parent.capabilities:
            raise GenealogyError("las capacidades cambiaron entre dos generaciones")
        if normalized.limits != parent.limits:
            raise GenealogyError("los límites cambiaron entre dos generaciones")
        generation = parent.generation + 1
        parent_hash = parent.content_hash

    snapshot = BlockSnapshot(
        block_id=normalized.block_id,
        generation=generation,
        parent_hash=parent_hash,
        owner=normalized.owner,
        code=normalized.code,
        state=FrozenVMState.from_state(normalized.state),
        capabilities=tuple(sorted(normalized.capabilities)),
        limits=normalized.limits,
        content_hash="0" * 64,
    )
    snapshot = replace(snapshot, content_hash=snapshot.calculate_hash())
    snapshot.verify()
    return snapshot


def verify_parent(child: BlockSnapshot, parent: BlockSnapshot) -> None:
    child.verify()
    parent.verify()

    if parent.state.halted:
        raise GenealogyError("un snapshot finalizado no puede tener descendencia")
    if child.parent_hash != parent.content_hash:
        raise GenealogyError("parent_hash no identifica al progenitor proporcionado")
    if child.block_id != parent.block_id:
        raise GenealogyError("la identidad del bloque cambió en la genealogía")
    if child.generation != parent.generation + 1:
        raise GenealogyError("las generaciones no son consecutivas")
    if child.code != parent.code:
        raise GenealogyError("el código cambió en la genealogía")
    if child.capabilities != parent.capabilities:
        raise GenealogyError("las capacidades cambiaron en la genealogía")
    if child.limits != parent.limits:
        raise GenealogyError("los límites cambiaron en la genealogía")
    if parent.state.halted:
        raise GenealogyError("un snapshot finalizado no puede tener descendencia")

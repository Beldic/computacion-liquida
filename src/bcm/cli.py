"""Interfaz de consola del intérprete BCM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .codec import load_json_file, write_canonical_json_file
from .errors import BCMError, ExecutionError
from .model import BCMBlock
from .snapshot import BlockSnapshot, create_snapshot, verify_parent
from .validator import validate_block
from .vm import RunEvent, VirtualMachine


def load_block(path: Path) -> BCMBlock:
    document = load_json_file(path)
    block = BCMBlock.from_document(document)
    validate_block(block)
    return block


def load_snapshot(path: Path) -> BlockSnapshot:
    return BlockSnapshot.from_document(load_json_file(path))


def _run_command(args: argparse.Namespace) -> int:
    block = load_block(args.path)
    vm = VirtualMachine()
    events: list[dict[str, object]] = []

    for cycle in range(1, args.max_cycles + 1):
        result = vm.run(block, quantum=args.quantum)
        events.append(
            {
                "cycle": cycle,
                "event": result.event.value,
                "executed": result.executed,
                "pc": result.pc,
            }
        )

        if result.event is RunEvent.HALTED or not args.until_halt:
            break
    else:
        raise ExecutionError(
            f"la ejecución superó el máximo de {args.max_cycles} ciclos"
        )

    output = {
        "events": events,
        "document": block.to_document(),
    }
    if args.output_block is not None:
        write_canonical_json_file(
            args.output_block,
            block.to_document(),
            overwrite=args.force,
        )
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _inspect_command(args: argparse.Namespace) -> int:
    block = load_block(args.path)
    summary = {
        "protocol": "BCM/0.1",
        "id": block.block_id,
        "generation": block.generation,
        "owner": block.owner,
        "instructions": len(block.code),
        "pc": block.state.pc,
        "stack_items": len(block.state.stack),
        "heap_cells": len(block.state.heap),
        "halted": block.state.halted,
        "capabilities": sorted(block.capabilities),
        "limits": block.limits.to_dict(),
        "valid": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _checkpoint_command(args: argparse.Namespace) -> int:
    block = load_block(args.path)
    parent = load_snapshot(args.parent) if args.parent is not None else None
    snapshot = create_snapshot(block, parent=parent)
    write_canonical_json_file(
        args.output,
        snapshot.to_document(),
        overwrite=args.force,
    )
    summary = {
        "snapshot_format": snapshot.SNAPSHOT_FORMAT,
        "id": snapshot.block_id,
        "generation": snapshot.generation,
        "parent_hash": snapshot.parent_hash,
        "content_hash": snapshot.content_hash,
        "output": str(args.output),
        "valid": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _verify_command(args: argparse.Namespace) -> int:
    snapshot = load_snapshot(args.path)
    if args.parent is not None:
        verify_parent(snapshot, load_snapshot(args.parent))
    summary = {
        "snapshot_format": snapshot.SNAPSHOT_FORMAT,
        "id": snapshot.block_id,
        "generation": snapshot.generation,
        "parent_hash": snapshot.parent_hash,
        "content_hash": snapshot.content_hash,
        "parent_verified": args.parent is not None,
        "valid": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _restore_command(args: argparse.Namespace) -> int:
    snapshot = load_snapshot(args.path)
    block = snapshot.thaw()
    write_canonical_json_file(
        args.output,
        block.to_document(),
        overwrite=args.force,
    )
    summary = {
        "id": block.block_id,
        "generation": block.generation,
        "content_hash": snapshot.content_hash,
        "output": str(args.output),
        "restored": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument(
        "--force",
        action="store_true",
        help="permite sustituir el archivo de salida",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bcm",
        description="Intérprete experimental de Computación Líquida",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect", help="valida y resume un documento BCM"
    )
    inspect_parser.add_argument("path", type=Path)
    inspect_parser.set_defaults(handler=_inspect_command)

    run_parser = subparsers.add_parser("run", help="ejecuta un documento BCM")
    run_parser.add_argument("path", type=Path)
    run_parser.add_argument(
        "--quantum",
        type=int,
        default=None,
        help="presupuesto por ciclo; no puede exceder el límite del bloque",
    )
    run_parser.add_argument(
        "--until-halt",
        action="store_true",
        help="reanuda localmente después de YIELD o de agotar el quantum",
    )
    run_parser.add_argument(
        "--max-cycles",
        type=int,
        default=1_000,
        help="protección frente a programas que no terminan",
    )
    run_parser.add_argument(
        "--output-block",
        type=Path,
        default=None,
        help="guarda el estado resultante como documento BCM canónico",
    )
    run_parser.add_argument(
        "--force",
        action="store_true",
        help="permite sustituir --output-block",
    )
    run_parser.set_defaults(handler=_run_command)

    checkpoint_parser = subparsers.add_parser(
        "checkpoint", help="congela un bloque como snapshot verificable"
    )
    checkpoint_parser.add_argument("path", type=Path)
    checkpoint_parser.add_argument(
        "--parent",
        type=Path,
        default=None,
        help="snapshot progenitor de la nueva generación",
    )
    _add_output_arguments(checkpoint_parser)
    checkpoint_parser.set_defaults(handler=_checkpoint_command)

    verify_parser = subparsers.add_parser(
        "verify", help="verifica la integridad y, opcionalmente, la filiación"
    )
    verify_parser.add_argument("path", type=Path)
    verify_parser.add_argument("--parent", type=Path, default=None)
    verify_parser.set_defaults(handler=_verify_command)

    restore_parser = subparsers.add_parser(
        "restore", help="reconstruye un bloque mutable desde un snapshot"
    )
    restore_parser.add_argument("path", type=Path)
    _add_output_arguments(restore_parser)
    restore_parser.set_defaults(handler=_restore_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (BCMError, OSError) as exc:
        print(f"BCM error: {exc}", file=sys.stderr)
        return 2

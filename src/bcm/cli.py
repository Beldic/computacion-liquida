"""Interfaz de consola del intérprete BCM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .errors import BCMError, DecodeError, ExecutionError
from .model import BCMBlock
from .validator import validate_block
from .vm import RunEvent, VirtualMachine


def load_block(path: Path) -> BCMBlock:
    try:
        with path.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except json.JSONDecodeError as exc:
        raise DecodeError(f"JSON inválido en {path}: {exc.msg}") from exc

    block = BCMBlock.from_document(document)
    validate_block(block)
    return block


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
    run_parser.set_defaults(handler=_run_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (BCMError, OSError) as exc:
        print(f"BCM error: {exc}", file=sys.stderr)
        return 2


"""Codificación JSON canónica y segura para documentos BCM."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

from .errors import CanonicalizationError, DecodeError


def normalize_json_value(value: object, path: str = "$") -> Any:
    """Devuelve una copia JSON inmutable por convención y normalizada a NFC.

    BCM/0.1-B excluye números de coma flotante, claves no textuales y cualquier
    objeto ejecutable de Python. Las tuplas se convierten en listas JSON.
    """

    if value is None or type(value) in {bool, int}:
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, (list, tuple)):
        return [
            normalize_json_value(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(f"{path} contiene una clave no textual")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise CanonicalizationError(
                    f"{path} contiene claves duplicadas tras normalizar Unicode"
                )
            normalized[normalized_key] = normalize_json_value(
                item, f"{path}.{normalized_key}"
            )
        return normalized

    raise CanonicalizationError(
        f"{path} contiene un tipo no canónico: {type(value).__name__}"
    )


def canonical_json_text(document: object) -> str:
    normalized = normalize_json_value(document)
    try:
        return json.dumps(
            normalized,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:  # defensa adicional de json.dumps
        raise CanonicalizationError("el documento no puede codificarse") from exc


def canonical_json_bytes(document: object) -> bytes:
    return canonical_json_text(document).encode("utf-8")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        normalized_key = unicodedata.normalize("NFC", key)
        if normalized_key in result:
            raise DecodeError(f"clave JSON duplicada: {normalized_key!r}")
        result[normalized_key] = value
    return result


def _reject_non_finite_number(value: str) -> None:
    raise DecodeError(f"constante numérica JSON no admitida: {value}")


def loads_json(text: str) -> Any:
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_non_finite_number,
        )
    except json.JSONDecodeError as exc:
        raise DecodeError(f"JSON inválido: {exc.msg}") from exc
    return normalize_json_value(document)


def load_json_file(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DecodeError(f"{path} no contiene UTF-8 válido") from exc
    return loads_json(text)


def write_canonical_json_file(
    path: Path,
    document: object,
    *,
    overwrite: bool = False,
) -> None:
    mode = "w" if overwrite else "x"
    with path.open(mode, encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json_text(document))
        stream.write("\n")


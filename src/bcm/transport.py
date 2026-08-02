"""Transporte TCP local y verificable para snapshots BCM."""

from __future__ import annotations

import ipaddress
import math
import re
import socket
import struct
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .codec import (
    canonical_json_bytes,
    load_json_file,
    loads_json,
    write_canonical_json_file,
)
from .errors import (
    BCMError,
    DecodeError,
    IntegrityError,
    RemoteRejectedError,
    TransportError,
    WireProtocolError,
)
from .snapshot import BlockSnapshot

WIRE_PROTOCOL = "BCM-WIRE/0.2"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7337
DEFAULT_TIMEOUT = 5.0
DEFAULT_MAX_FRAME_BYTES = 8 * 1024 * 1024

_FRAME_HEADER = struct.Struct("!I")
_REQUEST_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class TransferReceipt:
    request_id: str
    content_hash: str
    stored: bool


@dataclass(frozen=True, slots=True)
class ReceivedTransfer:
    request_id: str
    content_hash: str
    block_id: str
    generation: int
    stored: bool
    path: Path
    peer: str


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


def _validate_request_id(value: object, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or _REQUEST_ID_PATTERN.fullmatch(value) is None:
        raise WireProtocolError("request_id debe contener 32 caracteres hexadecimales")
    return value


def _validate_content_hash(value: object) -> str:
    if not isinstance(value, str) or _HASH_PATTERN.fullmatch(value) is None:
        raise WireProtocolError("content_hash no es un SHA-256 hexadecimal válido")
    return value


def _validate_timeout(timeout: float) -> None:
    if (
        type(timeout) not in {int, float}
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise WireProtocolError("timeout debe ser un número positivo")


def _validate_port(port: int, *, allow_zero: bool = False) -> None:
    minimum = 0 if allow_zero else 1
    if type(port) is not int or not minimum <= port <= 65_535:
        raise WireProtocolError(f"port debe estar entre {minimum} y 65535")


def _validate_frame_limit(max_frame_bytes: int) -> None:
    if (
        type(max_frame_bytes) is not int
        or max_frame_bytes <= 0
        or max_frame_bytes > 0xFFFF_FFFF
    ):
        raise WireProtocolError(
            "max_frame_bytes debe estar entre 1 y 4294967295"
        )


def validate_loopback_host(host: str) -> None:
    if host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise WireProtocolError("host debe ser una dirección IP de loopback") from exc
    if address.version != 4 or not address.is_loopback:
        raise WireProtocolError("BCM/0.2-A solo permite loopback IPv4")


def send_document(
    connection: socket.socket,
    document: object,
    *,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
) -> None:
    _validate_frame_limit(max_frame_bytes)
    payload = canonical_json_bytes(document)
    if not payload:
        raise WireProtocolError("un frame BCM no puede estar vacío")
    if len(payload) > max_frame_bytes:
        raise WireProtocolError(
            f"el frame ocupa {len(payload)} bytes y excede el límite "
            f"de {max_frame_bytes}"
        )
    try:
        connection.sendall(_FRAME_HEADER.pack(len(payload)) + payload)
    except socket.timeout as exc:
        raise TransportError("tiempo agotado durante el envío") from exc
    except OSError as exc:
        raise TransportError("falló el envío del frame BCM") from exc


def _receive_exact(connection: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        try:
            chunk = connection.recv(size - len(chunks))
        except socket.timeout as exc:
            raise TransportError("tiempo agotado durante la recepción") from exc
        except OSError as exc:
            raise TransportError("falló la recepción del frame BCM") from exc
        if not chunk:
            raise TransportError("la conexión se cerró antes de completar el frame")
        chunks.extend(chunk)
    return bytes(chunks)


def receive_document(
    connection: socket.socket,
    *,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
) -> Any:
    _validate_frame_limit(max_frame_bytes)
    header = _receive_exact(connection, _FRAME_HEADER.size)
    (payload_size,) = _FRAME_HEADER.unpack(header)
    if payload_size == 0:
        raise WireProtocolError("un frame BCM no puede estar vacío")
    if payload_size > max_frame_bytes:
        raise WireProtocolError(
            f"el frame declara {payload_size} bytes y excede el límite "
            f"de {max_frame_bytes}"
        )

    payload = _receive_exact(connection, payload_size)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DecodeError("el frame BCM no contiene UTF-8 válido") from exc
    document = loads_json(text)
    if canonical_json_bytes(document) != payload:
        raise WireProtocolError("el documento recibido no usa JSON canónico BCM")
    return document


def make_transfer_request(
    snapshot: BlockSnapshot,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    snapshot.verify()
    transfer_id = request_id or uuid.uuid4().hex
    _validate_request_id(transfer_id)
    return {
        "wire_protocol": WIRE_PROTOCOL,
        "message_type": "snapshot",
        "request_id": transfer_id,
        "snapshot": snapshot.to_document(),
    }


def parse_transfer_request(document: object) -> tuple[str, BlockSnapshot]:
    root = _require_exact_keys(
        document,
        {"wire_protocol", "message_type", "request_id", "snapshot"},
        "mensaje de transferencia",
    )
    if root["wire_protocol"] != WIRE_PROTOCOL:
        raise WireProtocolError("wire_protocol no es compatible")
    if root["message_type"] != "snapshot":
        raise WireProtocolError("message_type debe ser 'snapshot'")
    request_id = _validate_request_id(root["request_id"])
    if request_id is None:  # defensa para analizadores y cambios futuros
        raise WireProtocolError("request_id no puede ser nulo")
    return request_id, BlockSnapshot.from_document(root["snapshot"])


def make_acceptance(
    request_id: str,
    content_hash: str,
    *,
    stored: bool,
) -> dict[str, Any]:
    _validate_request_id(request_id)
    _validate_content_hash(content_hash)
    if type(stored) is not bool:
        raise WireProtocolError("stored debe ser booleano")
    return {
        "wire_protocol": WIRE_PROTOCOL,
        "message_type": "accepted",
        "request_id": request_id,
        "content_hash": content_hash,
        "stored": stored,
    }


def make_rejection(
    request_id: str | None,
    code: str,
    detail: str,
) -> dict[str, Any]:
    _validate_request_id(request_id, allow_none=True)
    if not isinstance(code, str) or not code:
        raise WireProtocolError("el rechazo necesita un código")
    if not isinstance(detail, str) or not detail:
        raise WireProtocolError("el rechazo necesita un detalle")
    return {
        "wire_protocol": WIRE_PROTOCOL,
        "message_type": "rejected",
        "request_id": request_id,
        "code": code,
        "detail": detail,
    }


def parse_transfer_response(
    document: object,
    *,
    expected_request_id: str,
    expected_content_hash: str,
) -> TransferReceipt:
    _validate_request_id(expected_request_id)
    _validate_content_hash(expected_content_hash)
    if not isinstance(document, dict):
        raise DecodeError("la respuesta debe ser un objeto JSON")
    message_type = document.get("message_type")

    if message_type == "rejected":
        root = _require_exact_keys(
            document,
            {"wire_protocol", "message_type", "request_id", "code", "detail"},
            "rechazo",
        )
        if root["wire_protocol"] != WIRE_PROTOCOL:
            raise WireProtocolError("wire_protocol no es compatible")
        response_id = _validate_request_id(root["request_id"], allow_none=True)
        if response_id is not None and response_id != expected_request_id:
            raise WireProtocolError("el rechazo corresponde a otra petición")
        code = root["code"]
        detail = root["detail"]
        if (
            not isinstance(code, str)
            or not code
            or not isinstance(detail, str)
            or not detail
        ):
            raise WireProtocolError("el rechazo contiene campos no textuales")
        raise RemoteRejectedError(code, detail)

    root = _require_exact_keys(
        document,
        {
            "wire_protocol",
            "message_type",
            "request_id",
            "content_hash",
            "stored",
        },
        "aceptación",
    )
    if root["wire_protocol"] != WIRE_PROTOCOL:
        raise WireProtocolError("wire_protocol no es compatible")
    if root["message_type"] != "accepted":
        raise WireProtocolError("message_type de respuesta desconocido")
    response_id = _validate_request_id(root["request_id"])
    response_hash = _validate_content_hash(root["content_hash"])
    if response_id != expected_request_id:
        raise WireProtocolError("la aceptación corresponde a otra petición")
    if response_hash != expected_content_hash:
        raise IntegrityError("el receptor confirmó una identidad distinta")
    if type(root["stored"]) is not bool:
        raise WireProtocolError("stored debe ser booleano")
    return TransferReceipt(response_id, response_hash, root["stored"])


def store_snapshot(snapshot: BlockSnapshot, inbox: Path) -> tuple[Path, bool]:
    snapshot.verify()
    inbox.mkdir(parents=True, exist_ok=True)
    target = inbox / f"{snapshot.content_hash}.snapshot.json"
    try:
        write_canonical_json_file(target, snapshot.to_document())
    except FileExistsError:
        existing = BlockSnapshot.from_document(load_json_file(target))
        if existing != snapshot:
            raise IntegrityError(
                "el almacén contiene otro snapshot bajo la misma identidad"
            )
        return target, False
    return target, True


def create_listener(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    backlog: int = 1,
) -> socket.socket:
    validate_loopback_host(host)
    _validate_port(port, allow_zero=True)
    if type(backlog) is not int or backlog <= 0:
        raise WireProtocolError("backlog debe ser un entero positivo")

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, port))
        listener.listen(backlog)
    except OSError as exc:
        listener.close()
        raise TransportError(f"no se pudo escuchar en {host}:{port}") from exc
    return listener


def _best_effort_rejection(
    connection: socket.socket,
    request_id: str | None,
    code: str,
    detail: str,
    max_frame_bytes: int,
) -> None:
    try:
        response = make_rejection(request_id, code, detail)
        send_document(connection, response, max_frame_bytes=max_frame_bytes)
    except (BCMError, OSError):
        pass


def receive_one(
    listener: socket.socket,
    inbox: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
) -> ReceivedTransfer:
    _validate_timeout(timeout)
    listener.settimeout(timeout)
    try:
        connection, address = listener.accept()
    except socket.timeout as exc:
        raise TransportError("tiempo agotado esperando una conexión") from exc
    except OSError as exc:
        raise TransportError("falló la aceptación de la conexión") from exc

    request_id: str | None = None
    with connection:
        connection.settimeout(timeout)
        try:
            document = receive_document(
                connection,
                max_frame_bytes=max_frame_bytes,
            )
            if isinstance(document, dict):
                candidate_id = document.get("request_id")
                if (
                    isinstance(candidate_id, str)
                    and _REQUEST_ID_PATTERN.fullmatch(candidate_id) is not None
                ):
                    request_id = candidate_id
            request_id, snapshot = parse_transfer_request(document)
            path, stored = store_snapshot(snapshot, inbox)
            response = make_acceptance(
                request_id,
                snapshot.content_hash,
                stored=stored,
            )
            send_document(
                connection,
                response,
                max_frame_bytes=max_frame_bytes,
            )
            peer = f"{address[0]}:{address[1]}"
            return ReceivedTransfer(
                request_id=request_id,
                content_hash=snapshot.content_hash,
                block_id=snapshot.block_id,
                generation=snapshot.generation,
                stored=stored,
                path=path,
                peer=peer,
            )
        except BCMError as exc:
            _best_effort_rejection(
                connection,
                request_id,
                "invalid-request",
                str(exc),
                max_frame_bytes,
            )
            raise
        except OSError:
            _best_effort_rejection(
                connection,
                request_id,
                "storage-error",
                "no se pudo almacenar el snapshot",
                max_frame_bytes,
            )
            raise


def send_snapshot(
    snapshot: BlockSnapshot,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
    max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
    request_id: str | None = None,
) -> TransferReceipt:
    validate_loopback_host(host)
    _validate_port(port)
    _validate_timeout(timeout)
    request = make_transfer_request(snapshot, request_id=request_id)
    transfer_id = request["request_id"]
    if not isinstance(transfer_id, str):  # defensa para cambios futuros
        raise WireProtocolError("request_id no es textual")

    try:
        connection = socket.create_connection((host, port), timeout=timeout)
    except OSError as exc:
        raise TransportError(f"no se pudo conectar con {host}:{port}") from exc
    with connection:
        connection.settimeout(timeout)
        send_document(
            connection,
            request,
            max_frame_bytes=max_frame_bytes,
        )
        response = receive_document(
            connection,
            max_frame_bytes=max_frame_bytes,
        )
    return parse_transfer_response(
        response,
        expected_request_id=transfer_id,
        expected_content_hash=snapshot.content_hash,
    )

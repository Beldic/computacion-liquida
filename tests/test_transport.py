import copy
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from bcm.errors import (
    IntegrityError,
    RemoteRejectedError,
    TransportError,
    WireProtocolError,
)
from bcm.isa import Opcode
from bcm.model import BCMBlock, Instruction
from bcm.snapshot import create_snapshot
from bcm.transport import (
    create_listener,
    make_acceptance,
    make_rejection,
    make_transfer_request,
    parse_transfer_request,
    parse_transfer_response,
    receive_document,
    receive_one,
    send_document,
    send_snapshot,
    store_snapshot,
    validate_loopback_host,
)


def transport_snapshot():
    block = BCMBlock(
        block_id="transporte-local",
        generation=0,
        owner="process-a",
        code=(Instruction(Opcode.PUSH, (7,)), Instruction(Opcode.HALT)),
    )
    return create_snapshot(block)


class FrameTests(unittest.TestCase):
    def test_document_round_trip_uses_one_frame(self) -> None:
        sender, receiver = socket.socketpair()
        with sender, receiver:
            send_document(sender, {"mensaje": "cómputo", "generation": 2})
            rebuilt = receive_document(receiver)

        self.assertEqual(rebuilt, {"mensaje": "cómputo", "generation": 2})

    def test_outgoing_frame_limit_is_enforced(self) -> None:
        sender, receiver = socket.socketpair()
        with sender, receiver:
            with self.assertRaises(WireProtocolError):
                send_document(sender, {"payload": "demasiado"}, max_frame_bytes=4)

    def test_declared_oversized_frame_is_rejected_before_payload(self) -> None:
        sender, receiver = socket.socketpair()
        with sender, receiver:
            sender.sendall((5).to_bytes(4, "big"))
            with self.assertRaises(WireProtocolError):
                receive_document(receiver, max_frame_bytes=4)

    def test_truncated_frame_is_rejected(self) -> None:
        sender, receiver = socket.socketpair()
        with sender, receiver:
            sender.sendall((10).to_bytes(4, "big") + b"{}")
            sender.shutdown(socket.SHUT_WR)
            with self.assertRaises(TransportError):
                receive_document(receiver)

    def test_noncanonical_json_frame_is_rejected(self) -> None:
        sender, receiver = socket.socketpair()
        payload = b'{"b":2, "a":1}'
        with sender, receiver:
            sender.sendall(len(payload).to_bytes(4, "big") + payload)
            with self.assertRaises(WireProtocolError):
                receive_document(receiver)


class WireMessageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = transport_snapshot()
        self.request_id = "a" * 32

    def test_request_round_trip_verifies_snapshot(self) -> None:
        request = make_transfer_request(
            self.snapshot,
            request_id=self.request_id,
        )
        request_id, rebuilt = parse_transfer_request(request)

        self.assertEqual(request_id, self.request_id)
        self.assertEqual(rebuilt, self.snapshot)

    def test_tampered_snapshot_is_rejected_before_acceptance(self) -> None:
        request = make_transfer_request(
            self.snapshot,
            request_id=self.request_id,
        )
        tampered = copy.deepcopy(request)
        tampered["snapshot"]["payload"]["block"]["state"]["pc"] = 1

        with self.assertRaises(IntegrityError):
            parse_transfer_request(tampered)

    def test_acceptance_must_confirm_request_and_hash(self) -> None:
        response = make_acceptance(
            self.request_id,
            self.snapshot.content_hash,
            stored=True,
        )
        receipt = parse_transfer_response(
            response,
            expected_request_id=self.request_id,
            expected_content_hash=self.snapshot.content_hash,
        )

        self.assertTrue(receipt.stored)
        self.assertEqual(receipt.content_hash, self.snapshot.content_hash)

    def test_remote_rejection_is_explicit(self) -> None:
        response = make_rejection(
            self.request_id,
            "invalid-request",
            "snapshot alterado",
        )

        with self.assertRaises(RemoteRejectedError) as context:
            parse_transfer_response(
                response,
                expected_request_id=self.request_id,
                expected_content_hash=self.snapshot.content_hash,
            )

        self.assertEqual(context.exception.code, "invalid-request")

    def test_non_loopback_host_is_rejected(self) -> None:
        with self.assertRaises(WireProtocolError):
            validate_loopback_host("0.0.0.0")


class LocalTransferTests(unittest.TestCase):
    def test_content_addressed_store_is_idempotent(self) -> None:
        snapshot = transport_snapshot()
        with tempfile.TemporaryDirectory() as temporary:
            inbox = Path(temporary)
            first_path, first_stored = store_snapshot(snapshot, inbox)
            second_path, second_stored = store_snapshot(snapshot, inbox)

        self.assertEqual(first_path, second_path)
        self.assertTrue(first_stored)
        self.assertFalse(second_stored)

    def test_snapshot_crosses_a_real_loopback_connection(self) -> None:
        snapshot = transport_snapshot()
        received = []
        errors = []

        with tempfile.TemporaryDirectory() as temporary:
            inbox = Path(temporary)
            with create_listener("127.0.0.1", 0) as listener:
                port = listener.getsockname()[1]

                def receive_in_thread() -> None:
                    try:
                        received.append(
                            receive_one(listener, inbox, timeout=2.0)
                        )
                    except BaseException as exc:
                        errors.append(exc)

                thread = threading.Thread(target=receive_in_thread, daemon=True)
                thread.start()
                receipt = send_snapshot(
                    snapshot,
                    host="127.0.0.1",
                    port=port,
                    timeout=2.0,
                    request_id="b" * 32,
                )
                thread.join(timeout=3.0)

            self.assertFalse(thread.is_alive())
            if errors:
                raise errors[0]
            self.assertEqual(len(received), 1)
            transfer = received[0]
            self.assertTrue(transfer.path.is_file())
            self.assertEqual(transfer.content_hash, snapshot.content_hash)
            self.assertEqual(transfer.block_id, snapshot.block_id)
            self.assertTrue(transfer.stored)
            self.assertTrue(receipt.stored)
            self.assertEqual(receipt.content_hash, snapshot.content_hash)

    def test_tampered_transfer_is_rejected_without_persistence(self) -> None:
        snapshot = transport_snapshot()
        request_id = "c" * 32
        request = make_transfer_request(snapshot, request_id=request_id)
        request["snapshot"]["payload"]["block"]["state"]["pc"] = 1
        server_errors = []

        with tempfile.TemporaryDirectory() as temporary:
            inbox = Path(temporary) / "inbox"
            with create_listener("127.0.0.1", 0) as listener:
                port = listener.getsockname()[1]

                def reject_in_thread() -> None:
                    try:
                        receive_one(listener, inbox, timeout=2.0)
                    except BaseException as exc:
                        server_errors.append(exc)

                thread = threading.Thread(target=reject_in_thread, daemon=True)
                thread.start()
                with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client:
                    client.settimeout(2.0)
                    send_document(client, request)
                    response = receive_document(client)
                with self.assertRaises(RemoteRejectedError):
                    parse_transfer_response(
                        response,
                        expected_request_id=request_id,
                        expected_content_hash=snapshot.content_hash,
                    )
                thread.join(timeout=3.0)

            self.assertFalse(thread.is_alive())
            self.assertEqual(len(server_errors), 1)
            self.assertIsInstance(server_errors[0], IntegrityError)
            self.assertFalse(inbox.exists())


if __name__ == "__main__":
    unittest.main()

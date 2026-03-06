"""Tests for the TCP sender module."""

import socket
import struct
import threading
import time

from goatguard_agent.capture.sanitizer import SanitizedPacket
from goatguard_agent.transport.tcp_sender import TcpSender, HEADER_FORMAT, HEADER_SIZE


def _make_packet(port=443, data_size=96, orig_len=500):
    """Create a fake sanitized packet for testing."""
    return SanitizedPacket(
        data=b"\xAB" * data_size,
        orig_len=orig_len,
        dst_port=port,
        timestamp=time.time(),
    )


def _start_mock_collector(host="127.0.0.1", port=0):
    """Start a TCP server that accepts one connection and returns received packets.

    Using port=0 lets the OS assign a free port, so tests don't
    conflict with each other or with real services.

    Returns:
        (thread, server_socket, results_list)
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    actual_port = server.getsockname()[1]

    results = []

    def collector_loop():
        server.settimeout(10.0)
        try:
            conn, addr = server.accept()
            conn.settimeout(5.0)

            while True:
                header_data = conn.recv(HEADER_SIZE)
                if not header_data or len(header_data) < HEADER_SIZE:
                    break

                orig_len, dst_port, timestamp, data_len = struct.unpack(
                    HEADER_FORMAT, header_data
                )

                packet_data = conn.recv(data_len)
                results.append({
                    "orig_len": orig_len,
                    "dst_port": dst_port,
                    "timestamp": timestamp,
                    "data_len": data_len,
                    "data": packet_data,
                })

            conn.close()
        except socket.timeout:
            pass
        finally:
            server.close()

    thread = threading.Thread(target=collector_loop, daemon=True)
    thread.start()

    return thread, actual_port, results


# --- Connection ---

def test_connect_to_listening_server():
    """Sender should connect successfully to an available server."""
    thread, port, _ = _start_mock_collector()
    time.sleep(0.2)

    sender = TcpSender("127.0.0.1", port)
    result = sender.connect()
    sender.close()
    thread.join(timeout=5)

    assert result == True


def test_connect_to_nonexistent_server():
    """Connecting to a server that doesn't exist should return False."""
    sender = TcpSender("127.0.0.1", 1, reconnect_delay=0)
    result = sender.connect()

    assert result == False


def test_send_returns_false_without_connection():
    """Sending without a server should return False."""
    sender = TcpSender("127.0.0.1", 1, reconnect_delay=0)

    packet = _make_packet()
    result = sender.send_batch([packet])

    assert result == False


# --- Sending ---

def test_send_single_packet():
    """A single packet should arrive with correct metadata."""
    thread, port, results = _start_mock_collector()
    time.sleep(0.2)

    sender = TcpSender("127.0.0.1", port)
    packet = _make_packet(port=443, data_size=96, orig_len=500)
    sender.send_batch([packet])
    sender.close()
    thread.join(timeout=5)

    assert len(results) == 1
    assert results[0]["orig_len"] == 500
    assert results[0]["dst_port"] == 443
    assert results[0]["data_len"] == 96


def test_send_batch_multiple_packets():
    """Multiple packets in a batch should all arrive in order."""
    thread, port, results = _start_mock_collector()
    time.sleep(0.2)

    sender = TcpSender("127.0.0.1", port)
    packets = [
        _make_packet(port=53, data_size=60, orig_len=60),
        _make_packet(port=443, data_size=96, orig_len=2586),
        _make_packet(port=80, data_size=96, orig_len=150),
    ]
    sender.send_batch(packets)
    sender.close()
    thread.join(timeout=5)

    assert len(results) == 3
    assert results[0]["dst_port"] == 53
    assert results[1]["dst_port"] == 443
    assert results[1]["orig_len"] == 2586
    assert results[2]["dst_port"] == 80


def test_send_preserves_data_content():
    """The actual packet bytes should arrive unchanged."""
    thread, port, results = _start_mock_collector()
    time.sleep(0.2)

    sender = TcpSender("127.0.0.1", port)
    packet = _make_packet(port=443, data_size=50, orig_len=50)
    sender.send_batch([packet])
    sender.close()
    thread.join(timeout=5)

    assert results[0]["data"] == b"\xAB" * 50


def test_send_returns_false_without_connection():
    """Sending without a server should return False."""
    sender = TcpSender("127.0.0.1", 1)
    sender._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sender._sock.settimeout(1.0)

    packet = _make_packet()
    result = sender.send_batch([packet])

    assert result == False
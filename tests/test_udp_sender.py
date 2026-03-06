"""Tests for the UDP sender module."""

import json
import socket
import threading
import time

from goatguard_agent.transport.udp_sender import UdpSender


def test_send_delivers_json():
    """Data sent via UDP should arrive as valid JSON."""
    received = []

    def receiver():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        received.append(port)
        sock.settimeout(5.0)
        data, _ = sock.recvfrom(4096)
        received.append(json.loads(data.decode("utf-8")))
        sock.close()

    thread = threading.Thread(target=receiver, daemon=True)
    thread.start()
    time.sleep(0.3)

    port = received[0]
    sender = UdpSender("127.0.0.1", port)
    result = sender.send({"test": "hello", "value": 42})
    sender.close()

    thread.join(timeout=5)

    assert result == True
    assert received[1]["test"] == "hello"
    assert received[1]["value"] == 42


def test_send_returns_true_on_success():
    """Successful send should return True."""
    sender = UdpSender("127.0.0.1", 9998)
    result = sender.send({"data": "test"})
    sender.close()
    assert result == True
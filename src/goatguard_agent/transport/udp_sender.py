"""
UDP sender for transmitting system metrics to the collector.

Serializes SystemMetrics as JSON and sends them as UDP datagrams
to the configured collector address. UDP is used because metrics
are periodic and loss-tolerant: a lost packet is replaced by the
next one 5 seconds later.

Requirements: RF-006 (UDP metrics transmission)
OSI layers:   L3 (IP addressing), L4 (UDP transport), L7 (JSON payload)
"""

import json
import logging
import socket
from dataclasses import asdict

logger = logging.getLogger(__name__)

# is a class, because it has an STATE
class UdpSender:
    """Sends data to the collector via UDP datagrams."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logger.info(f"UDP sender initialized -> {host}:{port}")

    def send(self, data: dict) -> bool:
        """Serialize a dictionary as JSON and send it via UDP.

        Args:
            data: Dictionary to serialize and send.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            payload = json.dumps(data).encode("utf-8")
            self.sock.sendto(payload, (self.host, self.port))
            logger.debug(f"UDP sent {len(payload)} bytes -> {self.host}:{self.port}")
            return True

        except OSError as e:
            logger.error(f"UDP send failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the UDP socket."""
        self.sock.close()
        logger.info("UDP sender closed")
"""
TCP sender for transmitting captured packets to the collector.

Maintains a persistent TCP connection and sends sanitized packets
using a length-prefixed binary protocol. TCP is used instead of
UDP because captured traffic data is irreplaceable: if a packet
is lost in transit, it cannot be regenerated.

Wire format for each packet:
    [4 bytes: orig_len    ] uint32, network byte order
    [4 bytes: dst_port    ] uint32, network byte order
    [8 bytes: timestamp   ] float64 (double), network byte order
    [4 bytes: data_len    ] uint32, network byte order
    [N bytes: packet data ] raw bytes (truncated by sanitizer)

The collector reads the 20-byte header, knows exactly how many
bytes of data follow, reads them, and has a complete packet.

Requirements: RF-003 (TCP transmission of captured traffic)
OSI layers:   L4 (TCP stream with three-way handshake)
"""

import logging
import socket
import struct
import time

from goatguard_agent.capture.sanitizer import SanitizedPacket

logger = logging.getLogger(__name__)

HEADER_FORMAT = '! I I d I'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # = 20 bytes

class TcpSender:
    """Sends sanitized packets to the collector via persistent TCP.

    Maintains an open connection and reconnects automatically if
    the connection drops. Packets are sent with a length-prefixed
    header so the collector knows where each packet starts and ends.

    Args:
        host: Collector IP address.
        port: Collector TCP port.
        reconnect_delay: Seconds to wait before reconnection attempt.
    """

    def __init__(self, host: str, port: int, reconnect_delay: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.reconnect_delay = reconnect_delay
        self._sock = None
        self._connected = False

    def connect(self) -> bool:
        """Establish TCP connection to the collector.

        Performs the three-way handshake (SYN -> SYN-ACK -> ACK).
        Returns True if successful, False otherwise.
        """
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(10.0)
            self._sock.connect((self.host, self.port))
            self._connected = True
            logger.info(f"TCP connected to {self.host}:{self.port}")
            return True

        except OSError as e:
            logger.error(f"TCP connection failed: {e}")
            self._connected = False
            return False
    
    def send_batch(self, packets: list[SanitizedPacket]) -> bool:
        """Send a batch of sanitized packets to the collector.

        Each packet is prefixed with a 20-byte header containing
        orig_len, dst_port, timestamp, and data_len. The collector
        reads the header, knows the data size, and reads accordingly.

        Args:
            packets: List of sanitized packets from buffer.flush().

        Returns:
            True if all packets sent successfully, False otherwise.
        """
        if not self._connected:
            if not self.connect():
                return False

        try:
            for packet in packets:
                header = struct.pack(
                    HEADER_FORMAT,
                    packet.orig_len,
                    packet.dst_port,
                    packet.timestamp,
                    len(packet.data),
                )
                self._sock.sendall(header + packet.data)

            logger.debug(f"TCP sent {len(packets)} packets")
            return True

        except OSError as e:
            logger.error(f"TCP send failed: {e}")
            self._connected = False
            return False
        
    def reconnect(self) -> bool:
        """Close current connection and try to reconnect.

        Waits reconnect_delay seconds before attempting, to avoid
        flooding the collector with connection attempts.
        """
        self.close()
        logger.info(f"Reconnecting in {self.reconnect_delay}s...")
        time.sleep(self.reconnect_delay)
        return self.connect()
    
    def close(self) -> None:
        """Close the TCP connection."""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        self._connected = False
        logger.info("TCP sender closed")

"""
Thread-safe packet buffer for GOATGuard agent.

Accumulates sanitized packets from the capture thread and
delivers them in batches to the TCP sender. Uses a lock to
prevent data corruption when the capture thread (producer)
and the sender thread (consumer) access the buffer simultaneously.

This is a classic Producer-Consumer pattern:
    Producer: capture thread adds packets via put()
    Consumer: main thread retrieves all packets via flush()

Requirements: RF-001 (continuous capture without data loss)
"""
import logging
import threading
from collections import deque

from goatguard_agent.capture.sanitizer import SanitizedPacket

logger = logging.getLogger(__name__)

class PacketBuffer:
    """Thread-safe buffer that accumulates sanitized packets.

    Packets are added one by one from the capture thread and
    flushed in batches by the sender. A maximum size prevents
    unbounded memory growth if the sender falls behind.

    Args:
        max_size: Maximum packets to hold. Oldest packets are
                  dropped when full to prevent memory exhaustion.
    """

    def __init__(self, max_size: int = 10000) -> None:
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self.dropped_count = 0
        logger.info(f"Packet buffer initialized: max_size={max_size}")

    def put(self, packet: SanitizedPacket) -> None:
            """Add a sanitized packet to the buffer.

            Called from the capture thread. Thread-safe via lock.
            If the buffer is full, the oldest packet is automatically
            dropped by deque's maxlen behavior.

            Args:
                packet: The sanitized packet to buffer.
            """
            with self._lock:
                was_full = len(self._buffer) == self._buffer.maxlen
                self._buffer.append(packet)
                if was_full:
                    self.dropped_count += 1
                    logger.warning(
                        f"Buffer full, oldest packet dropped "
                        f"(total dropped: {self.dropped_count})"
                    )
    
    def flush(self) -> list[SanitizedPacket]:
        """Remove and return all buffered packets.

        Called from the main/sender thread. Returns a list of all
        accumulated packets and clears the buffer. Thread-safe.

        Returns:
            List of all buffered packets. Empty list if buffer was empty.
        """
        with self._lock:
            packets = list(self._buffer)
            self._buffer.clear()

        if packets:
            logger.debug(f"Flushed {len(packets)} packets from buffer")

        return packets
    
    def size(self) -> int:
        """Return the current number of packets in the buffer."""
        return len(self._buffer)
    
if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.DEBUG)

    buffer = PacketBuffer(max_size=5)

    # Simulate adding packets
    for i in range(7):
        fake_packet = SanitizedPacket(
            data=b"\x00" * 96,
            orig_len=200,
            dst_port=443,
            timestamp=time.time(),
        )
        buffer.put(fake_packet)
        print(f"Added packet {i+1}, buffer size: {buffer.size()}")

    print(f"\nDropped packets: {buffer.dropped_count}")

    # Flush
    packets = buffer.flush()
    print(f"Flushed {len(packets)} packets, buffer size: {buffer.size()}")
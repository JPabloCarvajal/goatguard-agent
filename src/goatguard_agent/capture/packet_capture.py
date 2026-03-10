"""
Continuous packet capture module for GOATGuard agent.

Runs in a separate thread, sniffing all traffic on the primary
network interface using scapy. Each captured packet is passed
to a callback function for processing (sanitization and buffering).

The capture runs in its own thread because scapy's sniff() is
blocking: it enters an infinite loop waiting for packets. Without
a separate thread, the main loop (metrics, heartbeat) would freeze.

Requirements: RF-001 (continuous traffic capture at endpoint level)
OSI layers:   L2 (Ethernet frames), L3 (IP), L4 (TCP/UDP)
Threading:    Uses daemon thread so capture stops when agent stops
"""

import logging
import threading
from typing import Callable

from scapy.all import sniff

logger = logging.getLogger(__name__)

class PacketCapture:
    """Captures network packets in a background thread.
    
    Uses scapy's sniff() in a daemon thread to continuously
    capture traffic. Each packet is passed to the provided
    callback function for processing.
    
    The capture does not process packets itself (Single
    Responsibility). It only captures and forwards them.
    
    Args:
        interface: Network interface name or "auto".
        callback: Function called for each captured packet.
                  Receives one argument: the scapy packet.
    """

    def __init__(self, interface: str, callback: Callable, bpf_filter: str = "") -> None:
        self.interface = interface if interface != "auto" else None
        self.callback = callback
        self.bpf_filter = bpf_filter
        self._thread = None
        self._running = False
    
    def start(self) -> None:
        """Start packet capture in a background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
        )
        self._thread.start()
        logger.info(
            f"Packet capture started on interface: "
            f"{self.interface or 'auto-detect'}"
        )
    
    def _capture_loop(self) -> None:
        """Internal capture loop that runs in the background thread.
        
        Calls scapy's sniff() which blocks indefinitely, capturing
        packets and forwarding each one to self.callback.
        
        If an error occurs (interface down, permissions), it logs
        the error and stops gracefully instead of crashing the agent.
        """
        try:
            sniff(
                iface=self.interface,
                prn=self.callback,
                store=False,
                stop_filter=lambda _: not self._running,
                filter=self.bpf_filter if self.bpf_filter else None,
            )
        except Exception as e:
            logger.error(f"Capture error: {e}")
            self._running = False

if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.DEBUG)

    packet_count = 0

    def simple_callback(packet):
        global packet_count
        packet_count += 1
        print(f"  Packet #{packet_count}: {len(packet)} bytes")

    capture = PacketCapture(interface=None, callback=simple_callback)
    capture.start()

    print("Capturing for 10 seconds...")
    time.sleep(10)

    capture.stop()
    print(f"\nTotal captured: {packet_count} packets")
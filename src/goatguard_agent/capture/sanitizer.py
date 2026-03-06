"""
Packet sanitizer for GOATGuard agent.

Applies dynamic slicing to captured packets based on destination
port. This protects confidentiality by removing payload data
that could contain sensitive information (passwords, tokens,
encrypted content) while preserving the network headers needed
for traffic analysis.

The headers of layers 2 (Ethernet), 3 (IP), and 4 (TCP/UDP) are
always preserved since they contain the fields required for flow
reconstruction and feature extraction: source/destination IPs,
ports, protocol, TTL, TCP flags, sequence numbers, window size.

Slicing rules from agent_config.yaml:
    - DNS (port 53):    keep 300 bytes (to see queried domain)
    - HTTP (port 80):   keep 300 bytes (to see Host header)
    - HTTPS (port 443): keep 300 bytes (to see SNI)
    - Everything else:  keep 96 bytes (headers only)

The original packet length (orig_len) is always preserved so the
analysis engine can calculate real bandwidth even though the
payload was truncated. The timestamp is preserved so the collector
can reconstruct timing-based metrics (flow duration, jitter, RTT).

Together, the truncated bytes + orig_len + timestamp give the
collector everything needed to build a valid PCAP file that tools
like Zeek can analyze to generate conn.log, dns.log, and extract
features compatible with datasets like UNSW-NB15.

Requirements: RF-002 (dynamic slicing with orig_len preservation)
OSI layers:   L4 (reads destination port from TCP/UDP header)
Security:     Confidentiality (CIA) - prevents sensitive data leakage
"""

import logging
import time
from dataclasses import dataclass

from scapy.all import raw, TCP, UDP

logger = logging.getLogger(__name__)


@dataclass
class SanitizedPacket:
    """A packet after slicing, ready to be buffered and sent.

    Attributes:
        data: The truncated packet bytes. Contains complete L2/L3/L4
              headers for flow analysis.
        orig_len: Original packet size before truncation. Critical for
                  bandwidth and volume calculations (sbytes, dbytes,
                  smeansz, Sload, Dload in UNSW-NB15 terms).
        dst_port: Destination port (0 if not TCP/UDP). Used by the
                  collector to identify the service (HTTP, DNS, etc).
        timestamp: Capture time as Unix epoch float. Required for
                   temporal metrics: flow duration, jitter, RTT,
                   inter-packet arrival time.
    """
    data: bytes
    orig_len: int
    dst_port: int
    timestamp: float


class PacketSanitizer:
    """Applies slicing rules to captured packets.

    Reads the destination port from the TCP or UDP header and
    selects the appropriate snap_len from the configured rules.
    If no rule matches, uses the default snap_len.

    Args:
        default_snap_len: Bytes to keep when no rule matches.
        rules: List of slicing rule objects from config, each
               having .ports (list[int]) and .snap_len (int).
    """

    def __init__(self, default_snap_len: int, rules: list) -> None:
        self.default_snap_len = default_snap_len
        self._port_to_snap_len = self._build_port_map(rules)
        logger.info(
            f"Sanitizer initialized: default={default_snap_len} bytes, "
            f"{len(self._port_to_snap_len)} port rules loaded"
        )

    def _build_port_map(self, rules: list) -> dict:
        """Convert config rules to a fast port -> snap_len lookup.

        The config has rules like:
            [SlicingRule(ports=[53], snap_len=300), ...]

        This converts them to:
            {53: 300, 80: 300, 443: 300}

        So looking up the snap_len for a port is O(1) instead of
        looping through all rules every time.
        """
        port_map = {}
        for rule in rules:
            snap_len = rule.snap_len
            for port in rule.ports:
                port_map[port] = snap_len
                logger.debug(f"Slicing rule: port {port} -> {snap_len} bytes")
        return port_map

    def sanitize(self, packet) -> SanitizedPacket:
        """Apply slicing to a captured packet.

        Process:
        1. Get the raw bytes and measure original length
        2. Record the capture timestamp
        3. Extract destination port from TCP/UDP header
        4. Look up snap_len for that port
        5. Truncate the bytes to snap_len
        6. Return SanitizedPacket with data + orig_len + timestamp

        Packets smaller than snap_len are not modified.
        Non-IP packets (ARP, etc.) use default snap_len.

        Args:
            packet: Raw scapy packet from the capture thread.

        Returns:
            SanitizedPacket with truncated data and original length.
        """
        raw_bytes = raw(packet)
        orig_len = len(raw_bytes)
        dst_port = self._extract_dst_port(packet)
        snap_len = self._get_snap_len(dst_port)
        truncated = raw_bytes[:snap_len]

        if orig_len > snap_len:
            logger.debug(
                f"Sliced: port {dst_port}, {orig_len} -> {snap_len} bytes"
            )

        return SanitizedPacket(
            data=truncated,
            orig_len=orig_len,
            dst_port=dst_port,
            timestamp=time.time(),
        )

    def _extract_dst_port(self, packet) -> int:
        """Extract destination port from TCP or UDP header.

        Uses scapy's layer detection instead of manual byte parsing.
        Returns 0 for non-TCP/UDP packets (ARP, ICMP, etc.) since
        they don't have port numbers.
        """
        if packet.haslayer(TCP):
            return packet[TCP].dport
        elif packet.haslayer(UDP):
            return packet[UDP].dport
        return 0

    def _get_snap_len(self, dst_port: int) -> int:
        """Look up the snap_len for a given destination port.

        Returns the configured snap_len if a rule exists for this
        port, otherwise returns the default snap_len.

        Uses dict.get() for O(1) lookup with fallback to default.
        """
        return self._port_to_snap_len.get(dst_port, self.default_snap_len)

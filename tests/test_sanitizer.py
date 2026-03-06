"""Tests for the packet sanitizer module."""

import time
from goatguard_agent.capture.sanitizer import PacketSanitizer, SanitizedPacket


class FakeRule:
    """Mimics SlicingRule from config for testing."""
    def __init__(self, ports, snap_len):
        self.ports = ports
        self.snap_len = snap_len


def _make_sanitizer():
    """Create a sanitizer with standard test rules."""
    rules = [
        FakeRule([53], 300),
        FakeRule([80], 300),
        FakeRule([443], 300),
    ]
    return PacketSanitizer(default_snap_len=96, rules=rules)


# --- Port map building ---

def test_port_map_built_correctly():
    """Each port should map to its configured snap_len."""
    sanitizer = _make_sanitizer()
    assert sanitizer._port_to_snap_len[53] == 300
    assert sanitizer._port_to_snap_len[80] == 300
    assert sanitizer._port_to_snap_len[443] == 300


def test_unknown_port_uses_default():
    """Ports without rules should return default snap_len."""
    sanitizer = _make_sanitizer()
    assert sanitizer._get_snap_len(8080) == 96


def test_known_port_uses_rule():
    """Ports with rules should return configured snap_len."""
    sanitizer = _make_sanitizer()
    assert sanitizer._get_snap_len(443) == 300


# --- SanitizedPacket dataclass ---

def test_sanitized_packet_fields():
    """SanitizedPacket should store all required fields."""
    packet = SanitizedPacket(
        data=b"\x00" * 96,
        orig_len=500,
        dst_port=443,
        timestamp=1000.0,
    )
    assert len(packet.data) == 96
    assert packet.orig_len == 500
    assert packet.dst_port == 443
    assert packet.timestamp == 1000.0


def test_sanitized_packet_preserves_orig_len():
    """orig_len should reflect original size, not truncated size."""
    packet = SanitizedPacket(
        data=b"\x00" * 96,
        orig_len=2586,
        dst_port=443,
        timestamp=time.time(),
    )
    assert packet.orig_len == 2586
    assert len(packet.data) == 96
    assert packet.orig_len > len(packet.data)
"""Tests for the packet buffer module."""

import time
import threading
from goatguard_agent.capture.buffer import PacketBuffer
from goatguard_agent.capture.sanitizer import SanitizedPacket


def _make_packet(port=443):
    """Create a fake sanitized packet for testing."""
    return SanitizedPacket(
        data=b"\x00" * 96,
        orig_len=200,
        dst_port=port,
        timestamp=time.time(),
    )


# --- Basic operations ---

def test_put_and_flush():
    """Packets put in should come out on flush."""
    buffer = PacketBuffer(max_size=100)
    buffer.put(_make_packet())
    buffer.put(_make_packet())

    packets = buffer.flush()
    assert len(packets) == 2


def test_flush_empties_buffer():
    """After flush, buffer should be empty."""
    buffer = PacketBuffer(max_size=100)
    buffer.put(_make_packet())

    buffer.flush()
    assert buffer.size() == 0


def test_flush_empty_buffer():
    """Flushing an empty buffer should return empty list."""
    buffer = PacketBuffer(max_size=100)
    packets = buffer.flush()
    assert packets == []


def test_size_tracks_count():
    """Size should reflect current packet count."""
    buffer = PacketBuffer(max_size=100)
    assert buffer.size() == 0

    buffer.put(_make_packet())
    assert buffer.size() == 1

    buffer.put(_make_packet())
    assert buffer.size() == 2


# --- Overflow behavior ---

def test_overflow_drops_oldest():
    """When full, oldest packets should be dropped."""
    buffer = PacketBuffer(max_size=3)

    buffer.put(_make_packet(port=1))
    buffer.put(_make_packet(port=2))
    buffer.put(_make_packet(port=3))
    buffer.put(_make_packet(port=4))  # this drops port=1

    packets = buffer.flush()
    assert len(packets) == 3
    assert packets[0].dst_port == 2  # oldest surviving
    assert packets[2].dst_port == 4  # newest


def test_overflow_increments_dropped_count():
    """Dropped packet counter should track overflows."""
    buffer = PacketBuffer(max_size=2)

    buffer.put(_make_packet())
    buffer.put(_make_packet())
    buffer.put(_make_packet())  # overflow

    assert buffer.dropped_count == 1


# --- Thread safety ---

def test_concurrent_put_and_flush():
    """Buffer should handle simultaneous put and flush without crashing."""
    buffer = PacketBuffer(max_size=1000)
    errors = []

    def producer():
        try:
            for _ in range(500):
                buffer.put(_make_packet())
        except Exception as e:
            errors.append(e)

    def consumer():
        try:
            for _ in range(50):
                buffer.flush()
                time.sleep(0.01)
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=producer)
    t2 = threading.Thread(target=consumer)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert errors == []
"""Tests for the system metrics collector."""

from goatguard_agent.metrics.collector import collect_metrics, SystemMetrics


def test_collect_returns_system_metrics():
    """collect_metrics should return a SystemMetrics instance."""
    metrics = collect_metrics()
    assert isinstance(metrics, SystemMetrics)


def test_cpu_percent_in_range():
    """CPU percent should be between 0 and 100."""
    metrics = collect_metrics()
    assert 0.0 <= metrics.cpu_percent <= 100.0


def test_cpu_count_positive():
    """CPU count should be at least 1."""
    metrics = collect_metrics()
    assert metrics.cpu_count >= 1


def test_ram_percent_in_range():
    """RAM percent should be between 0 and 100."""
    metrics = collect_metrics()
    assert 0.0 <= metrics.ram_percent <= 100.0


def test_ram_total_positive():
    """Total RAM should be greater than zero."""
    metrics = collect_metrics()
    assert metrics.ram_total_bytes > 0


def test_ram_available_less_than_total():
    """Available RAM should not exceed total RAM."""
    metrics = collect_metrics()
    assert metrics.ram_available_bytes <= metrics.ram_total_bytes


def test_disk_percent_in_range():
    """Disk usage should be between 0 and 100."""
    metrics = collect_metrics()
    assert 0.0 <= metrics.disk_usage_percent <= 100.0


def test_uptime_positive():
    """Uptime should be greater than zero."""
    metrics = collect_metrics()
    assert metrics.uptime_seconds > 0


def test_timestamp_exists():
    """Timestamp should be a positive float."""
    metrics = collect_metrics()
    assert metrics.timestamp > 0
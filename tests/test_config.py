"""Tests for the configuration module."""

import pytest
from pathlib import Path

from goatguard_agent.config import load_config, ConfigError
from goatguard_agent.config.models import (
    AgentConfig,
    CollectorConfig,
    IntervalsConfig,
    SlicingConfig,
    SlicingRule,
)
from goatguard_agent.config.validator import validate_config

@pytest.fixture
def valid_yaml_file(tmp_path):
    """Create a temporary valid YAML config file."""
    content = """
collector:
  host: "10.0.0.1"
  tcp_port: 8888
  udp_port: 8889

intervals:
  metrics_seconds: 10
  heartbeat_seconds: 60
  arp_scan_seconds: 120

capture:
  interface: "eth0"

slicing:
  default_snap_len: 128
  rules:
    - ports: [53]
      snap_len: 256
    - ports: [443]
      snap_len: 300

logging:
  level: "DEBUG"
  file: "test.log"
"""
    config_file = tmp_path / "agent_config.yaml"
    config_file.write_text(content)
    return config_file

def test_load_valid_config(valid_yaml_file):
    """A valid YAML file should load all values correctly."""
    config = load_config(valid_yaml_file)

    assert config.collector.host == "10.0.0.1"
    assert config.collector.tcp_port == 8888
    assert config.collector.udp_port == 8889
    assert config.intervals.metrics_seconds == 10
    assert config.capture.interface == "eth0"
    assert config.slicing.default_snap_len == 128
    assert len(config.slicing.rules) == 2
    assert config.logging.level == "DEBUG"

def test_load_empty_yaml_uses_defaults(tmp_path):
    """An empty YAML should use all default values."""
    config_file = tmp_path / "agent_config.yaml"
    config_file.write_text("")

    config = load_config(config_file)

    assert config.collector.host == "192.168.1.100"
    assert config.collector.tcp_port == 9999
    assert config.intervals.metrics_seconds == 5
    assert config.capture.interface == "auto"
    assert config.slicing.default_snap_len == 96


def test_load_minimal_yaml(tmp_path):
    """A YAML with only one field should use defaults for the rest."""
    config_file = tmp_path / "agent_config.yaml"
    config_file.write_text("collector:\n  host: '1.2.3.4'\n")

    config = load_config(config_file)

    assert config.collector.host == "1.2.3.4"
    assert config.collector.tcp_port == 9999


def test_file_not_found():
    """A nonexistent file should raise ConfigError."""
    with pytest.raises(ConfigError):
        load_config(Path("/nonexistent/config.yaml"))


def test_invalid_yaml(tmp_path):
    """Malformed YAML should raise ConfigError."""
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("esto: no: es: yaml: [}")

    with pytest.raises(ConfigError):
        load_config(config_file)


def test_invalid_port_too_high():
    """A port above 65535 should fail validation."""
    config = AgentConfig(collector=CollectorConfig(tcp_port=99999))

    with pytest.raises(ConfigError):
        validate_config(config)


def test_invalid_port_zero():
    """Port 0 should fail validation."""
    config = AgentConfig(collector=CollectorConfig(tcp_port=0))

    with pytest.raises(ConfigError):
        validate_config(config)


def test_invalid_metrics_interval():
    """Metrics interval below 1 should fail validation."""
    config = AgentConfig(intervals=IntervalsConfig(metrics_seconds=0))

    with pytest.raises(ConfigError):
        validate_config(config)


def test_slicing_rules_parsed(valid_yaml_file):
    """Slicing rules should be parsed from YAML correctly."""
    config = load_config(valid_yaml_file)

    assert len(config.slicing.rules) == 2
    assert config.slicing.rules[0].ports == [53]
    assert config.slicing.rules[0].snap_len == 256
    assert config.slicing.rules[1].ports == [443]
    assert config.slicing.rules[1].snap_len == 300


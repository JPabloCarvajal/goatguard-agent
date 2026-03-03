"""
Configuration file loading and parsing.

Finds the YAML file, reads it, builds the typed config objects,
and runs validation before returning.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from goatguard_agent.config.models import (
    AgentConfig,
    CaptureConfig,
    CollectorConfig,
    ConfigError,
    IntervalsConfig,
    LoggingConfig,
)
from goatguard_agent.config.validator import validate_config

logger = logging.getLogger(__name__)


def load_config(file_path: Optional[Path] = None) -> AgentConfig:
    """
    Main entry point: load, parse, and validate agent configuration.

    Args:
        file_path: Path to YAML file. If None, searches default locations.

    Returns:
        Fully loaded and validated AgentConfig.

    Raises:
        ConfigError: If the file is missing, malformed, or has invalid values.
    """
    if file_path is None:
        file_path = _find_config_file()

    logger.info(f"Loading configuration from: {file_path}")

    raw = _load_yaml_file(file_path)
    config = _build_config(raw)
    validate_config(config)

    logger.info(
        f"Configuration loaded: collector={config.collector.host}:"
        f"{config.collector.tcp_port}, interface={config.capture.interface}"
    )

    return config


def _find_config_file() -> Path:
    """Search for the config file in default locations."""
    search_paths = [
        Path("config") / "agent_config.yaml",
        Path("agent_config.yaml"),
        Path.home() / ".goatguard" / "agent_config.yaml",
    ]

    for path in search_paths:
        if path.exists():
            logger.info(f"Config file found: {path}")
            return path

    searched = ", ".join(str(p) for p in search_paths)
    raise ConfigError(f"Config file not found. Searched: {searched}")


def _load_yaml_file(file_path: Path) -> dict:
    """Read and parse a YAML file into a dictionary."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            return {}

        if not isinstance(data, dict):
            raise ConfigError(f"File {file_path} does not contain valid YAML")

        return data

    except yaml.YAMLError as e:
        raise ConfigError(f"YAML parse error in {file_path}: {e}")
    except OSError as e:
        raise ConfigError(f"Cannot read file {file_path}: {e}")


def _build_config(raw: dict) -> AgentConfig:
    """
    Build typed config objects from a raw dictionary.

    Uses .get(key, default) so that missing YAML sections
    or fields gracefully fall back to defaults.
    """
    collector_data = raw.get("collector", {})
    collector = CollectorConfig(
        host=collector_data.get("host", "192.168.1.100"),
        tcp_port=collector_data.get("tcp_port", 9999),
        udp_port=collector_data.get("udp_port", 9998),
    )

    intervals_data = raw.get("intervals", {})
    intervals = IntervalsConfig(
        metrics_seconds=intervals_data.get("metrics_seconds", 5),
        heartbeat_seconds=intervals_data.get("heartbeat_seconds", 30),
        arp_scan_seconds=intervals_data.get("arp_scan_seconds", 60),
    )

    capture_data = raw.get("capture", {})
    capture = CaptureConfig(
        interface=capture_data.get("interface", "auto"),
    )

    logging_data = raw.get("logging", {})
    logging_cfg = LoggingConfig(
        level=logging_data.get("level", "INFO"),
        file=logging_data.get("file", "goatguard_agent.log"),
    )

    return AgentConfig(
        collector=collector,
        intervals=intervals,
        capture=capture,
        logging=logging_cfg,
    )
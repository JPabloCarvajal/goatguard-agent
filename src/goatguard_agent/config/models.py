"""
Data models for agent configuration.

Each dataclass maps to a section in agent_config.yaml.
Default values are used when a field is missing from the YAML.
"""

from dataclasses import dataclass, field


class ConfigError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""
    pass


@dataclass
class CollectorConfig:
    """Connection settings for the central collector server."""
    host: str = "192.168.1.100"
    tcp_port: int = 9999
    udp_port: int = 9998


@dataclass
class IntervalsConfig:
    """How often (in seconds) the agent performs each cyclic task."""
    metrics_seconds: int = 5
    heartbeat_seconds: int = 30
    arp_scan_seconds: int = 60


@dataclass
class CaptureConfig:
    """Packet capture settings."""
    interface: str = "auto"


@dataclass
class LoggingConfig:
    """Logging output settings."""
    level: str = "INFO"
    file: str = "goatguard_agent.log"


@dataclass
class AgentConfig:
    """
    Root configuration object that groups all sections.

    Usage:
        config.collector.host          -> "192.168.1.100"
        config.intervals.metrics_seconds -> 5
        config.capture.interface       -> "auto"
    """
    collector: CollectorConfig = field(default_factory=CollectorConfig)
    intervals: IntervalsConfig = field(default_factory=IntervalsConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
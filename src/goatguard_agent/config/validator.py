"""
Validation rules for agent configuration.

Checks that ports are in valid range, intervals are positive,
and logging level is recognized.
"""
import logging

from goatguard_agent.config.models import AgentConfig, ConfigError

logger = logging.getLogger(__name__)


def validate_config(config: AgentConfig) -> None:
    """
    Validate that all configuration values are coherent.

    Args:
        config: The configuration object to validate.

    Raises:
        ConfigError: If any value is invalid.
    """
    _validate_ports(config)
    _validate_intervals(config)
    _validate_logging_level(config)

    logger.debug("Configuration validated successfully")


def _validate_ports(config: AgentConfig) -> None:
    """Check that all ports are within the valid TCP/UDP range (1-65535)."""
    for port_name, port_value in [
        ("tcp_port", config.collector.tcp_port),
        ("udp_port", config.collector.udp_port),
    ]:
        if not 1 <= port_value <= 65535:
            raise ConfigError(
                f"Invalid port '{port_name}': {port_value}. "
                f"Must be between 1 and 65535."
            )


def _validate_intervals(config: AgentConfig) -> None:
    """Check that all time intervals are positive."""
    if config.intervals.metrics_seconds < 1:
        raise ConfigError("Metrics interval must be >= 1 second")

    if config.intervals.heartbeat_seconds < 1:
        raise ConfigError("Heartbeat interval must be >= 1 second")

    if config.intervals.arp_scan_seconds < 1:
        raise ConfigError("ARP scan interval must be >= 1 second")


def _validate_logging_level(config: AgentConfig) -> None:
    """Check that the logging level is a recognized Python logging level."""
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if config.logging.level.upper() not in valid_levels:
        raise ConfigError(
            f"Invalid logging level: '{config.logging.level}'. "
            f"Valid values: {valid_levels}"
        )
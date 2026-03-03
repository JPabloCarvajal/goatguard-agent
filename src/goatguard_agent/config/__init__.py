"""
Configuration package for the GOATGuard agent.

Usage:
    from goatguard_agent.config import load_config, AgentConfig, ConfigError
"""

from goatguard_agent.config.models import (
    AgentConfig,
    CaptureConfig,
    CollectorConfig,
    ConfigError,
    IntervalsConfig,
    LoggingConfig,
)
from goatguard_agent.config.loader import load_config
"""
Configuration package for the GOATGuard agent.

Usage:
    from goatguard_agent.config import load_config, AgentConfig, ConfigError
"""

from goatguard_agent.config.models import (
    AgentConfig as AgentConfig,
    CaptureConfig as CaptureConfig,
    CollectorConfig as CollectorConfig,
    ConfigError as ConfigError,
    IntervalsConfig as IntervalsConfig,
    LoggingConfig as LoggingConfig,
    SlicingConfig as SlicingConfig,
    SlicingRule as SlicingRule,
)
from goatguard_agent.config.loader import load_config as load_config
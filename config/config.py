"""Quick runner to test the config module."""

import sys
import logging

# Add src/ to Python's search path so it finds goatguard_agent
sys.path.insert(0, "src")

from goatguard_agent.config import load_config, ConfigError

logging.basicConfig(level=logging.DEBUG)

try:
    config = load_config()
    print(f"\nConfiguration loaded successfully:")
    print(f"  Collector: {config.collector.host}:{config.collector.tcp_port}")
    print(f"  UDP port:  {config.collector.udp_port}")
    print(f"  Metrics every:   {config.intervals.metrics_seconds}s")
    print(f"  Heartbeat every: {config.intervals.heartbeat_seconds}s")
    print(f"  ARP scan every:  {config.intervals.arp_scan_seconds}s")
    print(f"  Interface: {config.capture.interface}")
    print(f"  Log level: {config.logging.level}")
except ConfigError as e:
    print(f"\nERROR: {e}")
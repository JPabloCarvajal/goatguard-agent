"""
GOATGuard Agent — Main orchestrator.

Loads configuration, generates agent identity, and runs the
main loop that periodically collects system metrics and sends
them to the collector via UDP.

This module coordinates all other modules without performing
any low-level work itself (Single Responsibility Principle).

"""

import logging
import time
import sys
from dataclasses import asdict

from goatguard_agent.config import load_config, ConfigError
from goatguard_agent.identity import generate_agent_id, IdentityError
from goatguard_agent.metrics.collector import collect_metrics
from goatguard_agent.transport.udp_sender import UdpSender
from goatguard_agent.capture.packet_capture import PacketCapture
from goatguard_agent.capture.sanitizer import PacketSanitizer
from goatguard_agent.capture.buffer import PacketBuffer
from goatguard_agent.transport.tcp_sender import TcpSender


logger = logging.getLogger("goatguard_agent.main")

def setup_logging(level: str, log_file: str) -> None:
    """Configure logging to console and file."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger("goatguard_agent")
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


class GoatGuardAgent:
    """Main agent orchestrator. Coordinates all modules."""

    def __init__(self, config) -> None:
        self.config = config
        self.agent_id = ""
        self.udp_sender = None
        self.tcp_sender = None
        self.packet_capture = None
        self.sanitizer = None
        self.buffer = None
        self._running = False

    def initialize(self) -> None:
            """Set up identity and network connections.""" 
            self.interface_name = self.config.capture.interface
            self.agent_id = generate_agent_id(self.interface_name)

            logger.info(f"Agent ID: {self.agent_id}")

            self.udp_sender = UdpSender(
                host=self.config.collector.host,
                port=self.config.collector.udp_port,
            )
            self.tcp_sender = TcpSender(
                host=self.config.collector.host,
                port=self.config.collector.tcp_port,
            )

            self.sanitizer = PacketSanitizer(
                default_snap_len=self.config.slicing.default_snap_len,
                rules=self.config.slicing.rules,
            )

            self.buffer = PacketBuffer(max_size=10000)

            bpf_filter = (
                f"not (host {self.config.collector.host} and "
                f"(port {self.config.collector.tcp_port} or "
                f"port {self.config.collector.udp_port}))"
            )

            self.packet_capture = PacketCapture(
                interface=self.interface_name,
                callback=self._handle_packet,
                bpf_filter=bpf_filter,
            )
            self.packet_capture.start()

    def run(self) -> None:
        """Start the main agent loop."""
        self.initialize()
        self._running = True

        logger.info("Agent started. Press Ctrl+C to stop.")

        last_metrics_time = 0.0
        last_heartbeat_time = 0.0
        last_flush_time = 0.0

        try:
            while self._running:
                now = time.time()

                if now - last_metrics_time >= self.config.intervals.metrics_seconds:
                    self._send_metrics()
                    last_metrics_time = now

                if now - last_heartbeat_time >= self.config.intervals.heartbeat_seconds:
                    self._send_heartbeat()
                    last_heartbeat_time = now
                
                if now - last_flush_time >= 1.0:
                    self._flush_and_send()
                    last_flush_time = now

                time.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("Ctrl+C received")
        finally:
            self.shutdown()

    def _send_metrics(self) -> None:
        """Collect system metrics and send them via UDP."""
        try:
            metrics = collect_metrics(self.interface_name)
            payload = asdict(metrics)
            payload["agent_id"] = self.agent_id
            self.udp_sender.send(payload)

        except Exception as e:
            logger.error(f"Failed to send metrics: {e}")

    def _send_heartbeat(self) -> None:
        """Send heartbeat signal to the collector."""
        try:
            heartbeat = {
                "agent_id": self.agent_id,
                "type": "heartbeat",
                "timestamp": time.time(),
            }
            self.udp_sender.send(heartbeat)
            logger.debug("Heartbeat sent")

        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")

    def _flush_and_send(self) -> None:
        """Flush buffer and send packets to collector via TCP."""
        packets = self.buffer.flush()
        if not packets:
            return

        if not self.tcp_sender.send_batch(packets):
            logger.warning(f"Failed to send {len(packets)} packets, will retry")


    def shutdown(self) -> None:
        """Clean shutdown: close connections and free resources."""
        self._running = False
        if self.packet_capture:
            self.packet_capture.stop()
        if self.tcp_sender:
            self.tcp_sender.close()
        if self.udp_sender:
            self.udp_sender.close()
        logger.info("Agent stopped")

    
    def _handle_packet(self, packet) -> None:
        """Callback: sanitize captured packet and store in buffer."""
        try:
            sanitized = self.sanitizer.sanitize(packet)
            self.buffer.put(sanitized)
        except Exception as e:
            logger.error(f"Error processing packet: {e}")

def main() -> None:
    """Entry point for the GOATGuard agent."""
    try:
        config = load_config()
        setup_logging(config.logging.level, config.logging.file)

        
        agent = GoatGuardAgent(config)
        agent.run()

    except ConfigError as e:
        print(f"[CONFIG ERROR] {e}")
        sys.exit(1)

    except IdentityError as e:
        print(f"[IDENTITY ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
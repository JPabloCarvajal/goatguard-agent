# GOATGuard Agent

Infrastructure monitoring and security management system for LAN networks. The agent is installed on each network endpoint, captures traffic, collects system metrics, and sends everything to a centralized collector server for analysis.

Integrative Project III — UPB

## Simplified Agent Architecture
```
┌──────────────┐     UDP (JSON metrics)        ┌──────────────┐
│              │ ──────────────────────────►   │              │
│   Endpoint   │                               │  Collector   │
│   (Agent)    │  TCP (sanitized packets)      │  (Backend)   │
│              │ ──────────────────────────►   │              │
└──────────────┘                               └──────────────┘

The agent runs 4 tasks in parallel:
- Continuous network traffic capture (separate thread)
- System metrics collection every 5 seconds
- Heartbeat signal every 30 seconds
- Flush captured packets to collector every 1 second
```

## Requirements

- Python 3.10 or higher
- Npcap (Windows) — download from https://npcap.com
  - Check "Install Npcap in WinPcap API-compatible Mode" during installation
- libpcap-dev (Linux) — `sudo apt install libpcap-dev`

## Installation
```bash
git clone https://github.com/JPabloCarvajal/goatguard-agent.git
cd goatguard-agent
```

### Windows
```powershell
pip install pyyaml psutil scapy rich
```

### Linux (Ubuntu/Debian)
```bash
sudo apt install python3-full python3.12-venv libpcap-dev
python3 -m venv .venv
source .venv/bin/activate
pip install pyyaml psutil scapy rich
```

## Usage

Edit `config/agent_config.yaml` with the collector IP, then run:

### Windows
```powershell
python run.py
```

### Linux
```bash
source .venv/bin/activate
sudo PYTHONPATH=src .venv/bin/python3 run.py
```

> **Note:** On Linux, `sudo` is required because raw packet capture needs root privileges. The virtual environment path is specified explicitly so `sudo` can find the installed packages.

The agent identifies itself automatically, detects the primary network interface, and starts capturing traffic and sending metrics.

## Configuration

The file `config/agent_config.yaml` controls all agent behavior:
```yaml
collector:
  host: "192.168.1.100"     # Collector server IP
  tcp_port: 9999            # TCP port for captured traffic
  udp_port: 9998            # UDP port for metrics

intervals:
  metrics_seconds: 5        # CPU/RAM/disk reporting
  heartbeat_seconds: 30     # Keep-alive signal
  arp_scan_seconds: 60      # ARP scan

capture:
  interface: "auto"         # "auto" or exact name ("Ethernet", "eth0")

slicing:
  default_snap_len: 96      # Default bytes to keep (headers only)
  rules:
    - ports: [53]           # DNS
      snap_len: 300
    - ports: [80]           # HTTP
      snap_len: 300
    - ports: [443]          # HTTPS
      snap_len: 300

logging:
  level: "INFO"             # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "goatguard_agent.log"
```

## Project Structure
```
goatguard-agent/
├── config/
│   └── agent_config.yaml          # Agent configuration
├── src/goatguard_agent/
│   ├── config/                    # YAML loading and validation
│   │   ├── models.py              # Configuration dataclasses
│   │   ├── loader.py              # YAML reading and parsing
│   │   └── validator.py           # Value validation
│   ├── capture/                   # Network traffic capture
│   │   ├── packet_capture.py      # Continuous capture with scapy (thread)
│   │   ├── sanitizer.py           # Dynamic slicing by port
│   │   └── buffer.py              # Thread-safe buffer
│   ├── metrics/                   # System metrics
│   │   └── collector.py           # CPU, RAM, disk, link speed, uptime
│   ├── transport/                 # Collector communication
│   │   ├── udp_sender.py          # Metrics sending (JSON over UDP)
│   │   └── tcp_sender.py          # Packet sending (binary protocol over TCP)
│   ├── identity.py                # Unique identification (hostname + MAC)
│   └── main.py                    # Main orchestrator
├── tests/                         # Unit tests
├── .github/workflows/
│   ├── ci.yml                     # Lint + tests on every push
│   └── release.yml                # Executable build on every tag
├── run.py                         # Entry point
└── pyproject.toml                 # Project configuration
```

## Tests
```bash
pip install pytest ruff
$env:PYTHONPATH="src"              # PowerShell
# export PYTHONPATH=src            # Linux/Mac

python -m pytest tests/ -v
```

## CI/CD

The repository uses GitHub Actions with two workflows:

**CI** (`ci.yml`) — Runs on every push to `main` and `develop`. Executes linter (ruff) and tests (pytest) on Ubuntu and Windows simultaneously.

**Release** (`release.yml`) — Runs when a `v*` tag is created. Builds standalone executables with PyInstaller for Linux and Windows.

To create a release:
```bash
git tag v0.1.0
git push origin v0.1.0
```

## Communication Protocols

**Metrics (UDP):** Serialized as JSON. Include CPU, RAM, disk, link speed, uptime, and agent_id. Loss-tolerant.

**Captured traffic (TCP):** Binary protocol with length-prefix. Each packet carries a 20-byte header (orig_len, dst_port, timestamp, data_len) followed by the truncated bytes. The collector uses this data to reconstruct PCAP files.

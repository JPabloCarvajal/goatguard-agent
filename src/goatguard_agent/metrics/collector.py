
from dataclasses import dataclass, field
import time
import psutil

@dataclass
class SystemMetrics:
    """Snapshot of system metrics from the endpoint."""
    cpu_percent: float
    cpu_count: int
    ram_percent: float
    ram_total_bytes: int
    ram_available_bytes: int
    disk_usage_percent: float
    link_speed_mbps: int
    uptime_seconds: float
    timestamp: float = field(default_factory=time.time)
    
def collect_metrics(interface_name: str = "auto") -> SystemMetrics:
    """Read all system metrics and return them as a single snapshot."""
    return SystemMetrics(
        cpu_percent= psutil.cpu_percent(interval=0),
        cpu_count=psutil.cpu_count(logical=True),
        ram_percent=psutil.virtual_memory().percent,
        ram_total_bytes=psutil.virtual_memory().total,
        ram_available_bytes=psutil.virtual_memory().available,
        disk_usage_percent=psutil.disk_usage("/").percent,
        link_speed_mbps=_get_link_speed(interface_name),
        uptime_seconds=time.time() - psutil.boot_time(),
    )

def _get_link_speed(interface_name: str) -> int:
    """Get the link speed of the network interface in Mbps."""
    stats = psutil.net_if_stats()

    if interface_name != "auto":
        if interface_name in stats:
            return stats[interface_name].speed
        return 0

    for name, info in stats.items():
        if info.isup and info.speed > 0:
            return info.speed

    return 0

if __name__ == "__main__":
    metrics = collect_metrics()
    print(f"\nSystem Metrics:")
    print(f"  CPU: {metrics.cpu_percent}% ({metrics.cpu_count} cores)")
    print(f"  RAM: {metrics.ram_percent}% of {round(metrics.ram_total_bytes / (1024**3), 2)} GB")
    print(f"  RAM available: {round(metrics.ram_available_bytes / (1024**3), 2)} GB")
    print(f"  Disk: {metrics.disk_usage_percent}%")
    print(f"  Link speed: {metrics.link_speed_mbps} Mbps")
    print(f"  Uptime: {round(metrics.uptime_seconds / 3600, 1)} hours")
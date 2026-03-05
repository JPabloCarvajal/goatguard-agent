"""
Agent identity module for GOATGuard.

Generates a unique agent identifier from the hostname and
the MAC address of the primary network interface.

The ID format is: HOSTNAME__MAC (e.g. DESKTOP-01__CC:28:AA:09:16:04)
Double underscore separates components so the collector can
split them unambiguously (hostnames may contain single underscores).

Requirement: RF-009 (agent self-registration with unique ID)
OSI layers:  L2 (MAC from Data Link layer), L7 (hostname from OS)
"""

import logging
import socket
import psutil

class IdentityError(Exception):
    """Raised when agent identity cannot be determined."""
    pass

# "goatguard_agent.identity", mensaje en los logs de este módulo.
logger = logging.getLogger(__name__)

def get_hostname() -> str:

    """Get the hostname of the machine where the agent is running."""
    hostname = socket.gethostname()
    logger.debug(f"Hostname detected: {hostname}")
    return hostname

def _is_mac_address(addr) -> bool:
    """Check if a psutil address entry is a MAC address.

    Uses two detection methods for cross-platform compatibility:
    1. Check the address family against psutil.AF_LINK
    2. Fallback: verify the string format (XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)

    The fallback exists because AF_LINK values differ between
    Windows and Linux, and may not exist in all psutil versions.

    Args:
        addr: A single address entry from psutil.net_if_addrs().

    Returns:
        True if the address is a MAC address.
    """
        
    af_link = getattr(psutil, "AF_LINK", -1)
    if addr.family == af_link:
        return True

    address = addr.address
    if len(address) == 17 and (address.count(":") == 5 or address.count("-") == 5):
        return True

    return False

def _normalize_mac(mac: str) -> str:
    """Normalize a MAC address to uppercase colon-separated format.

    Example: "cc-28-aa-09-16-04" -> "CC:28:AA:09:16:04"
    """

    return mac.replace("-", ":").upper()

def _is_excluded_interface(name: str) -> bool:

    """Check if a network interface should be excluded from auto-detection.

    Excludes virtual interfaces (VMware, Docker, VirtualBox),
    Bluetooth adapters, and loopback interfaces.

    Args:
        name: Interface name as reported by the OS.

    Returns:
        True if the interface should be skipped.
    """
    excluded_keywords = [
        "loopback",
        "vmware",
        "virtualbox",
        "docker",
        "vethernet",
        "bluetooth",
        "adapter",
    ]

    name_lower = name.lower()
    for keyword in excluded_keywords:
        if keyword in name_lower:
            return True
    return False

def _is_valid_ipv4(address: str) -> bool:

    """Check if an IPv4 address belongs to a real connected network.

    Rejects loopback (127.x.x.x) and APIPA addresses (169.254.x.x).
    APIPA means the interface has no DHCP lease and is not connected
    to a functional network.

    Args:
        address: IPv4 address as a string.

    Returns:
        True if the address is usable for network identification.
    """

    if address.startswith("127."):
        return False

    if address.startswith("169.254."):
        return False

    return True


def get_primary_mac(interface_name: str = "auto") -> str:
    """Get the MAC address of the primary network interface.

    If interface_name is "auto", scans all interfaces and picks
    the first one that has a valid IPv4 and is not excluded.
    If a specific name is given, looks up that interface directly.

    The interface_name parameter comes from agent_config.yaml.

    Args:
        interface_name: Interface name or "auto" for auto-detection.

    Returns:
        MAC address in normalized format (e.g. "CC:28:AA:09:16:04").

    Raises:
        IdentityError: If no valid interface is found.
    """

    interfaces = psutil.net_if_addrs()

    if interface_name != "auto":
        return _get_mac_by_name(interfaces, interface_name)

    return _auto_detect_mac(interfaces)

def _get_mac_by_name(interfaces: dict, name: str) -> str:
    """Find the MAC address of a specific interface by its name.

    Args:
        interfaces: Dictionary from psutil.net_if_addrs().
        name: Exact interface name (e.g. "Ethernet", "Wi-Fi").

    Returns:
        Normalized MAC address.

    Raises:
        IdentityError: If the interface does not exist or has no MAC.
    """
    if name not in interfaces:
        available = list(interfaces.keys())
        raise IdentityError(
            f"Interface '{name}' not found. Available: {available}"
        )

    for addr in interfaces[name]:
        if _is_mac_address(addr):
            return _normalize_mac(addr.address)

    raise IdentityError(f"Interface '{name}' has no MAC address")

def _auto_detect_mac(interfaces: dict) -> str:
    """Automatically find the best network interface and return its MAC.

    Selection criteria:
    1. Interface name is not in the exclusion list
    2. Has at least one valid IPv4 address (not loopback, not APIPA)
    3. Has a MAC address

    The first interface matching all three conditions wins chicken dinner.

    Args:
        interfaces: Dictionary from psutil.net_if_addrs().

    Returns:
        Normalized MAC address of the selected interface.

    Raises:
        IdentityError: If no valid interface is found.
    """

    for iface_name, addrs in interfaces.items():
        if _is_excluded_interface(iface_name):
            continue

        has_valid_ip = False
        mac = None

        for addr in addrs:
            if addr.family == socket.AF_INET and _is_valid_ipv4(addr.address):
                has_valid_ip = True

            if _is_mac_address(addr):
                mac = _normalize_mac(addr.address)

        if has_valid_ip and mac:
            logger.info(f"Interface selected: {iface_name} -> {mac}")
            return mac

    raise IdentityError(
        "No valid network interface found. "
        "Check your connection or set the interface manually in agent_config.yaml"
    )

def generate_agent_id(interface_name: str = "auto") -> str:
    """Generate the unique agent identifier.

    Combines hostname and MAC address into a single string
    that the collector uses to identify this specific agent.

    Format: "HOSTNAME__MAC" (double underscore separator)
    Example: "MALEDUCADA__CC:28:AA:09:16:04"

    Args:
        interface_name: Interface name or "auto" for auto-detection.

    Returns:
        Unique agent identifier string.

    Raises:
        IdentityError: If hostname or MAC cannot be determined.
    """

    hostname = get_hostname()
    mac = get_primary_mac(interface_name)

    agent_id = f"{hostname}__{mac}"
    logger.info(f"Agent ID generated: {agent_id}")

    return agent_id

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    try:
        agent_id = generate_agent_id()
        print(f"\nAgent ID: {agent_id}")
    except IdentityError as e:
        print(f"ERROR: {e}")


"""
generate_agent_id("auto")          ← ÚNICA función que el mundo exterior llama
    │
    ├── get_hostname()              ← obtiene "MALEDUCADA"
    │
    └── get_primary_mac("auto")     ← decide qué camino tomar
            │
            ├── Si "auto" → _auto_detect_mac(interfaces)
            │                   │
            │                   ├── _is_excluded_interface(name)   ¿descarto esta interfaz?
            │                   ├── _is_valid_ipv4(address)        ¿tiene IP real?
            │                   ├── _is_mac_address(addr)          ¿esto es una MAC?
            │                   └── _normalize_mac(mac)            convertir a formato estándar
            │
            └── Si "Ethernet" → _get_mac_by_name(interfaces, name)
                                    │
                                    ├── _is_mac_address(addr)
                                    └── _normalize_mac(mac)
"""
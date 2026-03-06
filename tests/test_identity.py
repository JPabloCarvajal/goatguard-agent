"""Tests for the identity module."""

from goatguard_agent.identity import (
    get_hostname,
    generate_agent_id,
    _is_mac_address,
    _normalize_mac,
    _is_excluded_interface,
    _is_valid_ipv4,
)

# --- MAC normalization ---

def test_normalize_mac_with_dashes():
    """Windows-style MAC (dashes) should become colon-separated uppercase."""
    assert _normalize_mac("cc-28-aa-09-16-04") == "CC:28:AA:09:16:04"


def test_normalize_mac_already_normalized():
    """Already normalized MAC should stay the same."""
    assert _normalize_mac("CC:28:AA:09:16:04") == "CC:28:AA:09:16:04"


# --- Interface exclusion ---

def test_exclude_loopback():
    assert _is_excluded_interface("Loopback Pseudo-Interface 1") == True


def test_exclude_vmware():
    assert _is_excluded_interface("VMware Network Adapter VMnet1") == True


def test_exclude_bluetooth():
    assert _is_excluded_interface("Bluetooth Network Connection") == True


def test_exclude_docker():
    assert _is_excluded_interface("docker0") == True


def test_keep_ethernet():
    assert _is_excluded_interface("Ethernet") == False


def test_keep_wifi():
    assert _is_excluded_interface("Wi-Fi") == False


# --- IPv4 validation ---

def test_reject_loopback_ip():
    assert _is_valid_ipv4("127.0.0.1") == False


def test_reject_apipa():
    assert _is_valid_ipv4("169.254.38.229") == False


def test_accept_private_ip():
    assert _is_valid_ipv4("192.168.1.4") == True


def test_accept_other_private():
    assert _is_valid_ipv4("10.0.0.50") == True


# --- Hostname ---

def test_hostname_returns_string():
    """Hostname should always be a non-empty string."""
    hostname = get_hostname()
    assert isinstance(hostname, str)
    assert len(hostname) > 0


# --- Full agent ID ---

def test_agent_id_format():
    """Agent ID should contain double underscore separator."""
    agent_id = generate_agent_id()
    assert "__" in agent_id
    parts = agent_id.split("__")
    assert len(parts) == 2
    assert len(parts[0]) > 0  # hostname
    assert len(parts[1]) > 0  # MAC
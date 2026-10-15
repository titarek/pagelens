import ipaddress
import os
import socket
from typing import Tuple, List, Optional
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_SINGLE_PORTS = {80, 443}
ALLOWED_PORT_RANGE = range(8080, 8091)  # 8080 - 8090 inclusive
MAX_URL_LENGTH = 2048

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
}


class SSRFValidationError(ValueError):
    """Raised when a URL violates SSRF safety constraints."""
    pass


def is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if an IP is private, reserved, loopback, or in blocked networks."""
    # Check for IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        return True

    for net in BLOCKED_IP_NETWORKS:
        try:
            if ip in net:
                return True
        except TypeError:
            continue

    return False


def validate_and_resolve_url(raw_url: str, allow_local_for_testing: bool = False) -> Tuple[str, str]:
    """
    Validates a URL against SSRF, port, scheme, and DNS rebinding constraints.
    Returns a tuple of (canonical_url, resolved_ip).
    Raises SSRFValidationError on failure.
    """
    if not raw_url or not isinstance(raw_url, str):
        raise SSRFValidationError("URL must be a non-empty string.")

    cleaned_url = raw_url.strip()

    if len(cleaned_url) > MAX_URL_LENGTH:
        raise SSRFValidationError(f"URL length ({len(cleaned_url)}) exceeds maximum limit of {MAX_URL_LENGTH} characters.")

    try:
        parsed = urlparse(cleaned_url)
    except Exception as e:
        raise SSRFValidationError(f"Invalid URL structure: {e}")

    # Step 1: Validate scheme
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise SSRFValidationError(f"Invalid URL scheme '{scheme}'. Only http and https are allowed.")

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise SSRFValidationError("URL must include a valid hostname.")

    # Check hostname literal blocklist
    if not allow_local_for_testing:
        if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".local"):
            raise SSRFValidationError(f"Access to hostname '{hostname}' is blocked (SSRF protection).")

    # Step 2: Validate port
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80

    if port not in ALLOWED_SINGLE_PORTS and port not in ALLOWED_PORT_RANGE:
        raise SSRFValidationError(
            f"Port {port} is not permitted. Only ports 80, 443, and 8080-8090 are allowed."
        )

    # Allow local bypass during integration testing if explicitly enabled via flag or env
    bypass_local = allow_local_for_testing or (os.getenv("PAGELENS_ALLOW_LOCAL_TESTING", "false").lower() == "true")

    # Step 3: Check if hostname is an IP literal
    try:
        # Strip brackets from IPv6 literal if present
        ip_str = hostname.strip("[]")
        ip_obj = ipaddress.ip_address(ip_str)
        if not bypass_local and is_ip_blocked(ip_obj):
            raise SSRFValidationError(f"Access to IP address '{ip_str}' is blocked (SSRF protection).")
        return cleaned_url, str(ip_obj)
    except ValueError:
        # Not a raw IP literal, proceed to DNS resolution
        pass

    # Step 4: DNS Resolution & DNS Rebinding Check
    try:
        # Resolve all addresses (A and AAAA)
        addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFValidationError(f"Could not resolve host '{hostname}': {e}")
    except Exception as e:
        raise SSRFValidationError(f"DNS lookup error for host '{hostname}': {e}")

    if not addr_info:
        raise SSRFValidationError(f"No IP addresses resolved for host '{hostname}'.")

    resolved_ips: List[str] = []
    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        resolved_ips.append(ip_str)
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if not bypass_local and is_ip_blocked(ip_obj):
                raise SSRFValidationError(
                    f"Host '{hostname}' resolved to blocked private/local IP '{ip_str}' (SSRF/DNS Rebinding protection)."
                )
        except ValueError:
            raise SSRFValidationError(f"Invalid resolved IP '{ip_str}'.")

    primary_ip = resolved_ips[0] if resolved_ips else "unknown"
    return cleaned_url, primary_ip

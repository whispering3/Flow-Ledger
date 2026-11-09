import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse


class SSRFBlocked(ValueError):
    """Raised when a destination can reach a non-public network."""


@dataclass(frozen=True)
class ValidatedDestination:
    url: str
    hostname: str
    resolved_ips: tuple[str, ...]


def validate_public_http_destination(url: str) -> ValidatedDestination:
    """Resolve and reject non-public destination addresses before every call.

    Redirects are disabled by the caller. Production infrastructure must also
    restrict egress; an application-only DNS check cannot be the sole
    anti-rebinding control.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SSRFBlocked("Destination must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise SSRFBlocked("Destination URL must not include credentials")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in {80, 443}:
        raise SSRFBlocked("Destination port is not allowed")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SSRFBlocked("Destination hostname could not be resolved") from exc

    resolved_ips = tuple(sorted({address[4][0] for address in addresses}))
    if not resolved_ips:
        raise SSRFBlocked("Destination hostname resolved to no addresses")
    for raw_ip in resolved_ips:
        if not ipaddress.ip_address(raw_ip).is_global:
            raise SSRFBlocked("Destination resolves to a non-public address")
    return ValidatedDestination(url=url, hostname=parsed.hostname, resolved_ips=resolved_ips)

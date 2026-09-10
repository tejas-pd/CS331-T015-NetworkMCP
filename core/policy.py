from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from pathlib import Path

import yaml


class PolicyViolation(ValueError):
    """Raised when a requested network action is outside the lab policy."""


@dataclass(frozen=True)
class NetworkPolicy:
    allowed_networks: tuple[ipaddress.IPv4Network, ...]
    protected_ips: frozenset[ipaddress.IPv4Address]
    allowed_interfaces: frozenset[str]
    min_bandwidth_mbps: int
    max_bandwidth_mbps: int

    @classmethod
    def load(cls, path: Path) -> "NetworkPolicy":
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            allowed_networks=tuple(ipaddress.ip_network(value) for value in data["allowed_networks"]),
            protected_ips=frozenset(ipaddress.ip_address(value) for value in data["protected_ips"]),
            allowed_interfaces=frozenset(data["allowed_interfaces"]),
            min_bandwidth_mbps=int(data["min_bandwidth_mbps"]),
            max_bandwidth_mbps=int(data["max_bandwidth_mbps"]),
        )

    def validate_ip(self, value: str) -> str:
        try:
            address = ipaddress.ip_address(value)
        except ValueError as exc:
            raise PolicyViolation("Target must be a valid IPv4 address.") from exc
        if not isinstance(address, ipaddress.IPv4Address):
            raise PolicyViolation("Only IPv4 targets are supported.")
        if address in self.protected_ips:
            raise PolicyViolation(f"{address} is protected by policy.")
        if not any(address in network for network in self.allowed_networks):
            raise PolicyViolation(f"{address} is outside the allowed lab networks.")
        return str(address)

    def validate_limit(self, mbps: int) -> int:
        if not self.min_bandwidth_mbps <= mbps <= self.max_bandwidth_mbps:
            raise PolicyViolation(f"Bandwidth must be {self.min_bandwidth_mbps}-{self.max_bandwidth_mbps} Mbps.")
        return mbps

    def validate_interface(self, interface: str) -> str:
        if interface not in self.allowed_interfaces:
            raise PolicyViolation(f"Interface {interface!r} is not allowed by policy.")
        return interface

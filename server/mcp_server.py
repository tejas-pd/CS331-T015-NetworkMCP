from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastmcp import FastMCP
from core.network_tools import NetworkTools
from core.policy import NetworkPolicy, PolicyViolation
from core.runner import CommandRunner


mcp = FastMCP("Network Administration Assistant")

tools = NetworkTools(
    NetworkPolicy.load(ROOT / "policies" / "network_policy.yaml"),
    CommandRunner(ROOT / "logs" / "audit.jsonl")
)


@mcp.tool()
def block_ip(ip: str) -> dict:
    """Block inbound traffic from an authorized lab IPv4 address."""
    try:
        return tools.block_ip(ip)
    except PolicyViolation as error:
        return {
            "status": "rejected",
            "ip": ip,
            "reason": str(error)
        }


@mcp.tool()
def unblock_ip(ip: str) -> dict:
    """Remove this assistant's inbound DROP rule for an authorized lab IPv4 address."""
    try:
        return tools.unblock_ip(ip)
    except PolicyViolation as error:
        return {
            "status": "rejected",
            "ip": ip,
            "reason": str(error)
        }


@mcp.tool()
def list_firewall_rules() -> dict:
    """List current INPUT-chain iptables rules."""
    return tools.list_firewall_rules()

@mcp.tool()
def ping_host(ip: str) -> dict:
    """Check connectivity to an authorized lab IPv4 address."""
    try:
        return tools.ping_host(ip)
    except PolicyViolation as error:
        return {
            "status": "rejected",
            "ip": ip,
            "reason": str(error)
        }

@mcp.tool()
def limit_bandwidth(
    ip: str,
    mbps: int,
    interface: str = "eth0"
) -> dict:
    """Apply an authorized outbound bandwidth cap to a lab IPv4 address."""
    try:
        return tools.limit_bandwidth(ip, mbps, interface)
    except PolicyViolation as error:
        return {
            "status": "rejected",
            "ip": ip,
            "reason": str(error)
        }

@mcp.tool()
def test_bandwidth(ip: str) -> dict:
    """Run an iperf3 bandwidth test against an authorized lab IPv4 address."""
    return tools.test_bandwidth(ip)

if __name__ == "__main__":
    mcp.run()

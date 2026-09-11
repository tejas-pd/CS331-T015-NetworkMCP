from __future__ import annotations

import subprocess

from .policy import NetworkPolicy
from .runner import CommandRunner


class NetworkTools:
    def __init__(self, policy: NetworkPolicy, runner: CommandRunner) -> None:
        self.policy, self.runner = policy, runner

    def block_ip(self, ip: str) -> dict:
        ip = self.policy.validate_ip(ip)

        existing = self.runner.run(
            ["sudo", "-n", "iptables", "-C", "INPUT", "-s", ip, "-j", "DROP"]
        )

        if existing["ok"] and not existing.get("dry_run"):
            return {
                "status": "already_blocked",
                "ip": ip,
                "verified": True
            }

        applied = self.runner.run(
            ["sudo", "-n", "iptables", "-I", "INPUT", "-s", ip, "-j", "DROP"]
        )

        verified = self.runner.run(
            ["sudo", "-n", "iptables", "-C", "INPUT", "-s", ip, "-j", "DROP"]
        )

        return {
            "status": "blocked" if applied["ok"] else "failed",
            "ip": ip,
            "applied": applied,
            "verified": verified["ok"]
        }

    def unblock_ip(self, ip: str) -> dict:
        ip = self.policy.validate_ip(ip)

        applied = self.runner.run(
            ["sudo", "-n", "iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"]
        )

        verified = self.runner.run(
            ["sudo", "-n", "iptables", "-C", "INPUT", "-s", ip, "-j", "DROP"]
        )

        return {
            "status": "unblocked" if applied["ok"] else "not_found_or_failed",
            "ip": ip,
            "applied": applied,
            "verified_absent": not verified["ok"]
        }

    def list_firewall_rules(self) -> dict:
        return self.runner.run(
            ["sudo", "-n", "iptables", "-S", "INPUT"]
        )

    def limit_bandwidth(self, ip: str, mbps: int, interface: str) -> dict:
        ip = self.policy.validate_ip(ip)
        mbps = self.policy.validate_limit(int(mbps))
        interface = self.policy.validate_interface(interface)

        commands = [
            [
                "sudo", "-n", "tc", "qdisc", "replace",
                "dev", interface,
                "root", "handle", "1:", "htb",
                "default", "30"
            ],
            [
                "sudo", "-n", "tc", "class", "replace",
                "dev", interface,
                "parent", "1:",
                "classid", "1:10",
                "htb",
                "rate", f"{mbps}mbit",
                "ceil", f"{mbps}mbit"
            ],
            [
                "sudo", "-n", "tc", "filter", "replace",
                "dev", interface,
                "protocol", "ip",
                "parent", "1:",
                "prio", "1",
                "u32",
                "match", "ip", "src", f"{ip}/32",
                "flowid", "1:10"
            ]
        ]

        results = [
            self.runner.run(command)
            for command in commands
        ]

        inspection = self.runner.run(
            ["sudo", "-n", "tc", "class", "show", "dev", interface]
        )

        return {
            "status": "limited"
            if all(result["ok"] for result in results)
            else "failed",
            "ip": ip,
            "mbps": mbps,
            "interface": interface,
            "applied": results,
            "verified": inspection["ok"],
            "inspection": inspection
        }

    def test_bandwidth(self, ip: str) -> dict:
        ip = self.policy.validate_ip(ip)

        result = self.runner.observe([
            "iperf3",
            "-c",
            ip,
            "-J"
        ])

        if not result["ok"]:
            return {
                "status": "failed",
                "ip": ip,
                "result": result,
            }

        try:
            import json

            data = json.loads(result["stdout"])
            end = data["end"]

            sender = end["sum_sent"]
            receiver = end["sum_received"]

            return {
                "status": "completed",
                "ip": ip,
                "sender_bps": sender["bits_per_second"],
                "receiver_bps": receiver["bits_per_second"],
                "retransmissions": sender.get("retransmits", 0),
            }

        except (KeyError, ValueError, TypeError) as exc:
            return {
                "status": "completed",
                "ip": ip,
                "result": result,
                "parse_error": str(exc),
            }

    def ping_host(self, ip: str) -> dict:
        ip = self.policy.validate_ip(ip)

        command = [
            "ping",
            "-c",
            "3",
            "-W",
            "2",
            ip
        ]

        result = self.runner.run_monitor(command)

        return {
            "status": "reachable" if result["ok"] else "unreachable",
            "ip": ip,
            "result": result
        }

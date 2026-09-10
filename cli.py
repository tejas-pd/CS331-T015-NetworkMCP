from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.network_tools import NetworkTools
from core.policy import NetworkPolicy
from core.runner import CommandRunner

root = Path(__file__).parent
tools = NetworkTools(NetworkPolicy.load(root / "policies" / "network_policy.yaml"), CommandRunner(root / "logs" / "audit.jsonl"))
parser = argparse.ArgumentParser(description="Network MCP Assistant local CLI")
sub = parser.add_subparsers(dest="action", required=True)
for action in ("block", "unblock"):
    cmd = sub.add_parser(action); cmd.add_argument("ip")
sub.add_parser("list-rules")
cmd = sub.add_parser("limit"); cmd.add_argument("ip"); cmd.add_argument("mbps", type=int); cmd.add_argument("--interface", default="eth0")
args = parser.parse_args()
if args.action == "block": result = tools.block_ip(args.ip)
elif args.action == "unblock": result = tools.unblock_ip(args.ip)
elif args.action == "limit": result = tools.limit_bandwidth(args.ip, args.mbps, args.interface)
else: result = tools.list_firewall_rules()
print(json.dumps(result, indent=2))

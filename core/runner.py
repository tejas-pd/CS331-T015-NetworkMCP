from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence


class CommandRunner:
    """Runs fixed argument vectors, never shell-interpolated user input."""

    def __init__(self, audit_path: Path, execute: bool | None = None) -> None:
        self.audit_path = audit_path
        self.execute = execute if execute is not None else os.getenv("NETWORK_ASSISTANT_EXECUTE") == "1"

    def run(self, args: Sequence[str]) -> dict:
        command = list(args)
        if self.execute and platform.system() != "Linux":
            raise RuntimeError("Live network changes are supported only on Linux/Ubuntu.")
        if self.execute:
            result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=20)
            response = {"ok": result.returncode == 0, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "command": command}
        else:
            response = {"ok": True, "dry_run": True, "command": command}
        self._audit(response)
        return response

    def observe(self, args: Sequence[str]) -> dict:
        command = list(args)

        if platform.system() != "Linux":
            raise RuntimeError("Network monitoring is supported only on Linux/Ubuntu.")

        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        response = {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "command": command,
        }

        self._audit(response)
        return response

    def _audit(self, result: dict) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {"timestamp": datetime.now(UTC).isoformat(), **result}
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
    
    def run_monitor(self, args: Sequence[str]) -> dict:
        command = list(args)

        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=20
        )

        response = {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "command": command
        }

        self._audit(response)
        return response

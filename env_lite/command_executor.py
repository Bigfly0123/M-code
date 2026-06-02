from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    command: str
    returncode: int
    output: str
    timed_out: bool = False


class CommandExecutor:
    def __init__(self, cwd: Path, timeout: int = 30):
        self.cwd = cwd
        self.timeout = timeout

    def run(self, command: str, timeout: int | None = None) -> CommandResult:
        try:
            result = subprocess.run(
                command,
                cwd=self.cwd,
                shell=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout or self.timeout,
            )
            return CommandResult(command=command, returncode=result.returncode, output=result.stdout)
        except subprocess.TimeoutExpired as exc:
            output = exc.output or ""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            return CommandResult(command=command, returncode=-1, output=output, timed_out=True)

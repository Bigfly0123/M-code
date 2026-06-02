from __future__ import annotations

import difflib
from pathlib import Path

from evocode_orchard_lite.env_lite.command_executor import CommandExecutor
from evocode_orchard_lite.schema import Task, ToolResult
from evocode_orchard_lite.tools.path_utils import resolve_workspace_path


def list_files(task: Task, arguments: dict) -> ToolResult:
    root = resolve_workspace_path(task.workspace, arguments.get("path", "."))
    files = [str(path.relative_to(task.workspace)) for path in sorted(root.rglob("*")) if path.is_file()]
    return ToolResult(True, "\n".join(files), {"files": files})


def read_file(task: Task, arguments: dict) -> ToolResult:
    if "path" not in arguments:
        return ToolResult(False, "Missing required argument: 'path'", {"failure_type": "FORMAT_ERROR"})
    path = resolve_workspace_path(task.workspace, arguments["path"])
    return ToolResult(True, path.read_text(encoding="utf-8"), {"path": str(path.relative_to(task.workspace))})


def search_code(task: Task, arguments: dict) -> ToolResult:
    if "keyword" not in arguments:
        return ToolResult(False, "Missing required argument: 'keyword'", {"failure_type": "FORMAT_ERROR"})
    keyword = arguments["keyword"]
    matches: list[str] = []
    for path in sorted(task.workspace.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if keyword in line:
                matches.append(f"{path.relative_to(task.workspace)}:{line_no}: {line}")
    return ToolResult(True, "\n".join(matches) or "No matches.", {"matches": matches})


def run_tests(task: Task, arguments: dict) -> ToolResult:
    cmd = arguments.get("cmd") or task.metadata["test_command"]
    result = CommandExecutor(task.workspace, timeout=int(task.metadata.get("timeout", 30))).run(cmd)
    return ToolResult(
        result.returncode == 0,
        result.output,
        {"returncode": result.returncode, "command": cmd, "timed_out": result.timed_out},
    )


def git_diff(task: Task, arguments: dict) -> ToolResult:
    diff = _workspace_diff(task)
    return ToolResult(True, diff or "No diff available.", {"diff": diff})


def submit_patch(task: Task, arguments: dict) -> ToolResult:
    return ToolResult(True, "Patch submitted.", {"submitted": True})


def _workspace_diff(task: Task) -> str:
    original_root = task.task_dir / "repo"
    chunks: list[str] = []
    rel_paths = sorted(
        {path.relative_to(original_root) for path in original_root.rglob("*.py")}
        | {path.relative_to(task.workspace) for path in task.workspace.rglob("*.py")}
    )
    for rel in rel_paths:
        original = original_root / rel
        current = task.workspace / rel
        old_lines = original.read_text(encoding="utf-8").splitlines(keepends=True) if original.exists() else []
        new_lines = current.read_text(encoding="utf-8").splitlines(keepends=True) if current.exists() else []
        if old_lines == new_lines:
            continue
        chunks.extend(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{rel.as_posix()}",
                tofile=f"b/{rel.as_posix()}",
            )
        )
    return "".join(chunks)

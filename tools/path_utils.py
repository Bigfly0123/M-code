from __future__ import annotations

from pathlib import Path


def resolve_workspace_path(workspace: Path, relative_path: str) -> Path:
    candidate = (workspace / relative_path).resolve()
    root = workspace.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Path escapes workspace: {relative_path}")
    return candidate

from __future__ import annotations

from evocode_orchard_lite.schema import Task, ToolResult
from evocode_orchard_lite.tools.path_utils import resolve_workspace_path


def edit_file(task: Task, arguments: dict) -> ToolResult:
    for key in ("path", "old", "new"):
        if key not in arguments:
            return ToolResult(False, f"Missing required argument: '{key}'", {"failure_type": "FORMAT_ERROR"})
    path = resolve_workspace_path(task.workspace, arguments["path"])
    old = arguments["old"]
    new = arguments["new"]
    text = path.read_text(encoding="utf-8")
    if old not in text:
        return ToolResult(False, f"Old text not found in {arguments['path']}", {"failure_type": "PATCH_APPLY_ERROR"})
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return ToolResult(True, f"Edited {arguments['path']}", {"path": arguments["path"]})

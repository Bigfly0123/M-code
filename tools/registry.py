from __future__ import annotations

from collections.abc import Callable

from evocode_orchard_lite.schema import Action, Task, ToolResult
from evocode_orchard_lite.tools.basic_tools import git_diff, list_files, read_file, run_tests, search_code, submit_patch
from evocode_orchard_lite.tools.edit_file import edit_file

ToolFn = Callable[[Task, dict], ToolResult]


class ToolRegistry:
    def __init__(self, tools: dict[str, ToolFn]):
        self.tools = tools

    def execute(self, task: Task, action: Action) -> ToolResult:
        tool = self.tools.get(action.name)
        if tool is None:
            return ToolResult(False, f"Unknown tool: {action.name}", {"failure_type": "FORMAT_ERROR"})
        return tool(task, action.arguments)


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        {
            "list_files": list_files,
            "read_file": read_file,
            "search_code": search_code,
            "edit_file": edit_file,
            "run_tests": run_tests,
            "git_diff": git_diff,
            "submit_patch": submit_patch,
        }
    )

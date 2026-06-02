from __future__ import annotations

import json
import shutil
from pathlib import Path

from evocode_orchard_lite.env_lite.command_executor import CommandExecutor
from evocode_orchard_lite.schema import Task


class CodeRepairEnv:
    def __init__(self, tasks_root: Path, workspaces_root: Path):
        self.tasks_root = tasks_root
        self.workspaces_root = workspaces_root

    def load_task(self, task_id: str) -> Task:
        task_dir = self.tasks_root / task_id
        metadata = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8"))
        issue = (task_dir / "issue.md").read_text(encoding="utf-8")
        workspace = self.reset(task_id)
        return Task(task_id=task_id, task_dir=task_dir, workspace=workspace, issue=issue, metadata=metadata)

    def reset(self, task_id: str) -> Path:
        task_dir = self.tasks_root / task_id
        workspace = self.workspaces_root / task_id
        if workspace.exists():
            shutil.rmtree(workspace)
        shutil.copytree(task_dir / "repo", workspace)
        return workspace

    def executor_for(self, task: Task) -> CommandExecutor:
        return CommandExecutor(task.workspace, timeout=int(task.metadata.get("timeout", 30)))

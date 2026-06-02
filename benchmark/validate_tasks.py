from __future__ import annotations

import argparse
import json
from pathlib import Path

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.schema import Task
from evocode_orchard_lite.tools.edit_file import edit_file
from evocode_orchard_lite.tools.basic_tools import run_tests


def validate_task(task: Task) -> dict:
    initial = run_tests(task, {})
    fix = task.metadata.get("scripted_fix")
    if not fix:
        return {
            "task_id": task.task_id,
            "valid": False,
            "initial_failed": initial.data.get("returncode") != 0,
            "fixed_passed": False,
            "error": "missing scripted_fix",
        }

    edit_result = edit_file(task, fix)
    fixed = run_tests(task, {})
    initial_failed = initial.data.get("returncode") != 0
    fixed_passed = fixed.data.get("returncode") == 0
    return {
        "task_id": task.task_id,
        "valid": initial_failed and edit_result.success and fixed_passed,
        "initial_failed": initial_failed,
        "edit_success": edit_result.success,
        "fixed_passed": fixed_passed,
        "bug_type": task.metadata.get("bug_type", ""),
        "test_command": task.metadata.get("test_command", ""),
    }


def validate_all(root: Path, task_ids: list[str] | None = None) -> list[dict]:
    tasks_root = root / "benchmark" / "tasks"
    selected = task_ids or sorted(path.name for path in tasks_root.iterdir() if path.is_dir())
    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "validation_workspaces")
    return [validate_task(env.load_task(task_id)) for task_id in selected]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Validate toy code repair tasks.")
    parser.add_argument("--task", action="append", dest="tasks", help="Task id to validate. Can be repeated.")
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "outputs" / "reports" / "task_validation.json",
        help="Path for validation report JSON.",
    )
    args = parser.parse_args()
    results = validate_all(root, args.tasks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"total": len(results), "valid": sum(item["valid"] for item in results)}, indent=2))
    return 0 if all(item["valid"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

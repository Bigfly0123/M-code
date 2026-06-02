from __future__ import annotations

from evocode_orchard_lite.env_lite.command_executor import CommandExecutor
from evocode_orchard_lite.schema import Task, Trace


def _edited_files_from_patch(patch: str) -> set[str]:
    files: set[str] = set()
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            files.add(line.removeprefix("+++ b/"))
    return files


def _ran_tests_before_submit(trace: Trace) -> bool:
    for step in trace.steps:
        action_name = step.action.get("name")
        if action_name == "submit_patch":
            return False
        if action_name == "run_tests":
            return True
    return False


def evaluate_trace(task: Task, trace: Trace) -> Trace:
    test_command = task.metadata["test_command"]
    result = CommandExecutor(task.workspace, timeout=int(task.metadata.get("timeout", 30))).run(test_command)
    tests_passed = result.returncode == 0
    format_errors = trace.metrics.get("format_errors", 0)

    trace.success = tests_passed
    trace.reward = 1.0 if tests_passed else (-0.3 if format_errors else 0.0)
    if tests_passed:
        trace.failure_type = None
    trace.test_result = {
        "command": test_command,
        "returncode": result.returncode,
        "output": result.output,
        "passed": tests_passed,
    }
    trace.metrics |= {
        "num_steps": len(trace.steps),
        "format_errors": format_errors,
        "tool_valid": format_errors == 0,
        "tests_passed": tests_passed,
        "patch_apply": bool(trace.final_patch.strip()),
        "ran_tests_before_submit": _ran_tests_before_submit(trace),
        "edited_files": sorted(_edited_files_from_patch(trace.final_patch)),
        "unrelated_edit": bool(_edited_files_from_patch(trace.final_patch) - set(task.metadata.get("target_files", []))),
    }
    if not tests_passed and trace.failure_type is None:
        trace.failure_type = "TEST_STILL_FAIL"
    return trace

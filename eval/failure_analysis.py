from __future__ import annotations

from collections import Counter
from pathlib import Path

from evocode_orchard_lite.schema import Trace


def classify_failure(trace: Trace, task_metadata: dict | None = None) -> str:
    """Assign a single failure type to a failed trace.

    Checks are ordered from most specific to least specific so the most
    informative label wins.
    """
    target_files = set((task_metadata or {}).get("target_files", []))
    steps = trace.steps

    format_errors = trace.metrics.get("format_errors", 0)
    if format_errors > len(steps) * 0.5 and format_errors >= 2:
        return "FORMAT_ERROR"

    if _has_loop(steps):
        return "LOOP"

    if _is_give_up(steps):
        return "GIVE_UP"

    if _has_hallucinated_file(steps):
        return "HALLUCINATED_FILE"

    if _no_test_before_submit(steps):
        return "NO_TEST_BEFORE_SUBMIT"

    if _has_wrong_file_edit(steps, target_files):
        return "WRONG_FILE_EDIT"

    if trace.failure_type == "PATCH_APPLY_ERROR":
        return "PATCH_APPLY_ERROR"

    if trace.failure_type == "TIMEOUT":
        return "TIMEOUT"

    if not trace.test_result.get("passed"):
        return "TEST_STILL_FAIL"

    return "UNKNOWN"


def _has_loop(steps: list) -> bool:
    if len(steps) < 4:
        return False
    action_pairs = [(s.action.get("name"), str(s.action.get("arguments", {}))) for s in steps]
    for window_size in range(2, len(action_pairs) // 2 + 1):
        for i in range(len(action_pairs) - 2 * window_size + 1):
            if action_pairs[i : i + window_size] == action_pairs[i + window_size : i + 2 * window_size]:
                return True
    return False


def _is_give_up(steps: list) -> bool:
    if not steps:
        return False
    last = steps[-1]
    action_name = last.action.get("name", "")
    thought = last.thought.lower()
    if action_name == "submit_patch" and "give up" in thought:
        return True
    if action_name == "submit_patch" and not last.tool_success:
        return True
    return False


def _has_hallucinated_file(steps: list) -> bool:
    for step in steps:
        if step.action.get("name") in ("read_file", "edit_file") and not step.tool_success:
            obs = step.observation.lower()
            if "not found" in obs or "no such file" in obs or "path escapes" in obs:
                return True
    return False


def _no_test_before_submit(steps: list) -> bool:
    for step in steps:
        action_name = step.action.get("name")
        if action_name == "submit_patch":
            return True
        if action_name == "run_tests":
            return False
    return False


def _has_wrong_file_edit(steps: list, target_files: set[str]) -> bool:
    if not target_files:
        return False
    for step in steps:
        action_name = step.action.get("name")
        if action_name == "edit_file":
            edited_path = step.action.get("arguments", {}).get("path", "")
            if edited_path and edited_path not in target_files:
                return True
    return False


def analyze_failures(
    traces: list[Trace],
    task_metadata_map: dict[str, dict] | None = None,
) -> dict:
    """Analyze all failed traces and return a failure taxonomy.

    Returns
    -------
    dict
        ``{"taxonomy": {failure_type: count}, "details": [{task_id, failure_type, ...}], "total_failed": int}``
    """
    taxonomy: Counter[str] = Counter()
    details: list[dict] = []

    for trace in traces:
        if trace.success:
            continue
        metadata = (task_metadata_map or {}).get(trace.task_id, {})
        failure_type = classify_failure(trace, metadata)
        taxonomy[failure_type] += 1
        details.append(
            {
                "task_id": trace.task_id,
                "failure_type": failure_type,
                "num_steps": len(trace.steps),
                "format_errors": trace.metrics.get("format_errors", 0),
                "reward": trace.reward,
            }
        )

    return {
        "taxonomy": dict(taxonomy),
        "total_failed": len(details),
        "details": details,
    }


def write_failure_taxonomy(path: Path, analysis: dict) -> None:
    """Persist the failure taxonomy as a JSON file."""
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

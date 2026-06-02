from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from evocode_orchard_lite.schema import Trace


@dataclass
class EvalSummary:
    total_tasks: int
    task_success_rate: float
    test_pass_rate: float
    tool_valid_rate: float
    patch_apply_rate: float
    format_error_rate: float
    run_test_before_submit_rate: float
    unrelated_edit_rate: float
    avg_steps: float
    failure_counts: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "total_tasks": self.total_tasks,
            "task_success_rate": self.task_success_rate,
            "test_pass_rate": self.test_pass_rate,
            "tool_valid_rate": self.tool_valid_rate,
            "patch_apply_rate": self.patch_apply_rate,
            "format_error_rate": self.format_error_rate,
            "run_test_before_submit_rate": self.run_test_before_submit_rate,
            "unrelated_edit_rate": self.unrelated_edit_rate,
            "avg_steps": self.avg_steps,
            "failure_counts": self.failure_counts,
        }


def summarize_traces(traces: list[Trace]) -> EvalSummary:
    total = len(traces)
    if total == 0:
        return EvalSummary(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, {})

    successes = sum(1 for trace in traces if trace.success)
    tests_passed = sum(1 for trace in traces if trace.test_result.get("passed"))
    tool_valid = sum(1 for trace in traces if trace.metrics.get("tool_valid"))
    patch_apply = sum(1 for trace in traces if trace.metrics.get("patch_apply"))
    run_tests_first = sum(1 for trace in traces if trace.metrics.get("ran_tests_before_submit"))
    unrelated_edits = sum(1 for trace in traces if trace.metrics.get("unrelated_edit"))
    format_errors = sum(trace.metrics.get("format_errors", 0) for trace in traces)
    steps = sum(len(trace.steps) for trace in traces)
    failures = Counter(trace.failure_type or "NONE" for trace in traces if not trace.success)

    return EvalSummary(
        total_tasks=total,
        task_success_rate=successes / total,
        test_pass_rate=tests_passed / total,
        tool_valid_rate=tool_valid / total,
        patch_apply_rate=patch_apply / total,
        format_error_rate=format_errors / max(steps, 1),
        run_test_before_submit_rate=run_tests_first / total,
        unrelated_edit_rate=unrelated_edits / total,
        avg_steps=steps / total,
        failure_counts=dict(failures),
    )

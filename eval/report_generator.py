from __future__ import annotations

from pathlib import Path

from evocode_orchard_lite.eval.metrics import EvalSummary
from evocode_orchard_lite.schema import Trace


def write_baseline_report(path: Path, traces: list[Trace], summary: EvalSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Baseline Evaluation Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total Tasks | {summary.total_tasks} |",
        f"| Task Success Rate | {summary.task_success_rate:.2%} |",
        f"| Test Pass Rate | {summary.test_pass_rate:.2%} |",
        f"| Tool Valid Rate | {summary.tool_valid_rate:.2%} |",
        f"| Patch Apply Rate | {summary.patch_apply_rate:.2%} |",
        f"| Format Error Rate | {summary.format_error_rate:.2%} |",
        f"| Run Test Before Submit Rate | {summary.run_test_before_submit_rate:.2%} |",
        f"| Unrelated Edit Rate | {summary.unrelated_edit_rate:.2%} |",
        f"| Avg Steps | {summary.avg_steps:.2f} |",
        "",
        "## Per Task",
        "",
        "| Task | Success | Reward | Steps | Patch | Ran Tests First | Unrelated Edit | Failure Type |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for trace in traces:
        lines.append(
            f"| {trace.task_id} | {str(trace.success)} | {trace.reward:.2f} | {len(trace.steps)} | "
            f"{str(bool(trace.metrics.get('patch_apply')))} | "
            f"{str(bool(trace.metrics.get('ran_tests_before_submit')))} | "
            f"{str(bool(trace.metrics.get('unrelated_edit')))} | {trace.failure_type or ''} |"
        )

    lines.extend(["", "## Failure Counts", ""])
    if summary.failure_counts:
        for failure_type, count in summary.failure_counts.items():
            lines.append(f"- `{failure_type}`: {count}")
    else:
        lines.append("- No failures.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_real_baseline_report(
    path: Path,
    traces: list[Trace],
    summary: EvalSummary,
    failure_analysis: dict | None = None,
) -> None:
    """Generate a real-model baseline report with failure taxonomy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Real Baseline Evaluation Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total Tasks | {summary.total_tasks} |",
        f"| Task Success Rate | {summary.task_success_rate:.2%} |",
        f"| Test Pass Rate | {summary.test_pass_rate:.2%} |",
        f"| Tool Valid Rate | {summary.tool_valid_rate:.2%} |",
        f"| Patch Apply Rate | {summary.patch_apply_rate:.2%} |",
        f"| Format Error Rate | {summary.format_error_rate:.2%} |",
        f"| Run Test Before Submit Rate | {summary.run_test_before_submit_rate:.2%} |",
        f"| Unrelated Edit Rate | {summary.unrelated_edit_rate:.2%} |",
        f"| Avg Steps | {summary.avg_steps:.2f} |",
    ]

    if failure_analysis and failure_analysis.get("taxonomy"):
        lines.extend(
            [
                "",
                "## Failure Taxonomy",
                "",
                "| Failure Type | Count |",
                "|---|---:|",
            ]
        )
        for ftype, count in sorted(failure_analysis["taxonomy"].items(), key=lambda x: -x[1]):
            lines.append(f"| {ftype} | {count} |")

    lines.extend(
        [
            "",
            "## Per Task",
            "",
            "| Task | Success | Reward | Steps | Format Errors | Failure Type |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for trace in traces:
        lines.append(
            f"| {trace.task_id} | {str(trace.success)} | {trace.reward:.2f} | "
            f"{len(trace.steps)} | {trace.metrics.get('format_errors', 0)} | {trace.failure_type or ''} |"
        )

    lines.extend(["", "## Failure Counts", ""])
    if summary.failure_counts:
        for failure_type, count in summary.failure_counts.items():
            lines.append(f"- `{failure_type}`: {count}")
    else:
        lines.append("- No failures.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

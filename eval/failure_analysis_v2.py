"""Analyze failures from Step-SFT v2 evaluation.

Categorizes failures and provides detailed diagnosis.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter


def analyze_failure(trace: dict) -> dict:
    """Analyze a single failed trace."""
    steps = trace.get("steps", [])
    task_id = trace.get("task_id", "")
    
    # Basic info
    num_steps = len(steps)
    has_edit = False
    has_run_tests = False
    has_submit = False
    edit_target_file = False
    tests_passed = False
    loop_detected = False
    
    # Analyze steps
    action_sequence = []
    for step in steps:
        action = step.get("action", {})
        action_name = action.get("name", "")
        action_sequence.append(action_name)
        
        if action_name == "edit_file":
            has_edit = True
        if action_name == "run_tests":
            has_run_tests = True
        if action_name == "submit_patch":
            has_submit = True
        
        # Check if tests passed
        observation = step.get("observation", "")
        if "passed" in observation.lower() and action_name == "run_tests":
            tests_passed = True
    
    # Check for loop
    for i in range(len(action_sequence) - 2):
        if action_sequence[i] == action_sequence[i+1] == action_sequence[i+2] and action_sequence[i]:
            loop_detected = True
            break
    
    # Classify failure
    if not has_edit:
        failure_type = "NO_EDIT"
    elif not has_run_tests:
        failure_type = "NO_TEST_AFTER_EDIT"
    elif loop_detected:
        failure_type = "LOOP_NO_PROGRESS"
    elif tests_passed and not has_submit:
        failure_type = "SUCCESS_BUT_NO_SUBMIT"
    elif not tests_passed:
        failure_type = "TEST_FAIL_AFTER_EDIT"
    else:
        failure_type = "UNKNOWN"
    
    return {
        "task_id": task_id,
        "failure_type": failure_type,
        "num_steps": num_steps,
        "has_edit": has_edit,
        "has_run_tests": has_run_tests,
        "has_submit": has_submit,
        "tests_passed": tests_passed,
        "loop_detected": loop_detected,
        "action_sequence": action_sequence,
    }


def main():
    root = Path(__file__).resolve().parents[2]
    
    # Load failed traces
    trace_dir = root / "outputs" / "reports" / "eval_3b_step_sft_v2"
    failed_traces = []
    
    for trace_file in trace_dir.rglob("*.trace.json"):
        trace = json.loads(trace_file.read_text())
        if not trace.get("success"):
            failed_traces.append(trace)
    
    print(f"Total failed traces: {len(failed_traces)}")
    
    # Analyze each failure
    analyses = []
    for trace in failed_traces:
        analysis = analyze_failure(trace)
        analyses.append(analysis)
    
    # Count failure types
    failure_types = Counter(a["failure_type"] for a in analyses)
    
    print("\nFailure Type Distribution:")
    for ft, count in failure_types.most_common():
        print(f"  {ft}: {count}")
    
    # Detailed analysis
    print("\nDetailed Failure Analysis:")
    print("=" * 80)
    
    for analysis in analyses:
        print(f"\nTask: {analysis['task_id']}")
        print(f"  Failure Type: {analysis['failure_type']}")
        print(f"  Steps: {analysis['num_steps']}")
        print(f"  Has Edit: {analysis['has_edit']}")
        print(f"  Has Run Tests: {analysis['has_run_tests']}")
        print(f"  Has Submit: {analysis['has_submit']}")
        print(f"  Tests Passed: {analysis['tests_passed']}")
        print(f"  Loop Detected: {analysis['loop_detected']}")
        print(f"  Action Sequence: {' -> '.join(analysis['action_sequence'][:10])}")
    
    # Save report
    report = {
        "total_failed": len(failed_traces),
        "failure_types": dict(failure_types),
        "analyses": analyses,
    }
    
    report_path = root / "outputs" / "reports" / "step_sft_v2_failure_analysis.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved report: {report_path}")
    
    # Generate markdown report
    md_lines = [
        "# Step-SFT v2 Failure Analysis",
        "",
        f"## Summary",
        "",
        f"- Total failed traces: {len(failed_traces)}",
        "",
        "## Failure Type Distribution",
        "",
        "| Failure Type | Count |",
        "|---|---:|",
    ]
    
    for ft, count in failure_types.most_common():
        md_lines.append(f"| {ft} | {count} |")
    
    md_lines.extend([
        "",
        "## Detailed Analysis",
        "",
    ])
    
    for analysis in analyses:
        md_lines.extend([
            f"### {analysis['task_id']}",
            "",
            f"- **Failure Type:** {analysis['failure_type']}",
            f"- **Steps:** {analysis['num_steps']}",
            f"- **Has Edit:** {analysis['has_edit']}",
            f"- **Has Run Tests:** {analysis['has_run_tests']}",
            f"- **Tests Passed:** {analysis['tests_passed']}",
            f"- **Loop Detected:** {analysis['loop_detected']}",
            f"- **Action Sequence:** `{' -> '.join(analysis['action_sequence'][:10])}`",
            "",
        ])
    
    md_path = root / "outputs" / "reports" / "step_sft_v2_failure_analysis.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Saved markdown report: {md_path}")


if __name__ == "__main__":
    main()

"""Audit and label teacher traces for quality stratification.

Classifies traces into:
- high_quality_success: success + high quality score
- low_quality_success: success but low quality
- productive_failure: failed but made progress
- bad_failure: failed with no progress

Usage:
    python -m evocode_orchard_lite.data_builder.audit_teacher_traces
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter


def compute_quality_score(trace: dict) -> tuple[int, dict]:
    """Compute quality score for a trace. Returns (score, details)."""
    score = 0
    details = {}
    
    success = trace.get("success", False)
    steps = trace.get("steps", [])
    metrics = trace.get("metrics", {})
    
    # Success bonus
    if success:
        score += 5
        details["success"] = 5
    
    # Tests passed
    if metrics.get("tests_passed", False):
        score += 3
        details["tests_passed"] = 3
    
    # Edit target file
    if metrics.get("edit_target_file", False):
        score += 2
        details["edit_target_file"] = 2
    
    # Read target file
    if metrics.get("read_target_file", False):
        score += 2
        details["read_target_file"] = 2
    
    # Run tests after edit
    ran_tests_after_edit = False
    edited = False
    for step in steps:
        action_name = step.get("action", {}).get("name", "")
        if action_name == "edit_file":
            edited = True
        if action_name == "run_tests" and edited:
            ran_tests_after_edit = True
    if ran_tests_after_edit:
        score += 1
        details["run_tests_after_edit"] = 1
    
    # Submit after passed test
    if metrics.get("ran_tests_before_submit", False):
        score += 1
        details["submit_after_test"] = 1
    
    # Patch apply
    if metrics.get("patch_apply", False):
        score += 1
        details["patch_apply"] = 1
    
    # Steps <= 8
    if len(steps) <= 8:
        score += 1
        details["steps_le_8"] = 1
    
    # Penalties
    # Unrelated edit
    if metrics.get("unrelated_edit", False):
        score -= 3
        details["unrelated_edit"] = -3
    
    # Loop detected (same action repeated 3+ times)
    action_sequence = [s.get("action", {}).get("name", "") for s in steps]
    loop_detected = False
    for i in range(len(action_sequence) - 2):
        if action_sequence[i] == action_sequence[i+1] == action_sequence[i+2] and action_sequence[i]:
            loop_detected = True
            break
    if loop_detected:
        score -= 3
        details["loop_detected"] = -3
    
    # Submit before passed test
    if metrics.get("premature_submit", False):
        score -= 3
        details["premature_submit"] = -3
    
    # Format error
    format_errors = metrics.get("format_errors", 0)
    if format_errors > 0:
        score -= 2
        details["format_error"] = -2
    
    # Invalid tool
    if metrics.get("tool_valid", True) == False:
        score -= 2
        details["invalid_tool"] = -2
    
    # Steps > 12
    if len(steps) > 12:
        score -= 1
        details["steps_gt_12"] = -1
    
    return score, details


def classify_trace(trace: dict, quality_score: int) -> str:
    """Classify trace into category."""
    success = trace.get("success", False)
    metrics = trace.get("metrics", {})
    
    if success:
        if quality_score >= 8 and not metrics.get("unrelated_edit", False):
            return "high_quality_success"
        else:
            return "low_quality_success"
    else:
        # Check if made progress
        read_target = metrics.get("read_target_file", False)
        edit_target = metrics.get("edit_target_file", False)
        patch_apply = metrics.get("patch_apply", False)
        
        if read_target or edit_target or patch_apply:
            return "productive_failure"
        else:
            return "bad_failure"


def load_all_traces(root: Path) -> list[dict]:
    """Load all traces from rollout directories."""
    traces = []
    
    # Load from rollouts directory
    rollouts_dir = root / "outputs" / "rollouts"
    if rollouts_dir.exists():
        for run_dir in rollouts_dir.iterdir():
            if not run_dir.is_dir():
                continue
            for status in ["success", "failed"]:
                status_dir = run_dir / status
                if not status_dir.exists():
                    continue
                for task_dir in status_dir.iterdir():
                    if not task_dir.is_dir():
                        continue
                    for trace_file in task_dir.glob("*.trace.json"):
                        try:
                            trace = json.loads(trace_file.read_text(encoding="utf-8"))
                            trace["_source_file"] = str(trace_file)
                            traces.append(trace)
                        except Exception as e:
                            print(f"Warning: Failed to load {trace_file}: {e}")
    
    return traces


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load traces
    print("Loading traces...")
    traces = load_all_traces(root)
    print(f"Loaded {len(traces)} traces")
    
    # Audit and classify
    print("\nAuditing traces...")
    labeled_traces = []
    categories = Counter()
    
    for trace in traces:
        score, details = compute_quality_score(trace)
        category = classify_trace(trace, score)
        
        labeled_trace = {
            "task_id": trace.get("task_id"),
            "run_id": trace.get("run_id"),
            "rollout_id": trace.get("rollout_id"),
            "model": trace.get("model"),
            "success": trace.get("success"),
            "quality_score": score,
            "quality_details": details,
            "category": category,
            "num_steps": len(trace.get("steps", [])),
            "metrics": trace.get("metrics", {}),
        }
        labeled_traces.append(labeled_trace)
        categories[category] += 1
    
    # Save labeled traces
    labeled_path = output_dir / "teacher_traces_labeled.jsonl"
    with labeled_path.open("w", encoding="utf-8") as f:
        for t in labeled_traces:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"Saved labeled traces: {labeled_path}")
    
    # Save by category
    for category in ["high_quality_success", "low_quality_success", "productive_failure", "bad_failure"]:
        category_traces = [t for t in labeled_traces if t["category"] == category]
        if category_traces:
            category_path = output_dir / f"{category}_traces.jsonl"
            with category_path.open("w", encoding="utf-8") as f:
                for t in category_traces:
                    f.write(json.dumps(t, ensure_ascii=False) + "\n")
            print(f"Saved {category}: {len(category_traces)} traces -> {category_path}")
    
    # Generate audit report
    print("\n" + "=" * 60)
    print("AUDIT REPORT")
    print("=" * 60)
    print(f"Total traces: {len(traces)}")
    print()
    print("Category distribution:")
    for category, count in sorted(categories.items(), key=lambda x: -x[1]):
        pct = count / len(traces) * 100 if traces else 0
        print(f"  {category}: {count} ({pct:.1f}%)")
    
    # Quality score distribution
    scores = [t["quality_score"] for t in labeled_traces]
    print(f"\nQuality score: min={min(scores)}, max={max(scores)}, avg={sum(scores)/len(scores):.1f}")
    
    # Save audit report
    audit = {
        "total_traces": len(traces),
        "categories": dict(categories),
        "quality_score_stats": {
            "min": min(scores),
            "max": max(scores),
            "avg": sum(scores) / len(scores),
        },
    }
    audit_path = output_dir / "teacher_trace_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"\nSaved audit: {audit_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

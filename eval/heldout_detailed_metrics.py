"""Analyze detailed metrics for held-out evaluation."""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter


def analyze_traces(trace_dir: Path) -> dict:
    """Analyze traces and compute detailed metrics."""
    traces = []
    for trace_file in trace_dir.rglob("*.trace.json"):
        traces.append(json.loads(trace_file.read_text()))
    
    if not traces:
        return {}
    
    total = len(traces)
    success = sum(1 for t in traces if t.get("success"))
    
    # Detailed metrics
    json_parse_success = 0
    tool_valid = 0
    read_target_file = 0
    edit_target_file = 0
    test_pass_after_edit = 0
    total_steps = 0
    loop_count = 0
    no_edit_count = 0
    
    for trace in traces:
        steps = trace.get("steps", [])
        total_steps += len(steps)
        
        # JSON parse success (no format errors)
        format_errors = trace.get("metrics", {}).get("format_errors", 0)
        if format_errors == 0:
            json_parse_success += 1
        
        # Tool validity
        if format_errors == 0:
            tool_valid += 1
        
        # Check actions
        has_edit = False
        has_run_tests = False
        has_submit = False
        tests_passed = False
        action_sequence = []
        
        for step in steps:
            action_name = step.get("action", {}).get("name", "")
            action_sequence.append(action_name)
            
            if action_name == "read_file":
                read_target_file += 1
            if action_name == "edit_file":
                has_edit = True
                edit_target_file += 1
            if action_name == "run_tests":
                has_run_tests = True
                if "passed" in step.get("observation", "").lower():
                    tests_passed = True
            if action_name == "submit_patch":
                has_submit = True
        
        # Test pass after edit
        if has_edit and tests_passed:
            test_pass_after_edit += 1
        
        # Loop detection
        for i in range(len(action_sequence) - 2):
            if action_sequence[i] == action_sequence[i+1] == action_sequence[i+2] and action_sequence[i]:
                loop_count += 1
                break
        
        # NO_EDIT detection
        if not has_edit:
            no_edit_count += 1
    
    return {
        "total": total,
        "success": success,
        "success_rate": success / total if total else 0,
        "json_parse_success": json_parse_success / total if total else 0,
        "tool_valid_rate": tool_valid / total if total else 0,
        "read_target_file_rate": read_target_file / total if total else 0,
        "edit_target_file_rate": edit_target_file / total if total else 0,
        "test_pass_after_edit_rate": test_pass_after_edit / total if total else 0,
        "avg_steps": total_steps / total if total else 0,
        "loop_rate": loop_count / total if total else 0,
        "no_edit_rate": no_edit_count / total if total else 0,
        "failure_counts": dict(Counter(
            "TEST_STILL_FAIL" if not t.get("success") else "SUCCESS"
            for t in traces
        )),
    }


def main():
    root = Path(__file__).resolve().parents[2]
    
    # Analyze held-out evaluation
    heldout_dir = root / "outputs" / "reports" / "heldout_eval"
    
    models = {
        "3B Base": heldout_dir / "3b_base",
        "3B Step-SFT v2": heldout_dir / "3b_step_sft_v2",
        "7B Base": heldout_dir / "7b_base",
    }
    
    results = {}
    for name, path in models.items():
        if path.exists():
            results[name] = analyze_traces(path)
    
    # Print comparison table
    print("=" * 100)
    print("NEW 50 HELD-OUT DETAILED METRICS")
    print("=" * 100)
    
    metrics = [
        ("Success Rate", "success_rate"),
        ("JSON Parse", "json_parse_success"),
        ("Tool Valid", "tool_valid_rate"),
        ("Read Target File", "read_target_file_rate"),
        ("Edit Target File", "edit_target_file_rate"),
        ("Test Pass After Edit", "test_pass_after_edit_rate"),
        ("Avg Steps", "avg_steps"),
        ("Loop Rate", "loop_rate"),
        ("NO_EDIT Rate", "no_edit_rate"),
    ]
    
    header = f"{'Metric':<25}"
    for name in results:
        header += f"{name:>15}"
    print(header)
    print("-" * 100)
    
    for label, key in metrics:
        row = f"{label:<25}"
        for name in results:
            val = results[name].get(key, 0)
            if key == "avg_steps":
                row += f"{val:>15.1f}"
            else:
                row += f"{val:>14.1%}"
        print(row)
    
    print("=" * 100)
    
    # Failure analysis for Step-SFT v2
    if "3B Step-SFT v2" in results:
        print("\n3B Step-SFT v2 FAILURE ANALYSIS:")
        print("-" * 50)
        
        sft_dir = models["3B Step-SFT v2"]
        failed_traces = []
        for trace_file in sft_dir.rglob("*.trace.json"):
            trace = json.loads(trace_file.read_text())
            if not trace.get("success"):
                failed_traces.append(trace)
        
        print(f"Total failures: {len(failed_traces)}")
        
        # Analyze failure patterns
        failure_patterns = Counter()
        for trace in failed_traces:
            steps = trace.get("steps", [])
            action_sequence = [s.get("action", {}).get("name", "") for s in steps]
            
            has_edit = "edit_file" in action_sequence
            has_run_tests = "run_tests" in action_sequence
            has_submit = "submit_patch" in action_sequence
            
            # Check for loop
            loop_detected = False
            for i in range(len(action_sequence) - 2):
                if action_sequence[i] == action_sequence[i+1] == action_sequence[i+2] and action_sequence[i]:
                    loop_detected = True
                    break
            
            if not has_edit:
                failure_patterns["NO_EDIT (loop)"] += 1
            elif not has_run_tests:
                failure_patterns["NO_TEST_AFTER_EDIT"] += 1
            elif loop_detected:
                failure_patterns["LOOP_NO_PROGRESS"] += 1
            else:
                failure_patterns["TEST_FAIL_AFTER_EDIT"] += 1
        
        print("\nFailure patterns:")
        for pattern, count in failure_patterns.most_common():
            print(f"  {pattern}: {count}")
    
    # Save results
    output_path = heldout_dir / "heldout_detailed_metrics.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()

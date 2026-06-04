"""Compare evaluation results across models."""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter


def analyze_traces(trace_dir: Path) -> dict:
    """Analyze traces and compute metrics."""
    traces = []
    for trace_file in trace_dir.rglob("*.trace.json"):
        traces.append(json.loads(trace_file.read_text()))
    
    if not traces:
        return {}
    
    total = len(traces)
    success = sum(1 for t in traces if t.get("success"))
    
    # JSON parse success (no format errors in first step)
    json_parse_success = 0
    tool_valid = 0
    run_tests_before_edit = 0
    read_target_file = 0
    edit_target_file = 0
    test_pass_after_edit = 0
    premature_submit = 0
    total_steps = 0
    loop_count = 0
    unrelated_edit = 0
    
    for trace in traces:
        steps = trace.get("steps", [])
        total_steps += len(steps)
        
        # Check if first action was successful (JSON parse)
        if steps and steps[0].get("tool_success", False):
            json_parse_success += 1
        
        # Check tool validity
        format_errors = trace.get("metrics", {}).get("format_errors", 0)
        if format_errors == 0:
            tool_valid += 1
        
        # Check if ran tests before edit
        ran_tests_first = False
        edited = False
        for step in steps:
            action_name = step.get("action", {}).get("name", "")
            if action_name == "run_tests" and not edited:
                ran_tests_first = True
            if action_name == "edit_file":
                edited = True
                break
        if ran_tests_first:
            run_tests_before_edit += 1
        
        # Check if read target file
        target_files = set()
        for step in steps:
            action_name = step.get("action", {}).get("name", "")
            if action_name == "read_file":
                path = step.get("action", {}).get("arguments", {}).get("path", "")
                if path:
                    read_target_file += 1
                    break
        
        # Check if edited target file
        for step in steps:
            action_name = step.get("action", {}).get("name", "")
            if action_name == "edit_file":
                edit_target_file += 1
                break
        
        # Check premature submit (submit without running tests)
        submitted = False
        ran_tests = False
        for step in steps:
            action_name = step.get("action", {}).get("name", "")
            if action_name == "run_tests":
                ran_tests = True
            if action_name == "submit_patch":
                if not ran_tests:
                    premature_submit += 1
                submitted = True
                break
        
        # Check loop (same action repeated)
        action_sequence = [s.get("action", {}).get("name", "") for s in steps]
        for i in range(len(action_sequence) - 2):
            if action_sequence[i] == action_sequence[i+1] == action_sequence[i+2] and action_sequence[i]:
                loop_count += 1
                break
        
        # Check unrelated edit
        if trace.get("metrics", {}).get("unrelated_edit", False):
            unrelated_edit += 1
    
    return {
        "total": total,
        "success_rate": success / total if total else 0,
        "json_parse_success": json_parse_success / total if total else 0,
        "tool_valid_rate": tool_valid / total if total else 0,
        "run_tests_before_edit": run_tests_before_edit / total if total else 0,
        "read_target_file": read_target_file / total if total else 0,
        "edit_target_file": edit_target_file / total if total else 0,
        "test_pass_after_edit": success / total if total else 0,
        "premature_submit_rate": premature_submit / total if total else 0,
        "avg_steps": total_steps / total if total else 0,
        "loop_rate": loop_count / total if total else 0,
        "unrelated_edit_rate": unrelated_edit / total if total else 0,
    }


def main():
    root = Path("outputs/reports")
    
    models = {
        "3B Base": root / "eval_3b_base",
        "3B Old-SFT": root / "eval_sft",
        "3B Step-SFT": root / "eval_3b_step_sft",
        "7B Base": root / "eval_7b",
    }
    
    results = {}
    for name, path in models.items():
        if path.exists():
            results[name] = analyze_traces(path)
            print(f"Loaded {name}: {results[name].get('total', 0)} traces")
        else:
            print(f"Skipping {name}: {path} not found")
    
    if not results:
        print("No results found!")
        return
    
    # Print comparison table
    metrics = [
        ("success_rate", "Success Rate"),
        ("json_parse_success", "JSON Parse Success"),
        ("tool_valid_rate", "Tool Valid Rate"),
        ("run_tests_before_edit", "Run Tests Before Edit"),
        ("read_target_file", "Read Target File"),
        ("edit_target_file", "Edit Target File"),
        ("test_pass_after_edit", "Test Pass After Edit"),
        ("premature_submit_rate", "Premature Submit Rate"),
        ("avg_steps", "Avg Steps"),
        ("loop_rate", "Loop Rate"),
        ("unrelated_edit_rate", "Unrelated Edit Rate"),
    ]
    
    print("\n" + "=" * 80)
    print("Model Comparison")
    print("=" * 80)
    
    # Header
    header = f"{'Metric':<25}"
    for name in results:
        header += f"{name:>15}"
    print(header)
    print("-" * 80)
    
    # Rows
    for key, label in metrics:
        row = f"{label:<25}"
        for name in results:
            val = results[name].get(key, 0)
            if key == "avg_steps":
                row += f"{val:>15.1f}"
            else:
                row += f"{val:>14.1%}"
        print(row)
    
    print("=" * 80)
    
    # Save to file
    output = {
        "models": results,
        "comparison": {name: {k: v for k, v in stats.items()} for name, stats in results.items()}
    }
    
    output_path = root / "model_comparison.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()

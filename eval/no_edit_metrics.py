"""Compute NO_EDIT and read-only loop metrics for evaluation traces.

Metrics:
- NO_EDIT Rate: episode failed with edit_file_count = 0
- Read-only Loop Rate: read_file/search_code repeated >= 3 times without edit/run_tests/submit
- Same-file Read Loop Rate: same file read >= 2 times without edit
- Read-to-Edit Rate: after reading target file, did model edit?
- Edit After Target Read: did edit_file(target) occur after read_file(target)?
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter


def compute_no_edit_metrics(trace: dict, target_files: set[str] = None) -> dict:
    """Compute NO_EDIT metrics for a single trace."""
    steps = trace.get("steps", [])
    action_sequence = [s.get("action", {}).get("name", "") for s in steps]
    
    # Basic counts
    edit_count = action_sequence.count("edit_file")
    read_count = action_sequence.count("read_file")
    run_tests_count = action_sequence.count("run_tests")
    submit_count = action_sequence.count("submit_patch")
    
    # NO_EDIT: failed with no edit
    success = trace.get("success", False)
    no_edit = not success and edit_count == 0
    
    # Read-only loop: read_file/search_code repeated >= 3 times without progress
    read_only_loop = False
    read_streak = 0
    for action in action_sequence:
        if action in ("read_file", "search_code"):
            read_streak += 1
            if read_streak >= 3:
                read_only_loop = True
                break
        else:
            read_streak = 0
    
    # Same-file read loop: same file read >= 2 times without edit
    same_file_loop = False
    read_files = []
    for step in steps:
        action = step.get("action", {})
        if action.get("name") == "read_file":
            path = action.get("arguments", {}).get("path", "")
            if path:
                read_files.append(path)
    
    file_counts = Counter(read_files)
    for file, count in file_counts.items():
        if count >= 2:
            same_file_loop = True
            break
    
    # Read-to-Edit: after reading target file, did model edit?
    read_target = False
    edit_after_read = False
    for step in steps:
        action = step.get("action", {})
        action_name = action.get("name", "")
        path = action.get("arguments", {}).get("path", "")
        
        if action_name == "read_file" and target_files and path in target_files:
            read_target = True
        if action_name == "edit_file" and read_target:
            edit_after_read = True
            break
    
    return {
        "success": success,
        "no_edit": no_edit,
        "read_only_loop": read_only_loop,
        "same_file_loop": same_file_loop,
        "read_target": read_target,
        "edit_after_read": edit_after_read,
        "edit_count": edit_count,
        "read_count": read_count,
        "run_tests_count": run_tests_count,
        "submit_count": submit_count,
    }


def load_target_files(root: Path, task_id: str) -> set[str]:
    """Load target files from task metadata."""
    meta_path = root / "benchmark" / "tasks" / task_id / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return set(meta.get("target_files", []))
    return set()


def analyze_traces(trace_dir: Path, root: Path) -> dict:
    """Analyze traces and compute NO_EDIT metrics."""
    traces = []
    for trace_file in trace_dir.rglob("*.trace.json"):
        traces.append(json.loads(trace_file.read_text()))
    
    if not traces:
        return {}
    
    total = len(traces)
    metrics_list = []
    
    for trace in traces:
        task_id = trace.get("task_id", "")
        target_files = load_target_files(root, task_id)
        metrics = compute_no_edit_metrics(trace, target_files)
        metrics_list.append(metrics)
    
    # Aggregate metrics
    success = sum(1 for m in metrics_list if m["success"])
    no_edit = sum(1 for m in metrics_list if m["no_edit"])
    read_only_loop = sum(1 for m in metrics_list if m["read_only_loop"])
    same_file_loop = sum(1 for m in metrics_list if m["same_file_loop"])
    read_target = sum(1 for m in metrics_list if m["read_target"])
    edit_after_read = sum(1 for m in metrics_list if m["edit_after_read"])
    
    return {
        "total": total,
        "success": success,
        "success_rate": success / total if total else 0,
        "no_edit_count": no_edit,
        "no_edit_rate": no_edit / total if total else 0,
        "read_only_loop_count": read_only_loop,
        "read_only_loop_rate": read_only_loop / total if total else 0,
        "same_file_loop_count": same_file_loop,
        "same_file_loop_rate": same_file_loop / total if total else 0,
        "read_target_count": read_target,
        "edit_after_read_count": edit_after_read,
        "read_to_edit_rate": edit_after_read / read_target if read_target else 0,
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
            results[name] = analyze_traces(path, root)
    
    # Print comparison table
    print("=" * 100)
    print("NO_EDIT / READ-ONLY LOOP METRICS")
    print("=" * 100)
    
    metrics = [
        ("Success Rate", "success_rate"),
        ("NO_EDIT Rate", "no_edit_rate"),
        ("Read-only Loop Rate", "read_only_loop_rate"),
        ("Same-file Loop Rate", "same_file_loop_rate"),
        ("Read-to-Edit Rate", "read_to_edit_rate"),
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
            row += f"{val:>14.1%}"
        print(row)
    
    print("=" * 100)
    
    # Save results
    output_path = heldout_dir / "no_edit_metrics.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()

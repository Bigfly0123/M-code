"""Build Patch-Correctness DPO pairs from New100 v2.1-clean traces.

For each failed task, construct:
- chosen: success trace (from same task if available, or from same bug_type)
- rejected: v2.1-clean failure trace

If no success trace exists for the same task, use a success trace from
the same bug_type as a proxy chosen.
"""
import json
from pathlib import Path
from collections import defaultdict


def trace_to_step_sequence(trace):
    """Convert trace to list of (action_name, action_args, observation_preview)."""
    steps = []
    for s in trace.get("steps", []):
        action = s.get("action", {})
        name = action.get("name", "") if isinstance(action, dict) else ""
        args = action.get("arguments", {}) if isinstance(action, dict) else {}
        obs = str(s.get("observation", ""))[:500]
        steps.append({"name": name, "arguments": args, "observation": obs})
    return steps


def build_dpo_sample(task_id, bug_type, difficulty, chosen_trace, rejected_trace, pair_type):
    """Build a single DPO training sample."""
    # Build prompt from task
    chosen_steps = trace_to_step_sequence(chosen_trace)
    rejected_steps = trace_to_step_sequence(rejected_trace)

    # Use the task issue as prompt context
    return {
        "pair_id": f"{task_id}_{pair_type}_001",
        "task_id": task_id,
        "bug_type": bug_type,
        "difficulty": difficulty,
        "pair_type": pair_type,
        "chosen_steps": chosen_steps,
        "rejected_steps": rejected_steps,
        "chosen_num_steps": len(chosen_steps),
        "rejected_num_steps": len(rejected_steps),
        "chosen_success": chosen_trace.get("success", False),
        "rejected_success": rejected_trace.get("success", False),
        "rejected_failure_type": classify_failure(rejected_trace),
    }


def classify_failure(trace):
    """Classify failure type."""
    if trace.get("success"):
        return "SUCCESS"
    has_edit = False
    has_tests = False
    test_passed = False
    for s in trace.get("steps", []):
        action = s.get("action", {})
        name = action.get("name", "")
        if name == "edit_file":
            has_edit = True
        if name == "run_tests":
            has_tests = True
            obs = str(s.get("observation", ""))
            if "passed" in obs.lower() or "PASSED" in obs:
                test_passed = True
    if not has_edit:
        return "NO_EDIT"
    if has_edit and has_tests and not test_passed:
        return "TEST_STILL_FAIL"
    return "OTHER"


def main():
    root = Path(__file__).resolve().parents[2]
    new100_dir = root / "outputs" / "reports" / "full_metrics_new100"
    tasks_root = root / "benchmark" / "tasks"
    output_dir = root / "outputs" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir = root / "outputs" / "reports"

    # Load v2.1-clean traces
    v21_traces = {}
    for subdir in ["success", "failed"]:
        for f in (new100_dir / "3b_sft_v21_clean" / subdir).glob("*.json"):
            try:
                t = json.loads(f.read_text(encoding="utf-8"))
                v21_traces[t["task_id"]] = t
            except:
                pass

    # Load 7B base traces (as teacher success source)
    base7b_traces = {}
    for subdir in ["success", "failed"]:
        for f in (new100_dir / "7b_base" / subdir).glob("*.json"):
            try:
                t = json.loads(f.read_text(encoding="utf-8"))
                base7b_traces[t["task_id"]] = t
            except:
                pass

    print(f"v2.1-clean traces: {len(v21_traces)}")
    print(f"7B Base traces: {len(base7b_traces)}")

    # Load task metadata
    task_meta = {}
    for tid in set(list(v21_traces.keys()) + list(base7b_traces.keys())):
        meta_path = tasks_root / tid / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            task_meta[tid] = meta

    # Build DPO pairs
    pairs = []
    pair_types = defaultdict(int)

    for tid, v21_trace in v21_traces.items():
        if v21_trace.get("success"):
            continue  # Only use failures as rejected

        meta = task_meta.get(tid, {})
        bug_type = meta.get("bug_type", "unknown")
        difficulty = meta.get("difficulty", "unknown")
        failure_type = classify_failure(v21_trace)

        # Strategy 1: same-task 7B success as chosen
        if tid in base7b_traces and base7b_traces[tid].get("success"):
            pair = build_dpo_sample(tid, bug_type, difficulty,
                                   base7b_traces[tid], v21_trace,
                                   "correct_patch_vs_wrong_patch")
            pairs.append(pair)
            pair_types["same_task_7b_success"] += 1
            continue

        # Strategy 2: same bug_type success from 7B
        same_type_success = [
            (t_id, t) for t_id, t in base7b_traces.items()
            if t.get("success") and task_meta.get(t_id, {}).get("bug_type") == bug_type
        ]
        if same_type_success:
            chosen_tid, chosen_trace = same_type_success[0]
            pair = build_dpo_sample(tid, bug_type, difficulty,
                                   chosen_trace, v21_trace,
                                   "same_bugtype_success")
            pairs.append(pair)
            pair_types["same_bugtype_7b_success"] += 1
            continue

        # Strategy 3: v2.1-clean success from same bug_type
        same_type_v21 = [
            (t_id, t) for t_id, t in v21_traces.items()
            if t.get("success") and task_meta.get(t_id, {}).get("bug_type") == bug_type
        ]
        if same_type_v21:
            chosen_tid, chosen_trace = same_type_v21[0]
            pair = build_dpo_sample(tid, bug_type, difficulty,
                                   chosen_trace, v21_trace,
                                   "same_bugtype_v21_success")
            pairs.append(pair)
            pair_types["same_bugtype_v21_success"] += 1
            continue

        # No suitable chosen found
        pair_types["no_chosen_found"] += 1

    # Save
    output_path = output_dir / "dpo_patch_correctness_pairs.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"\nDPO pairs: {len(pairs)}")
    print(f"Pair sources: {dict(pair_types)}")

    # Verify
    chosen_success = sum(1 for p in pairs if p["chosen_success"])
    rejected_fail = sum(1 for p in pairs if not p["rejected_success"])
    print(f"Chosen success rate: {chosen_success}/{len(pairs)}")
    print(f"Rejected failure rate: {rejected_fail}/{len(pairs)}")

    # Audit
    audit = {
        "total_pairs": len(pairs),
        "pair_sources": dict(pair_types),
        "chosen_success_rate": chosen_success / max(len(pairs), 1),
        "rejected_failure_rate": rejected_fail / max(len(pairs), 1),
        "failure_types": defaultdict(int),
        "bug_types": defaultdict(int),
    }
    for p in pairs:
        audit["failure_types"][p["rejected_failure_type"]] += 1
        audit["bug_types"][p["bug_type"]] += 1
    audit["failure_types"] = dict(audit["failure_types"])
    audit["bug_types"] = dict(audit["bug_types"])

    (report_dir / "dpo_patch_correctness_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nAudit saved: {report_dir / 'dpo_patch_correctness_audit.json'}")


if __name__ == "__main__":
    main()

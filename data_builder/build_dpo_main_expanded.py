"""Expand DPO pairs to 200-300 from all available sources.

Sources:
1. dpo_pairs.jsonl (45 train-only mimo pairs)
2. dpo_patch_correctness_pairs.jsonl (33 new100 pairs)
3. new100 traces: 7B success vs v2.1-clean failure
4. new100 traces: v2.1-clean success vs 3B/v2 failure
5. dpo_rejected_errors.jsonl (train-only failures paired with successes)
"""
import json
from pathlib import Path
from collections import defaultdict


def trace_to_action_sequence(trace, max_steps=10):
    """Extract key actions from a trace."""
    actions = []
    for s in trace.get("steps", [])[:max_steps]:
        action = s.get("action", {})
        name = action.get("name", "")
        args = action.get("arguments", {})
        obs = str(s.get("observation", ""))[:300]
        actions.append({"name": name, "arguments": args, "observation": obs})
    return actions


def actions_to_text(actions):
    """Convert action sequence to text for DPO."""
    parts = []
    for a in actions:
        name = a["name"]
        args = a["arguments"]
        if name == "edit_file":
            parts.append(f'{{"action": "edit_file", "arguments": {json.dumps(args, ensure_ascii=False)}}}')
        elif name == "run_tests":
            parts.append('{"action": "run_tests", "arguments": {}}')
        elif name == "submit_patch":
            parts.append('{"action": "submit_patch", "arguments": {}}')
        elif name == "read_file":
            parts.append(f'{{"action": "read_file", "arguments": {{"path": "{args.get("path", "")}"}}}}')
    return "\n".join(parts) if parts else '{"action": "submit_patch", "arguments": {}}'


def classify_failure(trace):
    if trace.get("success"):
        return "SUCCESS"
    has_edit = False
    has_tests = False
    test_passed = False
    for s in trace.get("steps", []):
        a = s.get("action", {})
        name = a.get("name", "")
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
    if has_edit and not has_tests:
        return "NO_TEST_AFTER_EDIT"
    return "OTHER"


def main():
    root = Path(__file__).resolve().parents[2]
    data_dir = root / "outputs" / "data"
    report_dir = root / "outputs" / "reports"
    new100_dir = root / "outputs" / "reports" / "full_metrics_new100"
    tasks_root = root / "benchmark" / "tasks"

    # Load splits
    train_tasks = set(l.strip() for l in open(data_dir / "splits" / "train_tasks.txt") if l.strip())
    test_tasks = set(l.strip() for l in open(data_dir / "splits" / "test_tasks.txt") if l.strip())
    heldout = set(f"bugfix_{i}" for i in range(201, 351))
    print(f"Train: {len(train_tasks)}, Test: {len(test_tasks)}, Heldout: {len(heldout)}")

    # Load task metadata
    task_meta = {}
    for p in tasks_root.iterdir():
        if p.is_dir() and p.name.startswith("bugfix_"):
            meta_path = p / "metadata.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                task_meta[p.name] = meta

    all_pairs = []
    pair_id_counter = 0
    source_counts = defaultdict(int)

    # ============================================================
    # Source 1: Existing dpo_pairs.jsonl (train-only, 45 pairs)
    # ============================================================
    print("\n=== Source 1: dpo_pairs.jsonl ===")
    old_pairs = [json.loads(l) for l in open(data_dir / "dpo_pairs.jsonl") if l.strip()]
    train_old = [p for p in old_pairs if p.get("task_id", "") in train_tasks]
    print(f"  Total: {len(old_pairs)}, Train-only: {len(train_old)}")

    for p in train_old:
        pair_id_counter += 1
        chosen_trace = p.get("chosen", {})
        rejected_trace = p.get("rejected", {})

        chosen_actions = trace_to_action_sequence(chosen_trace)
        rejected_actions = trace_to_action_sequence(rejected_trace)

        task_id = p.get("task_id", "")
        meta = task_meta.get(task_id, {})
        issue_path = tasks_root / task_id / "issue.md"
        issue = issue_path.read_text(encoding="utf-8").strip() if issue_path.exists() else f"Fix bug in {task_id}"
        prompt = f"Fix the bug:\n\n{issue}\n\nRespond with JSON: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"

        all_pairs.append({
            "pair_id": f"old_mimo_{pair_id_counter:04d}",
            "task_id": task_id,
            "bug_type": meta.get("bug_type", "unknown"),
            "difficulty": meta.get("difficulty", "unknown"),
            "pair_type": "same_task_mimo",
            "chosen_source": "mimo_v25_success",
            "rejected_source": "mimo_v2_omni_failure",
            "prompt": prompt,
            "chosen": actions_to_text(chosen_actions),
            "rejected": actions_to_text(rejected_actions),
            "rejected_failure_type": p.get("rejected_failure_type", "UNKNOWN"),
            "split": "train",
        })
        source_counts["old_mimo_pairs"] += 1

    # ============================================================
    # Source 2: Patch correctness pairs (33 pairs)
    # ============================================================
    print("\n=== Source 2: dpo_patch_correctness_pairs.jsonl ===")
    patch_pairs_path = data_dir / "dpo_patch_correctness_pairs.jsonl"
    if patch_pairs_path.exists():
        patch_pairs = [json.loads(l) for l in open(patch_pairs_path) if l.strip()]
        for p in patch_pairs:
            pair_id_counter += 1
            task_id = p.get("task_id", "")
            meta = task_meta.get(task_id, {})
            issue_path = tasks_root / task_id / "issue.md"
            issue = issue_path.read_text(encoding="utf-8").strip() if issue_path.exists() else f"Fix bug in {task_id}"
            prompt = f"Fix the bug:\n\n{issue}\n\nRespond with JSON: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"

            chosen_steps = p.get("chosen_steps", [])
            rejected_steps = p.get("rejected_steps", [])

            all_pairs.append({
                "pair_id": f"patch_{pair_id_counter:04d}",
                "task_id": task_id,
                "bug_type": meta.get("bug_type", p.get("bug_type", "unknown")),
                "difficulty": meta.get("difficulty", p.get("difficulty", "unknown")),
                "pair_type": "patch_correctness",
                "chosen_source": p.get("chosen_source", "7b_success"),
                "rejected_source": "v21_clean_failure",
                "prompt": prompt,
                "chosen": actions_to_text(chosen_steps),
                "rejected": actions_to_text(rejected_steps),
                "rejected_failure_type": p.get("rejected_failure_type", "TEST_STILL_FAIL"),
                "split": "train",
            })
            source_counts["patch_correctness"] += 1

    # ============================================================
    # Source 3: new100 7B success vs v2.1-clean failure (same task)
    # ============================================================
    print("\n=== Source 3: new100 7B success vs v2.1-clean failure ===")
    v21_traces = {}
    for subdir in ["success", "failed"]:
        d = new100_dir / "3b_sft_v21_clean" / subdir
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    t = json.loads(f.read_text(encoding="utf-8"))
                    v21_traces[t["task_id"]] = t
                except:
                    pass

    base7b_traces = {}
    for subdir in ["success", "failed"]:
        d = new100_dir / "7b_base" / subdir
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    t = json.loads(f.read_text(encoding="utf-8"))
                    base7b_traces[t["task_id"]] = t
                except:
                    pass

    # Same-task pairs: 7B success vs v2.1-clean failure
    used_tasks = set(p["task_id"] for p in all_pairs)
    for tid, v21_t in v21_traces.items():
        if v21_t.get("success") or tid in used_tasks:
            continue
        if tid not in base7b_traces or not base7b_traces[tid].get("success"):
            continue

        pair_id_counter += 1
        meta = task_meta.get(tid, {})
        issue_path = tasks_root / tid / "issue.md"
        issue = issue_path.read_text(encoding="utf-8").strip() if issue_path.exists() else f"Fix bug in {tid}"
        prompt = f"Fix the bug:\n\n{issue}\n\nRespond with JSON: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"

        chosen_actions = trace_to_action_sequence(base7b_traces[tid])
        rejected_actions = trace_to_action_sequence(v21_t)

        all_pairs.append({
            "pair_id": f"new100_7b_vs_v21_{pair_id_counter:04d}",
            "task_id": tid,
            "bug_type": meta.get("bug_type", "unknown"),
            "difficulty": meta.get("difficulty", "unknown"),
            "pair_type": "same_task_7b_vs_v21",
            "chosen_source": "7b_base_success",
            "rejected_source": "v21_clean_failure",
            "prompt": prompt,
            "chosen": actions_to_text(chosen_actions),
            "rejected": actions_to_text(rejected_actions),
            "rejected_failure_type": classify_failure(v21_t),
            "split": "train",
        })
        used_tasks.add(tid)
        source_counts["new100_7b_vs_v21"] += 1

    # ============================================================
    # Source 4: new100 v2.1-clean success vs 3B Base failure (same task)
    # ============================================================
    print("\n=== Source 4: new100 v2.1-clean success vs 3B Base failure ===")
    base3b_traces = {}
    for subdir in ["success", "failed"]:
        d = new100_dir / "3b_base" / subdir
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    t = json.loads(f.read_text(encoding="utf-8"))
                    base3b_traces[t["task_id"]] = t
                except:
                    pass

    for tid, base_t in base3b_traces.items():
        if base_t.get("success") or tid in used_tasks:
            continue
        if tid not in v21_traces or not v21_traces[tid].get("success"):
            continue

        pair_id_counter += 1
        meta = task_meta.get(tid, {})
        issue_path = tasks_root / tid / "issue.md"
        issue = issue_path.read_text(encoding="utf-8").strip() if issue_path.exists() else f"Fix bug in {tid}"
        prompt = f"Fix the bug:\n\n{issue}\n\nRespond with JSON: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"

        chosen_actions = trace_to_action_sequence(v21_traces[tid])
        rejected_actions = trace_to_action_sequence(base_t)

        all_pairs.append({
            "pair_id": f"new100_v21_vs_base_{pair_id_counter:04d}",
            "task_id": tid,
            "bug_type": meta.get("bug_type", "unknown"),
            "difficulty": meta.get("difficulty", "unknown"),
            "pair_type": "same_task_v21_vs_base",
            "chosen_source": "v21_clean_success",
            "rejected_source": "3b_base_failure",
            "prompt": prompt,
            "chosen": actions_to_text(chosen_actions),
            "rejected": actions_to_text(rejected_actions),
            "rejected_failure_type": classify_failure(base_t),
            "split": "train",
        })
        used_tasks.add(tid)
        source_counts["new100_v21_vs_base"] += 1

    # ============================================================
    # Source 5: new100 v2.1-clean success vs v2 failure (same task)
    # ============================================================
    print("\n=== Source 5: new100 v2.1-clean success vs v2 failure ===")
    v2_traces = {}
    for subdir in ["success", "failed"]:
        d = new100_dir / "3b_sft_v2" / subdir
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    t = json.loads(f.read_text(encoding="utf-8"))
                    v2_traces[t["task_id"]] = t
                except:
                    pass

    for tid, v2_t in v2_traces.items():
        if v2_t.get("success") or tid in used_tasks:
            continue
        if tid not in v21_traces or not v21_traces[tid].get("success"):
            continue

        pair_id_counter += 1
        meta = task_meta.get(tid, {})
        issue_path = tasks_root / tid / "issue.md"
        issue = issue_path.read_text(encoding="utf-8").strip() if issue_path.exists() else f"Fix bug in {tid}"
        prompt = f"Fix the bug:\n\n{issue}\n\nRespond with JSON: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"

        chosen_actions = trace_to_action_sequence(v21_traces[tid])
        rejected_actions = trace_to_action_sequence(v2_t)

        all_pairs.append({
            "pair_id": f"new100_v21_vs_v2_{pair_id_counter:04d}",
            "task_id": tid,
            "bug_type": meta.get("bug_type", "unknown"),
            "difficulty": meta.get("difficulty", "unknown"),
            "pair_type": "same_task_v21_vs_v2",
            "chosen_source": "v21_clean_success",
            "rejected_source": "v2_failure",
            "prompt": prompt,
            "chosen": actions_to_text(chosen_actions),
            "rejected": actions_to_text(rejected_actions),
            "rejected_failure_type": classify_failure(v2_t),
            "split": "train",
        })
        used_tasks.add(tid)
        source_counts["new100_v21_vs_v2"] += 1

    # ============================================================
    # Source 6: same-bug-type pairs (7B success vs v2.1-clean failure)
    # ============================================================
    print("\n=== Source 6: same-bug-type pairs ===")
    # Group v2.1-clean failures by bug_type
    v21_failures_by_type = defaultdict(list)
    for tid, t in v21_traces.items():
        if not t.get("success"):
            bt = task_meta.get(tid, {}).get("bug_type", "unknown")
            v21_failures_by_type[bt].append(tid)

    # Group 7B successes by bug_type
    base7b_success_by_type = defaultdict(list)
    for tid, t in base7b_traces.items():
        if t.get("success"):
            bt = task_meta.get(tid, {}).get("bug_type", "unknown")
            base7b_success_by_type[bt].append(tid)

    for bt, fail_tids in v21_failures_by_type.items():
        success_tids = base7b_success_by_type.get(bt, [])
        if not success_tids:
            continue

        for fail_tid in fail_tids:
            if fail_tid in used_tasks:
                continue
            chosen_tid = success_tids[0]  # Use first success as chosen

            pair_id_counter += 1
            meta = task_meta.get(fail_tid, {})
            issue_path = tasks_root / fail_tid / "issue.md"
            issue = issue_path.read_text(encoding="utf-8").strip() if issue_path.exists() else f"Fix bug in {fail_tid}"
            prompt = f"Fix the bug:\n\n{issue}\n\nRespond with JSON: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"

            chosen_actions = trace_to_action_sequence(base7b_traces[chosen_tid])
            rejected_actions = trace_to_action_sequence(v21_traces[fail_tid])

            all_pairs.append({
                "pair_id": f"bugtype_{pair_id_counter:04d}",
                "task_id": fail_tid,
                "bug_type": bt,
                "difficulty": meta.get("difficulty", "unknown"),
                "pair_type": "same_bugtype_7b_vs_v21",
                "chosen_source": f"7b_success_{chosen_tid}",
                "rejected_source": "v21_clean_failure",
                "prompt": prompt,
                "chosen": actions_to_text(chosen_actions),
                "rejected": actions_to_text(rejected_actions),
                "rejected_failure_type": classify_failure(v21_traces[fail_tid]),
                "split": "train",
            })
            used_tasks.add(fail_tid)
            source_counts["same_bugtype"] += 1

    # ============================================================
    # Summary
    # ============================================================
    print(f"\n{'='*60}")
    print(f"DPO-MAIN EXPANDED PAIRS SUMMARY")
    print(f"{'='*60}")
    print(f"Total pairs: {len(all_pairs)}")
    print(f"Sources: {dict(source_counts)}")

    # Verify
    all_tasks = set(p["task_id"] for p in all_pairs)
    heldout_leak = all_tasks & heldout
    test_leak = all_tasks & test_tasks
    print(f"Unique tasks: {len(all_tasks)}")
    print(f"Heldout leakage: {len(heldout_leak)}")
    print(f"Test split leakage: {len(test_leak)}")

    # Failure type distribution
    fail_types = defaultdict(int)
    for p in all_pairs:
        fail_types[p["rejected_failure_type"]] += 1
    print(f"Rejected failure types: {dict(fail_types)}")

    # Bug type distribution
    bug_types = defaultdict(int)
    for p in all_pairs:
        bug_types[p["bug_type"]] += 1
    print(f"Bug types: {dict(sorted(bug_types.items(), key=lambda x: -x[1]))}")

    # Pair type distribution
    pair_types = defaultdict(int)
    for p in all_pairs:
        pair_types[p["pair_type"]] += 1
    print(f"Pair types: {dict(pair_types)}")

    # Save
    output_path = data_dir / "dpo_main_pairs.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for p in all_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"\nSaved: {output_path}")

    # Audit
    audit = {
        "total_pairs": len(all_pairs),
        "sources": dict(source_counts),
        "unique_tasks": len(all_tasks),
        "heldout_leakage": len(heldout_leak),
        "test_leakage": len(test_leak),
        "failure_types": dict(fail_types),
        "bug_types": dict(bug_types),
        "pair_types": dict(pair_types),
    }
    (report_dir / "dpo_main_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Audit: {report_dir / 'dpo_main_audit.json'}")


if __name__ == "__main__":
    main()

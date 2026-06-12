"""Mine DPO-v3 pairs with pair-level dedup (not task-level).

Key change: allow multiple pairs per task if pair_type/failure_type differs.
Each task can have up to 5 high-quality pairs.
"""
import json
from pathlib import Path
from collections import defaultdict


def load_rollout_traces(run_id, root):
    traces = {"success": {}, "failed": {}}
    rollouts_dir = root / "outputs" / "rollouts" / run_id
    for status in ["success", "failed"]:
        status_dir = rollouts_dir / status
        if not status_dir.exists():
            continue
        for task_dir in status_dir.iterdir():
            if not task_dir.is_dir():
                continue
            for trace_file in task_dir.glob("*.trace.json"):
                try:
                    t = json.loads(trace_file.read_text(encoding="utf-8"))
                    traces[status][task_dir.name] = t
                except:
                    pass
    return traces


def load_model_traces(model_name, root):
    traces = {}
    for subdir in ["success", "failed"]:
        d = root / "outputs" / "reports" / "full_metrics_new100" / model_name / subdir
        if d.exists():
            for f in d.glob("*.trace.json"):
                try:
                    t = json.loads(f.read_text(encoding="utf-8"))
                    traces[t["task_id"]] = t
                except:
                    pass
    return traces


def make_prompt(root, task_id):
    issue_path = root / "benchmark" / "tasks" / task_id / "issue.md"
    issue = issue_path.read_text(encoding="utf-8").strip() if issue_path.exists() else f"Fix bug in {task_id}"
    return f"Fix the bug:\n\n{issue}\n\nRespond with JSON: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"


def trace_to_text(trace, max_steps=10):
    parts = []
    for s in trace.get("steps", [])[:max_steps]:
        a = s.get("action", {})
        name = a.get("name", "")
        args = a.get("arguments", {})
        if name in ("edit_file", "run_tests", "submit_patch", "read_file"):
            parts.append(json.dumps({"action": name, "arguments": args}, ensure_ascii=False))
    return "\n".join(parts) if parts else '{"action": "submit_patch", "arguments": {}}'


def classify_failure(trace):
    if trace.get("success"):
        return "SUCCESS"
    has_edit = any(s.get("action", {}).get("name") == "edit_file" for s in trace.get("steps", []))
    if not has_edit:
        return "NO_EDIT"
    has_tests = any(s.get("action", {}).get("name") == "run_tests" for s in trace.get("steps", []))
    test_pass = any("passed" in str(s.get("observation", "")).lower() for s in trace.get("steps", []) if s.get("action", {}).get("name") == "run_tests")
    if has_tests and not test_pass:
        return "TEST_STILL_FAIL"
    return "OTHER"


def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    data_dir = root / "outputs" / "data"

    # Load task metadata
    task_meta = {}
    for p in tasks_root.iterdir():
        if p.is_dir() and p.name.startswith("bugfix_"):
            mp = p / "metadata.json"
            if mp.exists():
                task_meta[p.name] = json.loads(mp.read_text(encoding="utf-8"))

    # Load mimo traces
    print("Loading mimo traces...")
    mimo_new100 = load_rollout_traces("mimo_v25pro_new100", root)
    mimo_351_400 = load_rollout_traces("mimo_v25pro_351_400", root)
    print(f"  new100: {len(mimo_new100['success'])} success")
    print(f"  351-400: {len(mimo_351_400['success'])} success")

    # Load model failure traces
    print("Loading model failure traces...")
    model_traces = {}
    for model_name in ["3b_base", "3b_sft_v2", "3b_sft_v21_clean"]:
        traces = load_model_traces(model_name, root)
        model_traces[model_name] = traces
        failures = {tid: t for tid, t in traces.items() if not t.get("success")}
        print(f"  {model_name}: {len(failures)} failures")

    # Load existing pairs for pair-level dedup
    existing_path = data_dir / "dpo_patch_correctness_v2_pairs.jsonl"
    existing = [json.loads(l) for l in open(existing_path) if l.strip()] if existing_path.exists() else []

    # Build pair-level dedup key set
    def pair_key(p):
        return (p["task_id"], p.get("pair_type", ""), p.get("rejected_source", ""))

    existing_keys = set(pair_key(p) for p in existing)
    print(f"Existing pairs: {len(existing)}, unique keys: {len(existing_keys)}")

    # Track pairs per task (max 5)
    task_pair_count = defaultdict(int)
    for p in existing:
        task_pair_count[p["task_id"]] += 1
    MAX_PAIRS_PER_TASK = 5

    new_pairs = []
    counter = 0

    # === Source 1: new100 mimo success vs ALL model failures (same task) ===
    print("\n=== Mining new100 same-task pairs ===")
    for tid, mimo_trace in mimo_new100["success"].items():
        if task_pair_count[tid] >= MAX_PAIRS_PER_TASK:
            continue
        for model_name, traces in model_traces.items():
            if tid not in traces or traces[tid].get("success"):
                continue
            failure_type = classify_failure(traces[tid])
            # Pair-level dedup
            key = (tid, "same_task_mimo_vs_model", f"{model_name}_failure")
            if key in existing_keys:
                continue
            counter += 1
            meta = task_meta.get(tid, {})
            new_pairs.append({
                "pair_id": f"mimo_{counter:04d}",
                "task_id": tid,
                "bug_type": meta.get("bug_type", "unknown"),
                "difficulty": meta.get("difficulty", "unknown"),
                "pair_type": "same_task_mimo_vs_model",
                "chosen_source": "mimo_v25pro_success",
                "rejected_source": f"{model_name}_failure",
                "prompt": make_prompt(root, tid),
                "chosen": trace_to_text(mimo_trace),
                "rejected": trace_to_text(traces[tid]),
                "rejected_failure_type": failure_type,
                "split": "train",
            })
            existing_keys.add(key)
            task_pair_count[tid] += 1
            if task_pair_count[tid] >= MAX_PAIRS_PER_TASK:
                break

    print(f"  New pairs: {len([p for p in new_pairs if 'mimo' in p['pair_id']])}")

    # === Source 2: 351-400 mimo success vs scripted fix ===
    print("\n=== Mining 351-400 pairs ===")
    ind_count = 0
    for tid, mimo_trace in mimo_351_400["success"].items():
        if task_pair_count[tid] >= MAX_PAIRS_PER_TASK:
            continue
        meta_path = tasks_root / tid / "metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        scripted_fix = meta.get("scripted_fix", {})
        if not scripted_fix:
            continue

        key = (tid, "mimo_success_vs_scripted", "scripted_fix")
        if key in existing_keys:
            continue

        counter += 1
        new_pairs.append({
            "pair_id": f"ind_{counter:04d}",
            "task_id": tid,
            "bug_type": meta.get("bug_type", "unknown"),
            "difficulty": meta.get("difficulty", "unknown"),
            "pair_type": "mimo_success_vs_scripted",
            "chosen_source": "mimo_v25pro_success",
            "rejected_source": "scripted_fix",
            "prompt": make_prompt(root, tid),
            "chosen": trace_to_text(mimo_trace),
            "rejected": json.dumps({"action": "edit_file", "arguments": {"path": scripted_fix["path"], "old": scripted_fix["old"], "new": scripted_fix["new"]}}, ensure_ascii=False),
            "rejected_failure_type": "TEST_STILL_FAIL",
            "split": "train",
        })
        existing_keys.add(key)
        task_pair_count[tid] += 1
        ind_count += 1
    print(f"  New pairs: {ind_count}")

    # === Source 3: 351-400 mimo success vs model failures (if we have them) ===
    print("\n=== Mining 351-400 model failure pairs ===")
    model_351_count = 0
    # Check if we have model traces on 351-400
    for model_name in ["3b_base", "3b_sft_v2", "3b_sft_v21_clean"]:
        model_dir = root / "outputs" / "reports" / f"full_metrics_new100" / model_name / "failed"
        if not model_dir.exists():
            continue
        for trace_file in model_dir.glob("*.trace.json"):
            tid = trace_file.stem.replace(".trace", "")
            task_num = int(tid.split("_")[1]) if tid.startswith("bugfix_") else 0
            if task_num < 351 or task_num > 400:
                continue
            if tid not in mimo_351_400["success"]:
                continue
            if task_pair_count[tid] >= MAX_PAIRS_PER_TASK:
                continue

            key = (tid, "same_task_mimo_vs_model_351", f"{model_name}_failure")
            if key in existing_keys:
                continue

            try:
                fail_trace = json.loads(trace_file.read_text(encoding="utf-8"))
            except:
                continue

            counter += 1
            meta = task_meta.get(tid, {})
            new_pairs.append({
                "pair_id": f"m351_{counter:04d}",
                "task_id": tid,
                "bug_type": meta.get("bug_type", "unknown"),
                "difficulty": meta.get("difficulty", "unknown"),
                "pair_type": "same_task_mimo_vs_model_351",
                "chosen_source": "mimo_v25pro_success",
                "rejected_source": f"{model_name}_failure",
                "prompt": make_prompt(root, tid),
                "chosen": trace_to_text(mimo_351_400["success"][tid]),
                "rejected": trace_to_text(fail_trace),
                "rejected_failure_type": classify_failure(fail_trace),
                "split": "train",
            })
            existing_keys.add(key)
            task_pair_count[tid] += 1
            model_351_count += 1
    print(f"  New pairs: {model_351_count}")

    # Combine
    all_pairs = existing + new_pairs
    print(f"\n{'='*60}")
    print(f"TOTAL DPO-v3 PAIRS: {len(all_pairs)}")
    print(f"  Existing: {len(existing)}")
    print(f"  New: {len(new_pairs)}")

    # Stats
    ft = defaultdict(int)
    pt = defaultdict(int)
    for p in all_pairs:
        ft[p.get("rejected_failure_type", "")] += 1
        pt[p.get("pair_type", "")] += 1
    print(f"\nFailure types: {dict(sorted(ft.items(), key=lambda x: -x[1]))}")
    print(f"Pair types: {dict(sorted(pt.items(), key=lambda x: -x[1]))}")
    print(f"Unique tasks: {len(set(p['task_id'] for p in all_pairs))}")

    # Check if we meet targets
    wrong_patch = ft.get("TEST_STILL_FAIL", 0) + ft.get("WRONG_PATCH", 0)
    print(f"\nPatch correctness pairs: {wrong_patch} (target: 80-100)")
    print(f"FORMAT_ERROR: {ft.get('FORMAT_ERROR', 0)} (target: <=10)")

    # Save
    out_path = data_dir / "dpo_patch_correctness_v3_full.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for p in all_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"\nSaved: {out_path}")

    # Audit
    audit = {
        "total_pairs": len(all_pairs),
        "existing": len(existing),
        "new_pairs": len(new_pairs),
        "failure_types": dict(ft),
        "pair_types": dict(pt),
        "unique_tasks": len(set(p["task_id"] for p in all_pairs)),
        "max_pairs_per_task": MAX_PAIRS_PER_TASK,
        "dedup_method": "pair_level",
    }
    (data_dir / "dpo_v3_full_audit.json").write_text(json.dumps(audit, indent=2))
    print(f"Audit: {data_dir / 'dpo_v3_full_audit.json'}")


if __name__ == "__main__":
    main()

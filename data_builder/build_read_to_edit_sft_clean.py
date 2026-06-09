"""Build CLEAN read-to-edit transition SFT data (train-split only).

Changes from original:
1. Only uses train_tasks.txt traces (excludes test/val/heldout/unknown)
2. Adds provenance fields: source_trace_path, source_run_id, split, in_train_split
3. Removes samples with answer leakage (new_text in prompt/messages)
4. Outputs audit report
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def load_split_tasks(root: Path) -> dict[str, set[str]]:
    """Load train/val/test splits."""
    splits = {}
    splits_dir = root / "outputs" / "data" / "splits"
    for name in ["train_tasks", "val_tasks", "test_tasks"]:
        path = splits_dir / f"{name}.txt"
        if path.exists():
            splits[name.replace("_tasks", "")] = {
                l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()
            }
        else:
            splits[name.replace("_tasks", "")] = set()
    splits["heldout"] = {f"bugfix_{i}" for i in range(201, 251)}
    return splits


def load_task_issue(root: Path, task_id: str) -> str:
    issue_path = root / "benchmark" / "tasks" / task_id / "issue.md"
    if issue_path.exists():
        return issue_path.read_text(encoding="utf-8").strip()
    return ""


def load_target_files(root: Path, task_id: str) -> set[str]:
    meta_path = root / "benchmark" / "tasks" / task_id / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return set(meta.get("target_files", []))
    return set()


def check_answer_leakage(sample: dict) -> list[str]:
    """Check if completion's new_text or future actions appear in prompt/messages."""
    reasons = []
    comp = json.loads(sample["completion"])
    args = comp.get("arguments", {})
    new_text = args.get("new", "")
    msgs = sample.get("messages", [])

    # Check new_text in prompt-side messages
    if new_text and len(new_text) > 5:
        for m in msgs:
            if m.get("role") in ("system", "user", "tool"):
                if new_text in m.get("content", ""):
                    reasons.append("new_text_in_prompt")
                    break

    return reasons


def extract_read_to_edit_samples(trace: dict, root: Path, trace_path: str) -> list[dict]:
    """Extract read_file -> edit_file transitions from a trace."""
    samples = []
    steps = trace.get("steps", [])
    task_id = trace.get("task_id", "")
    target_files = load_target_files(root, task_id)
    issue = load_task_issue(root, task_id)

    for i in range(len(steps) - 1):
        current_step = steps[i]
        next_step = steps[i + 1]

        current_action = current_step.get("action", {})
        next_action = next_step.get("action", {})

        if (current_action.get("name") == "read_file" and
            next_action.get("name") == "edit_file"):

            read_path = current_action.get("arguments", {}).get("path", "")
            edit_path = next_action.get("arguments", {}).get("path", "")

            if read_path and edit_path and read_path == edit_path:
                if target_files and edit_path not in target_files:
                    continue

                messages = []
                messages.append({"role": "system", "content": "You are a coding assistant. Fix the bug in the codebase."})
                messages.append({"role": "user", "content": issue})

                for j in range(i + 1):
                    step = steps[j]
                    action = step.get("action", {})
                    assistant_msg = {
                        "thought": action.get("thought", ""),
                        "action": action.get("name", ""),
                        "arguments": action.get("arguments", {}),
                    }
                    messages.append({"role": "assistant", "content": json.dumps(assistant_msg, ensure_ascii=False)})
                    messages.append({"role": "tool", "content": step.get("observation", "")})

                completion = {
                    "thought": next_action.get("thought", "") or "The code has been inspected. Apply the minimal fix now.",
                    "action": "edit_file",
                    "arguments": next_action.get("arguments", {}),
                }

                sample = {
                    "sample_id": f"{task_id}_r2e_{i:03d}",
                    "task_id": task_id,
                    "step": i + 1,
                    "source": trace.get("model", "unknown"),
                    "bug_type": trace.get("metadata", {}).get("bug_type", ""),
                    "transition_type": "read_to_edit",
                    "prompt": "",
                    "completion": json.dumps(completion, ensure_ascii=False),
                    "action": "edit_file",
                    "messages": messages,
                    # Provenance fields
                    "source_trace_path": trace_path,
                    "source_run_id": trace.get("run_id", "unknown"),
                    "source_model": trace.get("model", "unknown"),
                }
                samples.append(sample)

    return samples


def main():
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir = root / "outputs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Load splits
    splits = load_split_tasks(root)
    train_tasks = splits["train"]
    print(f"Train split: {len(train_tasks)} tasks")
    print(f"Val split: {len(splits['val'])} tasks")
    print(f"Test split: {len(splits['test'])} tasks")
    print(f"Held-out: {len(splits['heldout'])} tasks")

    # Load all success traces with split filtering
    traces_dir = root / "outputs" / "rollouts"
    stats = {
        "total_traces_seen": 0,
        "traces_used": 0,
        "skipped_not_train": 0,
        "skipped_val": 0,
        "skipped_test": 0,
        "skipped_heldout": 0,
        "skipped_unknown": 0,
    }
    skip_detail = defaultdict(int)

    all_traces = []
    for run_dir in traces_dir.iterdir():
        if not run_dir.is_dir():
            continue
        success_dir = run_dir / "success"
        if not success_dir.exists():
            continue
        for task_dir in success_dir.iterdir():
            if not task_dir.is_dir():
                continue
            task_id = task_dir.name
            stats["total_traces_seen"] += 1

            # Split filtering
            if task_id in train_tasks:
                pass  # OK
            elif task_id in splits["val"]:
                stats["skipped_val"] += 1
                skip_detail[task_id] = "val"
                continue
            elif task_id in splits["test"]:
                stats["skipped_test"] += 1
                skip_detail[task_id] = "test"
                continue
            elif task_id in splits["heldout"]:
                stats["skipped_heldout"] += 1
                skip_detail[task_id] = "heldout"
                continue
            else:
                stats["skipped_unknown"] += 1
                skip_detail[task_id] = "unknown"
                continue

            for trace_file in task_dir.glob("*.trace.json"):
                try:
                    trace = json.loads(trace_file.read_text(encoding="utf-8"))
                    all_traces.append((trace, str(trace_file.relative_to(root))))
                    stats["traces_used"] += 1
                except Exception:
                    pass

    stats["skipped_not_train"] = stats["skipped_val"] + stats["skipped_test"] + stats["skipped_heldout"] + stats["skipped_unknown"]
    print(f"\nTrace loading stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Extract read-to-edit samples
    all_samples = []
    for trace, trace_path in all_traces:
        samples = extract_read_to_edit_samples(trace, root, trace_path)
        all_samples.extend(samples)
    print(f"\nExtracted {len(all_samples)} raw r2e samples")

    # Filter: parseable completion
    from evocode_orchard_lite.harness.action_parser import parse_action, ActionParseError
    clean_samples = []
    for sample in all_samples:
        try:
            parsed = parse_action(sample["completion"])
            if parsed.name == "edit_file":
                clean_samples.append(sample)
        except ActionParseError:
            pass
    print(f"Parseable samples: {len(clean_samples)}")

    # Answer leakage filter
    leakage_removed = 0
    leakage_reasons = defaultdict(int)
    final_samples = []
    for sample in clean_samples:
        reasons = check_answer_leakage(sample)
        if reasons:
            leakage_removed += 1
            for r in reasons:
                leakage_reasons[r] += 1
        else:
            # Add split field
            task_id = sample["task_id"]
            sample["split"] = "train"
            sample["in_train_split"] = True
            final_samples.append(sample)

    print(f"\nLeakage filter:")
    print(f"  Removed: {leakage_removed}")
    for r, c in leakage_reasons.items():
        print(f"    {r}: {c}")
    print(f"  Final clean samples: {len(final_samples)}")

    # Save clean data
    output_path = output_dir / "read_to_edit_step_sft_clean_train_only.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for sample in final_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"\nSaved: {output_path}")

    # Generate audit report
    task_ids = set(s["task_id"] for s in final_samples)
    bug_types = defaultdict(int)
    models = defaultdict(int)
    for s in final_samples:
        bug_types[s.get("bug_type", "unknown")] += 1
        models[s.get("source_model", "unknown")] += 1

    # Verify no contamination
    assert len(task_ids & splits["test"]) == 0, "FAIL: test split contamination!"
    assert len(task_ids & splits["val"]) == 0, "FAIL: val split contamination!"
    assert len(task_ids & splits["heldout"]) == 0, "FAIL: heldout contamination!"
    print("\nAll contamination checks PASSED")

    audit = {
        "total_traces_seen": stats["total_traces_seen"],
        "traces_used": stats["traces_used"],
        "skipped_not_train": stats["skipped_not_train"],
        "skipped_val": stats["skipped_val"],
        "skipped_test": stats["skipped_test"],
        "skipped_heldout": stats["skipped_heldout"],
        "skipped_unknown": stats["skipped_unknown"],
        "raw_samples": len(all_samples),
        "parseable_samples": len(clean_samples),
        "leakage_removed": leakage_removed,
        "final_samples": len(final_samples),
        "unique_tasks": len(task_ids),
        "test_overlap": len(task_ids & splits["test"]),
        "val_overlap": len(task_ids & splits["val"]),
        "heldout_overlap": len(task_ids & splits["heldout"]),
        "bug_type_distribution": dict(bug_types),
        "model_distribution": dict(models),
        "avg_samples_per_task": round(len(final_samples) / max(len(task_ids), 1), 1),
    }
    audit_path = report_dir / "read_to_edit_clean_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Audit report: {audit_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"CLEAN R2E DATA SUMMARY")
    print(f"{'='*60}")
    print(f"Samples: {len(final_samples)}")
    print(f"Tasks: {len(task_ids)}")
    print(f"Avg per task: {audit['avg_samples_per_task']}")
    print(f"Test overlap: {audit['test_overlap']}")
    print(f"Val overlap: {audit['val_overlap']}")
    print(f"Held-out overlap: {audit['heldout_overlap']}")
    print(f"Leakage removed: {leakage_removed}")


if __name__ == "__main__":
    main()

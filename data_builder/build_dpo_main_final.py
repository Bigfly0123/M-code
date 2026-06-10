"""Build final DPO-main dataset with expanded WRONG_PATCH pairs."""
import json
from pathlib import Path
from collections import defaultdict

root = Path(".")
data_dir = root / "outputs" / "data"
tasks_root = root / "benchmark" / "tasks"
new100_dir = root / "outputs" / "reports" / "full_metrics_new100"

train_tasks = set(l.strip() for l in open(data_dir / "splits" / "train_tasks.txt") if l.strip())

task_meta = {}
for p in tasks_root.iterdir():
    if p.is_dir() and p.name.startswith("bugfix_"):
        mp = p / "metadata.json"
        if mp.exists():
            task_meta[p.name] = json.loads(mp.read_text())


def load_traces(model_name):
    traces = {}
    for sub in ["success", "failed"]:
        d = new100_dir / model_name / sub
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    t = json.loads(f.read_text())
                    traces[t["task_id"]] = t
                except:
                    pass
    return traces


v21 = load_traces("3b_sft_v21_clean")
b7 = load_traces("7b_base")
b3 = load_traces("3b_base")
v2 = load_traces("3b_sft_v2")

counter = 0


def make_prompt(tid):
    ip = tasks_root / tid / "issue.md"
    issue = ip.read_text().strip() if ip.exists() else f"Fix bug in {tid}"
    return f"Fix the bug:\n\n{issue}\n\nRespond with JSON: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"


def actions_text(trace, max_steps=10):
    parts = []
    for s in trace.get("steps", [])[:max_steps]:
        a = s.get("action", {})
        name = a.get("name", "")
        args = a.get("arguments", {})
        if name in ("edit_file", "run_tests", "submit_patch", "read_file"):
            parts.append(json.dumps({"action": name, "arguments": args}, ensure_ascii=False))
    return "\n".join(parts) if parts else '{"action": "submit_patch", "arguments": {}}'


def classify(trace):
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


# Load existing pairs
existing = [json.loads(l) for l in open(data_dir / "dpo_main_pairs_expanded.jsonl") if l.strip()]
existing_tasks = set(p["task_id"] for p in existing)
print(f"Existing: {len(existing)} pairs")

new_pairs = []

# === Generate more WRONG_PATCH pairs ===
# Strategy: 7B success vs v2.1-clean failure (same bug_type, multiple per type)
b7_succ_by_type = defaultdict(list)
for tid, t in b7.items():
    if t.get("success"):
        b7_succ_by_type[task_meta.get(tid, {}).get("bug_type", "unknown")].append(tid)

v21_fail_by_type = defaultdict(list)
for tid, t in v21.items():
    if not t.get("success"):
        v21_fail_by_type[task_meta.get(tid, {}).get("bug_type", "unknown")].append(tid)

count = 0
for bt, fail_tids in v21_fail_by_type.items():
    succ_tids = b7_succ_by_type.get(bt, [])
    if not succ_tids:
        continue
    for i, fail_tid in enumerate(fail_tids):
        if fail_tid in existing_tasks:
            continue
        chosen_tid = succ_tids[i % len(succ_tids)]
        counter += 1
        meta = task_meta.get(fail_tid, {})
        new_pairs.append({
            "pair_id": f"wrong_patch_{counter}",
            "task_id": fail_tid,
            "bug_type": bt,
            "difficulty": meta.get("difficulty", "unknown"),
            "pair_type": "wrong_patch_7b_vs_v21",
            "chosen_source": f"7b_{chosen_tid}",
            "rejected_source": "v21_failure",
            "prompt": make_prompt(fail_tid),
            "chosen": actions_text(b7[chosen_tid]),
            "rejected": actions_text(v21[fail_tid]),
            "rejected_failure_type": classify(v21[fail_tid]),
            "split": "train",
        })
        existing_tasks.add(fail_tid)
        count += 1
print(f"New WRONG_PATCH pairs: {count}")

# === Generate test-feedback pairs ===
# v2.1-clean success vs 3B/v2 failure where both tried edit
count2 = 0
for tid, base_t in b3.items():
    if base_t.get("success") or tid in existing_tasks:
        continue
    if tid not in v21 or not v21[tid].get("success"):
        continue
    # Only if base model tried to edit (not NO_EDIT)
    if classify(base_t) == "NO_EDIT":
        continue
    counter += 1
    meta = task_meta.get(tid, {})
    new_pairs.append({
        "pair_id": f"test_feedback_{counter}",
        "task_id": tid,
        "bug_type": meta.get("bug_type", "unknown"),
        "difficulty": meta.get("difficulty", "unknown"),
        "pair_type": "test_feedback_v21_vs_base",
        "chosen_source": "v21_success",
        "rejected_source": "3b_base_wrong_patch",
        "prompt": make_prompt(tid),
        "chosen": actions_text(v21[tid]),
        "rejected": actions_text(base_t),
        "rejected_failure_type": "TEST_STILL_FAIL",
        "split": "train",
    })
    existing_tasks.add(tid)
    count2 += 1
print(f"New test-feedback pairs: {count2}")

# Combine all
all_pairs = existing + new_pairs
print(f"\nTotal DPO-main pairs: {len(all_pairs)}")

# Stats
ft = defaultdict(int)
for p in all_pairs:
    ft[p.get("rejected_failure_type", "UNKNOWN")] += 1
print(f"Failure types: {dict(sorted(ft.items(), key=lambda x: -x[1]))}")

bt = defaultdict(int)
for p in all_pairs:
    bt[p.get("bug_type", "unknown")] += 1
print(f"Top bug types: {dict(sorted(bt.items(), key=lambda x: -x[1])[:10])}")

# Save
out = data_dir / "dpo_main_patch_stable.jsonl"
with out.open("w", encoding="utf-8") as f:
    for p in all_pairs:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")
print(f"\nSaved: {out}")

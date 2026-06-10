"""Expand DPO pairs to 200+ with relaxed dedup and more sources."""
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

# Load rejected errors (train-only)
rej_errors = [json.loads(l) for l in open(data_dir / "dpo_rejected_errors.jsonl") if l.strip()]
rej_train = [r for r in rej_errors if r.get("task_id", "") in train_tasks]

# Load HQ success traces
hq_path = data_dir / "high_quality_success_traces.jsonl"
hq_traces = {}
if hq_path.exists():
    for l in open(hq_path):
        if l.strip():
            t = json.loads(l)
            tid = t.get("task_id", "")
            if tid in train_tasks and tid not in hq_traces:
                hq_traces[tid] = t

# Load existing pairs
existing = [json.loads(l) for l in open(data_dir / "dpo_main_pairs.jsonl") if l.strip()]
existing_tasks = set(p["task_id"] for p in existing)
print(f"Existing: {len(existing)} pairs, {len(existing_tasks)} tasks")

new_pairs = []
counter = 1000


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


def make_pair(pair_type, tid, chosen_trace, rejected_trace, chosen_src, rejected_src):
    global counter
    counter += 1
    meta = task_meta.get(tid, {})
    return {
        "pair_id": f"{pair_type}_{counter}",
        "task_id": tid,
        "bug_type": meta.get("bug_type", "unknown"),
        "difficulty": meta.get("difficulty", "unknown"),
        "pair_type": pair_type,
        "chosen_source": chosen_src,
        "rejected_source": rejected_src,
        "prompt": make_prompt(tid),
        "chosen": actions_text(chosen_trace),
        "rejected": actions_text(rejected_trace),
        "rejected_failure_type": classify(rejected_trace),
        "split": "train",
    }


# === Source A: same-bug-type relaxed (multiple pairs per type) ===
v21_fail_by_type = defaultdict(list)
for tid, t in v21.items():
    if not t.get("success"):
        v21_fail_by_type[task_meta.get(tid, {}).get("bug_type", "unknown")].append(tid)

b7_succ_by_type = defaultdict(list)
for tid, t in b7.items():
    if t.get("success"):
        b7_succ_by_type[task_meta.get(tid, {}).get("bug_type", "unknown")].append(tid)

count_a = 0
for bt, fail_tids in v21_fail_by_type.items():
    succ_tids = b7_succ_by_type.get(bt, [])
    if not succ_tids:
        continue
    for i, fail_tid in enumerate(fail_tids):
        if fail_tid in existing_tasks:
            continue
        chosen_tid = succ_tids[i % len(succ_tids)]
        new_pairs.append(make_pair("bugtype_relax", fail_tid, b7[chosen_tid], v21[fail_tid], f"7b_{chosen_tid}", "v21_failure"))
        existing_tasks.add(fail_tid)
        count_a += 1
print(f"Source A (bug-type relaxed): {count_a}")

# === Source B: rejected_errors paired with success ===
count_b = 0
for r in rej_train:
    tid = r.get("task_id", "")
    if tid in existing_tasks:
        continue
    chosen_trace = None
    chosen_src = ""
    if tid in hq_traces:
        chosen_trace = hq_traces[tid]
        chosen_src = "hq_success"
    elif tid in v21 and v21[tid].get("success"):
        chosen_trace = v21[tid]
        chosen_src = "v21_success"
    elif tid in b7 and b7[tid].get("success"):
        chosen_trace = b7[tid]
        chosen_src = "7b_success"
    else:
        bt = task_meta.get(tid, {}).get("bug_type", "unknown")
        if bt in b7_succ_by_type and b7_succ_by_type[bt]:
            chosen_trace = b7[b7_succ_by_type[bt][0]]
            chosen_src = f"7b_bugtype_{bt}"
    if not chosen_trace:
        continue

    # Build rejected from messages
    msgs = r.get("messages", [])
    rej_parts = []
    for m in msgs:
        if m.get("role") == "assistant":
            try:
                a = json.loads(m.get("content", "{}"))
                rej_parts.append(json.dumps({"action": a.get("action", ""), "arguments": a.get("arguments", {})}, ensure_ascii=False))
            except:
                pass
    rej_text = "\n".join(rej_parts) if rej_parts else '{"action": "read_file", "arguments": {"path": "bug.py"}}'

    # Create a mock rejected trace for classify
    mock_rej = {"success": False, "steps": [{"action": {"name": "read_file", "arguments": {"path": "x"}}, "observation": ""}]}
    counter += 1
    meta = task_meta.get(tid, {})
    new_pairs.append({
        "pair_id": f"rej_err_{counter}",
        "task_id": tid,
        "bug_type": meta.get("bug_type", "unknown"),
        "difficulty": meta.get("difficulty", "unknown"),
        "pair_type": "rejected_error_vs_success",
        "chosen_source": chosen_src,
        "rejected_source": "rejected_error_trace",
        "prompt": make_prompt(tid),
        "chosen": actions_text(chosen_trace),
        "rejected": rej_text,
        "rejected_failure_type": "FORMAT_ERROR",
        "split": "train",
    })
    existing_tasks.add(tid)
    count_b += 1
print(f"Source B (rejected errors): {count_b}")

# === Source C: v2.1-clean success vs 3B Base failure (relax) ===
count_c = 0
for tid, base_t in b3.items():
    if base_t.get("success") or tid in existing_tasks:
        continue
    if tid in v21 and v21[tid].get("success"):
        new_pairs.append(make_pair("v21_vs_base", tid, v21[tid], base_t, "v21_success", "3b_base_failure"))
        existing_tasks.add(tid)
        count_c += 1
print(f"Source C (base failures): {count_c}")

# === Source D: v2.1-clean success vs v2 failure (relax) ===
count_d = 0
for tid, v2_t in v2.items():
    if v2_t.get("success") or tid in existing_tasks:
        continue
    if tid in v21 and v21[tid].get("success"):
        new_pairs.append(make_pair("v21_vs_v2", tid, v21[tid], v2_t, "v21_success", "v2_failure"))
        existing_tasks.add(tid)
        count_d += 1
print(f"Source D (v2 failures): {count_d}")

# === Source E: 7B success vs v2.1-clean failure (same task, relax) ===
count_e = 0
for tid, v21_t in v21.items():
    if v21_t.get("success") or tid in existing_tasks:
        continue
    if tid in b7 and b7[tid].get("success"):
        new_pairs.append(make_pair("7b_vs_v21", tid, b7[tid], v21_t, "7b_success", "v21_failure"))
        existing_tasks.add(tid)
        count_e += 1
print(f"Source E (7B vs v2.1): {count_e}")

# === Source F: v2 success vs v2.1-clean failure (same task) ===
count_f = 0
for tid, v21_t in v21.items():
    if v21_t.get("success") or tid in existing_tasks:
        continue
    if tid in v2 and v2[tid].get("success"):
        new_pairs.append(make_pair("v2_vs_v21", tid, v2[tid], v21_t, "v2_success", "v21_failure"))
        existing_tasks.add(tid)
        count_f += 1
print(f"Source F (v2 vs v2.1): {count_f}")

# Combine
all_pairs = existing + new_pairs

print(f"\n{'='*60}")
print(f"TOTAL: {len(all_pairs)} pairs")
print(f"  Existing: {len(existing)}")
print(f"  New: {len(new_pairs)}")
print(f"  Unique tasks: {len(set(p['task_id'] for p in all_pairs))}")

ft = defaultdict(int)
for p in all_pairs:
    ft[p["rejected_failure_type"]] += 1
print(f"  Failure types: {dict(ft)}")

pt = defaultdict(int)
for p in all_pairs:
    pt[p["pair_type"]] += 1
print(f"  Pair types: {dict(pt)}")

# Save
out = data_dir / "dpo_main_pairs_expanded.jsonl"
with out.open("w", encoding="utf-8") as f:
    for p in all_pairs:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")
print(f"\nSaved: {out}")

"""Build DPO preference pairs from success and failure traces.

Generates:
- dpo_pairs_v2.jsonl - chosen/rejected pairs for DPO training

Pair types:
1. Success vs NO_EDIT failure (loop)
2. Success vs TEST_FAIL failure
3. Same task success vs failure
"""
from __future__ import annotations

import json
from pathlib import Path


def load_traces(trace_dir: Path) -> list[dict]:
    """Load all traces from directory."""
    traces = []
    for trace_file in trace_dir.rglob("*.trace.json"):
        try:
            trace = json.loads(trace_file.read_text())
            traces.append(trace)
        except Exception:
            pass
    return traces


def build_sft_sample(trace: dict) -> dict:
    """Convert trace to SFT format."""
    messages = []
    messages.append({"role": "system", "content": "You are a coding assistant. Fix the bug in the codebase."})
    
    # Add issue if available
    issue = trace.get("issue", "")
    messages.append({"role": "user", "content": issue})
    
    # Add steps
    for step in trace.get("steps", []):
        action = step.get("action", {})
        assistant_msg = {
            "thought": action.get("thought", ""),
            "action": action.get("name", ""),
            "arguments": action.get("arguments", {}),
        }
        messages.append({"role": "assistant", "content": json.dumps(assistant_msg, ensure_ascii=False)})
        messages.append({"role": "tool", "content": step.get("observation", "")})
    
    return {
        "task_id": trace.get("task_id"),
        "messages": messages,
        "metadata": {
            "success": trace.get("success"),
            "num_steps": len(trace.get("steps", [])),
        }
    }


def main():
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load success traces
    success_dir = root / "outputs" / "reports" / "eval_3b_step_sft_v2"
    success_traces = []
    for trace_file in success_dir.rglob("*.trace.json"):
        try:
            trace = json.loads(trace_file.read_text())
            if trace.get("success"):
                success_traces.append(trace)
        except Exception:
            pass
    
    # Load failure traces from eval_3b_base (has more failures)
    failure_dir = root / "outputs" / "reports" / "eval_3b_base"
    failure_traces = []
    for trace_file in failure_dir.rglob("*.trace.json"):
        try:
            trace = json.loads(trace_file.read_text())
            if not trace.get("success"):
                failure_traces.append(trace)
        except Exception:
            pass
    
    # Also load from eval_3b_step_sft_v2
    for trace_file in success_dir.rglob("*.trace.json"):
        try:
            trace = json.loads(trace_file.read_text())
            if not trace.get("success"):
                failure_traces.append(trace)
        except Exception:
            pass
    
    print(f"Success traces: {len(success_traces)}")
    print(f"Failure traces: {len(failure_traces)}")
    
    # Group by task_id
    success_by_task = {}
    for trace in success_traces:
        task_id = trace.get("task_id")
        if task_id not in success_by_task:
            success_by_task[task_id] = []
        success_by_task[task_id].append(trace)
    
    failure_by_task = {}
    for trace in failure_traces:
        task_id = trace.get("task_id")
        if task_id not in failure_by_task:
            failure_by_task[task_id] = []
        failure_by_task[task_id].append(trace)
    
    # Build DPO pairs
    dpo_pairs = []
    
    # Same task pairs
    for task_id in set(success_by_task.keys()) & set(failure_by_task.keys()):
        success_trace = success_by_task[task_id][0]
        failure_trace = failure_by_task[task_id][0]
        
        chosen = build_sft_sample(success_trace)
        rejected = build_sft_sample(failure_trace)
        
        # Determine failure type
        failure_type = "UNKNOWN"
        steps = failure_trace.get("steps", [])
        action_sequence = [s.get("action", {}).get("name", "") for s in steps]
        
        # Check for loop
        for i in range(len(action_sequence) - 2):
            if action_sequence[i] == action_sequence[i+1] == action_sequence[i+2] and action_sequence[i]:
                failure_type = "LOOP"
                break
        
        if failure_type == "UNKNOWN":
            has_edit = any(a == "edit_file" for a in action_sequence)
            has_test = any(a == "run_tests" for a in action_sequence)
            if not has_edit:
                failure_type = "NO_EDIT"
            elif not has_test:
                failure_type = "NO_TEST"
            else:
                failure_type = "TEST_STILL_FAIL"
        
        dpo_pairs.append({
            "pair_id": f"{task_id}_same_task",
            "task_id": task_id,
            "pair_type": "same_task",
            "chosen": chosen,
            "rejected": rejected,
            "rejected_failure_type": failure_type,
        })
    
    # Cross-task pairs (if not enough same-task pairs)
    if len(dpo_pairs) < 50:
        success_list = list(success_by_task.values())
        failure_list = list(failure_by_task.values())
        
        for i in range(min(len(success_list), len(failure_list), 50 - len(dpo_pairs))):
            success_trace = success_list[i][0]
            failure_trace = failure_list[i][0]
            
            # Skip if same task (already added)
            if success_trace.get("task_id") == failure_trace.get("task_id"):
                continue
            
            chosen = build_sft_sample(success_trace)
            rejected = build_sft_sample(failure_trace)
            
            dpo_pairs.append({
                "pair_id": f"{success_trace.get('task_id')}_{failure_trace.get('task_id')}_cross",
                "task_id": success_trace.get("task_id"),
                "pair_type": "cross_task",
                "chosen": chosen,
                "rejected": rejected,
                "rejected_failure_type": "CROSS_TASK",
            })
    
    # Save
    output_path = output_dir / "dpo_pairs_v2.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for pair in dpo_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    
    print(f"\nGenerated {len(dpo_pairs)} DPO pairs")
    print(f"Saved to: {output_path}")
    
    # Stats
    pair_types = {}
    failure_types = {}
    for pair in dpo_pairs:
        pt = pair.get("pair_type", "unknown")
        ft = pair.get("rejected_failure_type", "unknown")
        pair_types[pt] = pair_types.get(pt, 0) + 1
        failure_types[ft] = failure_types.get(ft, 0) + 1
    
    print(f"\nPair types: {pair_types}")
    print(f"Failure types: {failure_types}")


if __name__ == "__main__":
    main()

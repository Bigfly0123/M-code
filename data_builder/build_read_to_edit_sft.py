"""Build read-to-edit transition SFT data.

Extracts read_file -> edit_file transitions from success traces.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_task_issue(root: Path, task_id: str) -> str:
    """Load issue text from task directory."""
    issue_path = root / "benchmark" / "tasks" / task_id / "issue.md"
    if issue_path.exists():
        return issue_path.read_text(encoding="utf-8").strip()
    return ""


def load_target_files(root: Path, task_id: str) -> set[str]:
    """Load target files from task metadata."""
    meta_path = root / "benchmark" / "tasks" / task_id / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return set(meta.get("target_files", []))
    return set()


def extract_read_to_edit_samples(trace: dict, root: Path) -> list[dict]:
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
        
        # Check if current is read_file and next is edit_file
        if (current_action.get("name") == "read_file" and 
            next_action.get("name") == "edit_file"):
            
            # Check if edit targets the file that was read
            read_path = current_action.get("arguments", {}).get("path", "")
            edit_path = next_action.get("arguments", {}).get("path", "")
            
            # Only keep if editing the file that was read
            if read_path and edit_path and read_path == edit_path:
                # Check if it's a target file
                if target_files and edit_path not in target_files:
                    continue
                
                # Build prompt: issue + history up to read_file
                messages = []
                messages.append({"role": "system", "content": "You are a coding assistant. Fix the bug in the codebase."})
                messages.append({"role": "user", "content": issue})
                
                # Add history up to current step
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
                
                # Build completion: edit_file action
                completion = {
                    "thought": next_action.get("thought", "") or "The code has been inspected. Apply the minimal fix now.",
                    "action": "edit_file",
                    "arguments": next_action.get("arguments", {}),
                }
                
                sample = {
                    "sample_id": f"{task_id}_read_to_edit_{i:03d}",
                    "task_id": task_id,
                    "step": i + 1,
                    "source": trace.get("model", "unknown"),
                    "bug_type": trace.get("metadata", {}).get("bug_type", ""),
                    "transition_type": "read_to_edit",
                    "prompt": "",  # Will be formatted during training
                    "completion": json.dumps(completion, ensure_ascii=False),
                    "action": "edit_file",
                    "messages": messages,
                }
                samples.append(sample)
    
    return samples


def main():
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load high-quality success traces
    traces_dir = root / "outputs" / "rollouts"
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
            for trace_file in task_dir.glob("*.trace.json"):
                try:
                    trace = json.loads(trace_file.read_text(encoding="utf-8"))
                    all_traces.append(trace)
                except Exception:
                    pass
    
    print(f"Loaded {len(all_traces)} success traces")
    
    # Extract read-to-edit samples
    all_samples = []
    for trace in all_traces:
        samples = extract_read_to_edit_samples(trace, root)
        all_samples.extend(samples)
    
    print(f"Extracted {len(all_samples)} read-to-edit samples")
    
    # Filter: only keep samples with valid completion
    from evocode_orchard_lite.harness.action_parser import parse_action, ActionParseError
    
    clean_samples = []
    for sample in all_samples:
        try:
            parsed = parse_action(sample["completion"])
            if parsed.name == "edit_file":
                clean_samples.append(sample)
        except ActionParseError:
            pass
    
    print(f"Clean samples (parseable): {len(clean_samples)}")
    
    # Save
    output_path = output_dir / "read_to_edit_step_sft.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for sample in clean_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"Saved: {output_path}")
    
    # Stats
    task_ids = set(s["task_id"] for s in clean_samples)
    bug_types = {}
    for s in clean_samples:
        bt = s.get("bug_type", "unknown")
        bug_types[bt] = bug_types.get(bt, 0) + 1
    
    print(f"\nUnique tasks: {len(task_ids)}")
    print(f"Bug type distribution:")
    for bt, count in sorted(bug_types.items(), key=lambda x: -x[1])[:10]:
        print(f"  {bt}: {count}")


if __name__ == "__main__":
    main()

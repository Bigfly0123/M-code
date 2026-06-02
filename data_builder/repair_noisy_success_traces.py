"""Repair noisy success traces by removing bad steps and keeping good ones.

Generates:
  - sft_clean_repaired.jsonl (purified traces)
  - dpo_rejected_errors.jsonl (error steps for DPO rejected)

Usage:
    python -m evocode_orchard_lite.data_builder.repair_noisy_success_traces
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BAD_PATTERNS = [
    "Missing required argument",
    "Unknown tool",
    "Response is not valid JSON",
    "Path escapes workspace",
    "Old text not found",
    "Format error after retries",
]

ALLOWED_ACTIONS = {
    "list_files",
    "read_file",
    "search_code",
    "edit_file",
    "run_tests",
    "git_diff",
    "submit_patch",
}


def is_bad_step(step: dict) -> tuple[bool, str | None]:
    """Check if a step has errors. Returns (is_bad, error_type)."""
    observation = step.get("observation", "")
    action = step.get("action", {})
    action_name = action.get("name", "")
    
    # Check for bad patterns
    for pattern in BAD_PATTERNS:
        if pattern in observation:
            return True, f"bad_pattern:{pattern}"
    
    # Check if action is valid
    if action_name not in ALLOWED_ACTIONS:
        return True, f"invalid_action:{action_name}"
    
    # Check for missing required arguments
    arguments = action.get("arguments", {})
    if action_name == "edit_file":
        if not arguments.get("path"):
            return True, "missing_arg:path"
        if not arguments.get("old") and not arguments.get("new"):
            return True, "missing_arg:old_or_new"
    
    return False, None


def repair_trace(trace: dict) -> tuple[dict | None, list[dict]]:
    """Repair a trace by removing bad steps.
    
    Returns:
        - repaired trace (or None if can't be repaired)
        - list of error steps for DPO rejected
    """
    steps = trace.get("steps", [])
    if not steps:
        return None, []
    
    # Split into good and bad steps
    good_steps = []
    bad_steps = []
    
    for step in steps:
        is_bad, error_type = is_bad_step(step)
        if is_bad:
            step["_error_type"] = error_type
            bad_steps.append(step)
        else:
            good_steps.append(step)
    
    # If no bad steps, return original trace
    if not bad_steps:
        return trace, []
    
    # If no good steps, can't repair
    if not good_steps:
        return None, bad_steps
    
    # Check if repaired trace has required elements
    has_run_tests = any(s.get("action", {}).get("name") == "run_tests" for s in good_steps)
    has_edit_file = any(s.get("action", {}).get("name") == "edit_file" for s in good_steps)
    has_submit_patch = any(s.get("action", {}).get("name") == "submit_patch" for s in good_steps)
    
    if not (has_run_tests and has_edit_file and has_submit_patch):
        return None, bad_steps
    
    # Renumber steps
    for i, step in enumerate(good_steps):
        step["step"] = i + 1
    
    # Create repaired trace
    repaired = trace.copy()
    repaired["steps"] = good_steps
    repaired["_repaired"] = True
    repaired["_original_steps"] = len(steps)
    repaired["_removed_steps"] = len(bad_steps)
    
    return repaired, bad_steps


def build_sft_sample(trace: dict) -> dict:
    """Convert trace to SFT training sample."""
    messages = []
    
    # System message
    messages.append({
        "role": "system",
        "content": "You are a coding assistant. Fix the bug in the codebase."
    })
    
    # User message (issue)
    issue = trace.get("issue", "")
    messages.append({
        "role": "user",
        "content": issue
    })
    
    # Assistant actions
    for step in trace.get("steps", []):
        action = step.get("action", {})
        
        # Assistant message
        assistant_msg = {
            "thought": action.get("thought", ""),
            "action": action.get("name", ""),
            "arguments": action.get("arguments", {}),
        }
        messages.append({
            "role": "assistant",
            "content": json.dumps(assistant_msg, ensure_ascii=False)
        })
        
        # Tool response
        messages.append({
            "role": "tool",
            "content": step.get("observation", "")
        })
    
    return {
        "task_id": trace.get("task_id"),
        "run_id": trace.get("run_id"),
        "rollout_id": trace.get("rollout_id"),
        "model": trace.get("model"),
        "messages": messages,
        "metadata": {
            "success": trace.get("success"),
            "reward": trace.get("reward"),
            "num_steps": len(trace.get("steps", [])),
            "repaired": trace.get("_repaired", False),
        }
    }


def build_dpo_rejected_sample(step: dict, trace: dict) -> dict:
    """Convert an error step to DPO rejected sample."""
    action = step.get("action", {})
    
    messages = [
        {"role": "system", "content": "You are a coding assistant. Fix the bug in the codebase."},
        {"role": "user", "content": trace.get("issue", "")},
    ]
    
    # Add the error action
    assistant_msg = {
        "thought": action.get("thought", ""),
        "action": action.get("name", ""),
        "arguments": action.get("arguments", {}),
    }
    messages.append({
        "role": "assistant",
        "content": json.dumps(assistant_msg, ensure_ascii=False)
    })
    
    # Add the error observation
    messages.append({
        "role": "tool",
        "content": step.get("observation", "")
    })
    
    return {
        "task_id": trace.get("task_id"),
        "run_id": trace.get("run_id"),
        "rollout_id": trace.get("rollout_id"),
        "model": trace.get("model"),
        "messages": messages,
        "metadata": {
            "source": "dpo_rejected_error",
            "error_type": step.get("_error_type"),
            "action_name": action.get("name"),
        }
    }


def load_noisy_traces(root: Path) -> list[dict]:
    """Load traces that have 'Missing required argument' errors."""
    rollouts_dir = root / "outputs" / "rollouts"
    noisy_traces = []
    
    for run_dir in sorted(rollouts_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        success_dir = run_dir / "success"
        if not success_dir.exists():
            continue
        for task_dir in sorted(success_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            for trace_file in sorted(task_dir.glob("*.trace.json")):
                try:
                    trace = json.loads(trace_file.read_text(encoding="utf-8"))
                    steps = trace.get("steps", [])
                    
                    # Check if has Missing required argument
                    has_issue = False
                    for step in steps:
                        obs = step.get("observation", "")
                        if "Missing required argument" in obs:
                            has_issue = True
                            break
                    
                    if has_issue:
                        trace["_source_file"] = str(trace_file)
                        noisy_traces.append(trace)
                except Exception as e:
                    print(f"Warning: Failed to load {trace_file}: {e}")
    
    return noisy_traces


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load noisy traces
    print("Loading noisy traces...")
    noisy_traces = load_noisy_traces(root)
    print(f"Loaded {len(noisy_traces)} noisy traces")
    
    # Repair traces
    print("\nRepairing traces...")
    repaired_traces = []
    all_bad_steps = []
    
    for trace in noisy_traces:
        repaired, bad_steps = repair_trace(trace)
        if repaired:
            repaired_traces.append(repaired)
        all_bad_steps.extend([(step, trace) for step in bad_steps])
    
    print(f"Repaired: {len(repaired_traces)}")
    print(f"Bad steps: {len(all_bad_steps)}")
    
    # Build SFT samples from repaired traces
    print("\nBuilding SFT samples from repaired traces...")
    sft_repaired = []
    for trace in repaired_traces:
        sample = build_sft_sample(trace)
        sft_repaired.append(sample)
    
    print(f"SFT repaired: {len(sft_repaired)}")
    
    # Save SFT repaired
    sft_path = output_dir / "sft_clean_repaired.jsonl"
    with sft_path.open("w", encoding="utf-8") as f:
        for sample in sft_repaired:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"Saved: {sft_path}")
    
    # Build DPO rejected samples from bad steps
    print("\nBuilding DPO rejected samples...")
    dpo_rejected = []
    for step, trace in all_bad_steps:
        sample = build_dpo_rejected_sample(step, trace)
        dpo_rejected.append(sample)
    
    print(f"DPO rejected: {len(dpo_rejected)}")
    
    # Save DPO rejected
    dpo_path = output_dir / "dpo_rejected_errors.jsonl"
    with dpo_path.open("w", encoding="utf-8") as f:
        for sample in dpo_rejected:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"Saved: {dpo_path}")
    
    # Save stats
    stats = {
        "noisy_traces": len(noisy_traces),
        "repaired_traces": len(repaired_traces),
        "bad_steps": len(all_bad_steps),
        "sft_repaired": len(sft_repaired),
        "dpo_rejected": len(dpo_rejected),
    }
    
    stats_path = output_dir / "repair_stats.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved stats: {stats_path}")
    
    # Summary
    print("\n" + "=" * 50)
    print("REPAIR SUMMARY")
    print("=" * 50)
    print(f"Noisy traces: {len(noisy_traces)}")
    print(f"Repaired traces: {len(repaired_traces)}")
    print(f"SFT repaired: {len(sft_repaired)}")
    print(f"DPO rejected: {len(dpo_rejected)}")
    
    # Load existing clean SFT and combine
    existing_sft_path = output_dir / "sft_clean.jsonl"
    if existing_sft_path.exists():
        existing_sft = []
        for line in existing_sft_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_sft.append(json.loads(line))
        
        combined = existing_sft + sft_repaired
        combined_path = output_dir / "sft_clean_combined.jsonl"
        with combined_path.open("w", encoding="utf-8") as f:
            for sample in combined:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        
        print(f"\nCombined SFT: {len(combined)} (existing {len(existing_sft)} + repaired {len(sft_repaired)})")
        print(f"Saved: {combined_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

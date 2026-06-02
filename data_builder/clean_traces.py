"""Clean and build training data from rollout traces.

Generates:
  - sft_clean.jsonl
  - dpo_pairs.jsonl
  - credit_sft_data.jsonl
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


def load_all_traces(root: Path) -> list[dict]:
    """Load all traces from all rollout batches."""
    rollouts_dir = root / "outputs" / "rollouts"
    traces = []
    
    for run_dir in sorted(rollouts_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        
        for status in ["success", "failed"]:
            status_dir = run_dir / status
            if not status_dir.exists():
                continue
            
            for task_dir in sorted(status_dir.iterdir()):
                if not task_dir.is_dir():
                    continue
                
                for trace_file in sorted(task_dir.glob("*.trace.json")):
                    try:
                        trace = json.loads(trace_file.read_text(encoding="utf-8"))
                        trace["_source_file"] = str(trace_file)
                        traces.append(trace)
                    except Exception as e:
                        print(f"Warning: Failed to load {trace_file}: {e}")
    
    return traces


def load_task_issue(root: Path, task_id: str) -> str:
    """Load issue text from task directory."""
    issue_path = root / "benchmark" / "tasks" / task_id / "issue.md"
    if issue_path.exists():
        return issue_path.read_text(encoding="utf-8").strip()
    return ""


def check_sft_quality(trace: dict) -> tuple[bool, str | None]:
    """Check if trace is suitable for SFT."""
    if not trace.get("success"):
        return False, "not_success"
    
    steps = trace.get("steps", [])
    if not steps:
        return False, "no_steps"
    
    has_run_tests = False
    has_edit_file = False
    has_submit_patch = False
    
    for step in steps:
        action = step.get("action", {})
        action_name = action.get("name", "")
        observation = step.get("observation", "")
        
        for pattern in BAD_PATTERNS:
            if pattern in observation:
                return False, f"bad_pattern:{pattern}"
        
        if action_name not in ALLOWED_ACTIONS:
            return False, f"invalid_action:{action_name}"
        
        if action_name == "run_tests":
            has_run_tests = True
        if action_name == "edit_file":
            has_edit_file = True
        if action_name == "submit_patch":
            has_submit_patch = True
    
    if not has_run_tests:
        return False, "no_run_tests"
    if not has_edit_file:
        return False, "no_edit_file"
    if not has_submit_patch:
        return False, "no_submit_patch"
    
    return True, None


def build_sft_sample(trace: dict, issue: str) -> dict:
    """Convert trace to SFT training sample."""
    messages = []
    
    messages.append({
        "role": "system",
        "content": "You are a coding assistant. Fix the bug in the codebase."
    })
    
    messages.append({
        "role": "user",
        "content": issue
    })
    
    for step in trace.get("steps", []):
        action = step.get("action", {})
        
        assistant_msg = {
            "thought": action.get("thought", ""),
            "action": action.get("name", ""),
            "arguments": action.get("arguments", {}),
        }
        messages.append({
            "role": "assistant",
            "content": json.dumps(assistant_msg, ensure_ascii=False)
        })
        
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
        }
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading traces...")
    traces = load_all_traces(root)
    print(f"Loaded {len(traces)} traces")
    
    success_traces = [t for t in traces if t.get("success")]
    failed_traces = [t for t in traces if not t.get("success")]
    print(f"Success: {len(success_traces)}, Failed: {len(failed_traces)}")
    
    # Build clean SFT
    print("\nBuilding clean SFT...")
    sft_clean = []
    sft_rejected = []
    reject_reasons = {}
    
    for trace in success_traces:
        is_clean, reason = check_sft_quality(trace)
        if is_clean:
            issue = load_task_issue(root, trace.get("task_id", ""))
            sft_clean.append(build_sft_sample(trace, issue))
        else:
            sft_rejected.append({**trace, "_reject_reason": reason})
            reject_reasons[reason] = reject_reasons.get(reason, 0) + 1
    
    print(f"Clean SFT: {len(sft_clean)}")
    print(f"Rejected: {len(sft_rejected)}")
    print(f"Reject reasons: {reject_reasons}")
    
    # Save SFT clean
    sft_path = output_dir / "sft_clean.jsonl"
    with sft_path.open("w", encoding="utf-8") as f:
        for sample in sft_clean:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"Saved: {sft_path}")
    
    # Save stats
    stats = {
        "total_traces": len(traces),
        "success_traces": len(success_traces),
        "failed_traces": len(failed_traces),
        "sft_clean": len(sft_clean),
        "sft_rejected": len(sft_rejected),
        "reject_reasons": reject_reasons,
    }
    
    stats_path = output_dir / "dataset_stats.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved stats: {stats_path}")
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total traces: {len(traces)}")
    print(f"Clean SFT: {len(sft_clean)}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

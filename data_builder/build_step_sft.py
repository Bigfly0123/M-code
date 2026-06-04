"""Build step-level SFT data from high-quality success traces.

Converts trajectory-level data into step-level prompt-completion pairs
that match the actual agent inference loop.

Usage:
    python -m evocode_orchard_lite.data_builder.build_step_sft
"""
from __future__ import annotations

import json
from pathlib import Path

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.harness.action_parser import parse_action, ActionParseError
from evocode_orchard_lite.harness.prompt_builder import PromptBuilder
from evocode_orchard_lite.schema import Step


def load_task_issue(root: Path, task_id: str) -> str:
    """Load issue text from task directory."""
    issue_path = root / "benchmark" / "tasks" / task_id / "issue.md"
    if issue_path.exists():
        return issue_path.read_text(encoding="utf-8").strip()
    return ""


def build_step_samples(trace: dict, env: CodeRepairEnv, prompt_builder: PromptBuilder, root: Path) -> list[dict]:
    """Convert a trace into step-level samples."""
    samples = []
    task_id = trace.get("task_id", "")
    
    # Load task
    try:
        task = env.load_task(task_id)
    except Exception:
        return samples
    
    steps = trace.get("steps", [])
    history: list[Step] = []
    
    for i, step in enumerate(steps):
        action = step.get("action", {})
        action_name = action.get("name", "")
        
        # Skip if action is empty or invalid
        if not action_name or action_name not in {
            "list_files", "read_file", "search_code", "edit_file",
            "run_tests", "git_diff", "submit_patch"
        }:
            # Add to history as tool response and continue
            history.append(Step(
                step=i + 1,
                thought=action.get("thought", ""),
                action=action,
                observation=step.get("observation", ""),
                tool_success=step.get("tool_success", False),
            ))
            continue
        
        # Build prompt using PromptBuilder
        prompt = prompt_builder.build(task, history, sorted(env.tools.tools if hasattr(env, 'tools') else []))
        
        # Build completion
        completion = {
            "thought": action.get("thought", "") or f"Execute {action_name}",
            "action": action_name,
            "arguments": action.get("arguments", {}),
        }
        completion_str = json.dumps(completion, ensure_ascii=False)
        
        # Validate completion can be parsed
        try:
            parsed = parse_action(completion_str)
            if parsed.name != action_name:
                # Skip if parsed action doesn't match
                history.append(Step(
                    step=i + 1,
                    thought=action.get("thought", ""),
                    action=action,
                    observation=step.get("observation", ""),
                    tool_success=step.get("tool_success", False),
                ))
                continue
        except ActionParseError:
            # Skip unparseable completions
            history.append(Step(
                step=i + 1,
                thought=action.get("thought", ""),
                action=action,
                observation=step.get("observation", ""),
                tool_success=step.get("tool_success", False),
            ))
            continue
        
        # Get bug type from metadata
        bug_type = ""
        meta_path = root / "benchmark" / "tasks" / task_id / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            bug_type = meta.get("bug_type", "")
        
        sample = {
            "sample_id": f"{task_id}_step_{i:03d}",
            "task_id": task_id,
            "step": i,
            "source": trace.get("model", "unknown"),
            "bug_type": bug_type,
            "prompt": prompt,
            "completion": completion_str,
            "action": action_name,
            "trace_success": trace.get("success", False),
            "trace_label": trace.get("_category", "unknown"),
        }
        samples.append(sample)
        
        # Add to history
        history.append(Step(
            step=i + 1,
            thought=action.get("thought", ""),
            action=action,
            observation=step.get("observation", ""),
            tool_success=step.get("tool_success", False),
        ))
    
    return samples


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load high-quality success traces
    input_path = output_dir / "high_quality_success_traces.jsonl"
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run audit_teacher_traces first.")
        return 1
    
    print(f"Loading traces from {input_path}")
    traces = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Loaded {len(traces)} traces")
    
    # Load full traces from rollouts
    rollouts_dir = root / "outputs" / "rollouts"
    full_traces = {}
    for run_dir in rollouts_dir.iterdir():
        if not run_dir.is_dir():
            continue
        for status in ["success", "failed"]:
            status_dir = run_dir / status
            if not status_dir.exists():
                continue
            for task_dir in status_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                for trace_file in task_dir.glob("*.trace.json"):
                    try:
                        trace = json.loads(trace_file.read_text(encoding="utf-8"))
                        key = (trace.get("task_id"), trace.get("run_id"), trace.get("rollout_id"))
                        full_traces[key] = trace
                    except Exception:
                        pass
    
    print(f"Loaded {len(full_traces)} full traces")
    
    # Setup environment and prompt builder
    env = CodeRepairEnv(
        tasks_root=root / "benchmark" / "tasks",
        workspaces_root=root / "outputs" / "workspaces",
    )
    prompt_builder = PromptBuilder()
    
    # Build step-level samples
    print("\nBuilding step-level samples...")
    all_samples = []
    parse_errors = 0
    
    for labeled_trace in traces:
        key = (labeled_trace.get("task_id"), labeled_trace.get("run_id"), labeled_trace.get("rollout_id"))
        full_trace = full_traces.get(key)
        
        if not full_trace:
            # Try to find by task_id only
            task_id = labeled_trace.get("task_id")
            for k, v in full_traces.items():
                if k[0] == task_id:
                    full_trace = v
                    break
        
        if not full_trace:
            parse_errors += 1
            continue
        
        full_trace["_category"] = labeled_trace.get("category", "unknown")
        samples = build_step_samples(full_trace, env, prompt_builder, root)
        all_samples.extend(samples)
    
    print(f"Generated {len(all_samples)} step-level samples")
    print(f"Traces without full data: {parse_errors}")
    
    # Save
    output_path = output_dir / "step_sft_clean.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"Saved: {output_path}")
    
    # Generate audit
    action_counts = {}
    for s in all_samples:
        action = s.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
    
    print("\nAction distribution:")
    for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
        print(f"  {action}: {count}")
    
    # Save audit
    audit = {
        "total_samples": len(all_samples),
        "unique_tasks": len(set(s["task_id"] for s in all_samples)),
        "action_distribution": action_counts,
        "parse_errors": parse_errors,
    }
    audit_path = output_dir / "step_sft_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"\nSaved audit: {audit_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

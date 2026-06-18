"""Build minimal-edit alignment data for 7B.

This stage targets the Phase 8.5 failure pattern:
7B workflow-aligned failures make too many edit_file attempts and often end in
PATCH_APPLY_ERROR or TEST_STILL_FAIL. The data here only uses train-side
high-quality success traces and filters for compact, stable workflows.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.harness.action_parser import ActionParseError, parse_action
from evocode_orchard_lite.harness.prompt_builder import PromptBuilder
from evocode_orchard_lite.schema import Step
from evocode_orchard_lite.tools import default_tool_registry


ACTION_LIMITS = {
    "read_file": 160,
    "edit_file": 260,
    "run_tests": 260,
    "git_diff": 80,
    "submit_patch": 160,
    "list_files": 40,
    "search_code": 20,
}

ALLOWED_ACTIONS = set(ACTION_LIMITS)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def trace_path(root: Path, item: dict) -> Path:
    run_id = item.get("run_id", "")
    task_id = item.get("task_id", "")
    rollout_id = item.get("rollout_id", "")
    return root / "outputs" / "rollouts" / run_id / "success" / task_id / f"rollout_{rollout_id}.trace.json"


def is_train_task(task_id: str) -> bool:
    try:
        idx = int(task_id.split("_")[1])
    except Exception:
        return False
    return idx <= 200


def is_minimal_success(trace: dict, max_steps: int, max_edits: int) -> bool:
    if not trace.get("success"):
        return False
    steps = trace.get("steps", [])
    actions = [s.get("action", {}).get("name", "") for s in steps if isinstance(s.get("action"), dict)]
    if len(steps) > max_steps:
        return False
    if actions.count("edit_file") > max_edits:
        return False
    if "edit_file" not in actions or "run_tests" not in actions or "submit_patch" not in actions:
        return False
    first_edit = actions.index("edit_file")
    return "run_tests" in actions[first_edit + 1 :]


def build_samples_from_trace(trace: dict, env: CodeRepairEnv, prompt_builder: PromptBuilder, root: Path) -> list[dict]:
    task_id = trace.get("task_id", "")
    try:
        task = env.load_task(task_id)
    except Exception:
        return []

    meta_path = root / "benchmark" / "tasks" / task_id / "metadata.json"
    bug_type = ""
    if meta_path.exists():
        bug_type = json.loads(meta_path.read_text(encoding="utf-8")).get("bug_type", "")

    history: list[Step] = []
    samples: list[dict] = []
    tools = sorted(default_tool_registry().tools)

    for i, step in enumerate(trace.get("steps", [])):
        action = step.get("action", {})
        action_name = action.get("name", "") if isinstance(action, dict) else ""
        if action_name not in ALLOWED_ACTIONS:
            continue

        prompt = prompt_builder.build(task, history, tools)
        completion = {
            "thought": step.get("thought", "") or f"Execute {action_name}",
            "action": action_name,
            "arguments": action.get("arguments", {}),
        }
        completion_str = json.dumps(completion, ensure_ascii=False)

        try:
            parsed = parse_action(completion_str)
            if parsed.name != action_name:
                continue
        except ActionParseError:
            continue

        samples.append(
            {
                "sample_id": f"{task_id}_minimal_{i:03d}",
                "task_id": task_id,
                "step": i,
                "source": trace.get("model", "unknown"),
                "bug_type": bug_type,
                "prompt": prompt,
                "completion": completion_str,
                "action": action_name,
                "trace_success": True,
                "trace_label": "minimal_edit_success",
                "num_trace_steps": len(trace.get("steps", [])),
                "edit_count": sum(
                    1
                    for s in trace.get("steps", [])
                    if isinstance(s.get("action"), dict) and s.get("action", {}).get("name") == "edit_file"
                ),
            }
        )

        history.append(
            Step(
                step=i + 1,
                thought=step.get("thought", ""),
                action=action,
                observation=step.get("observation", ""),
                tool_success=step.get("tool_success", False),
            )
        )

    return samples


def take_balanced(samples: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_action: dict[str, list[dict]] = defaultdict(list)
    for sample in samples:
        by_action[sample["action"]].append(sample)

    selected: list[dict] = []
    for action, limit in ACTION_LIMITS.items():
        bucket = by_action.get(action, [])
        rng.shuffle(bucket)
        selected.extend(bucket[:limit])
    rng.shuffle(selected)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="outputs/data/high_quality_success_traces.jsonl")
    parser.add_argument("--output", default="outputs/data/7b_minimal_edit_alignment.jsonl")
    parser.add_argument("--max_steps", type=int, default=5)
    parser.add_argument("--max_edits", type=int, default=2)
    parser.add_argument("--seed", type=int, default=43)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    labeled = load_jsonl(root / args.input)

    env = CodeRepairEnv(tasks_root=root / "benchmark" / "tasks", workspaces_root=root / "outputs" / "workspaces")
    prompt_builder = PromptBuilder()

    all_samples: list[dict] = []
    trace_stats = Counter()
    for item in labeled:
        task_id = item.get("task_id", "")
        if not is_train_task(task_id):
            trace_stats["non_train_task"] += 1
            continue
        path = trace_path(root, item)
        if not path.exists():
            trace_stats["missing_trace"] += 1
            continue
        trace = json.loads(path.read_text(encoding="utf-8"))
        if not is_minimal_success(trace, args.max_steps, args.max_edits):
            trace_stats["filtered_non_minimal"] += 1
            continue
        trace_stats["minimal_trace"] += 1
        all_samples.extend(build_samples_from_trace(trace, env, prompt_builder, root))

    selected = take_balanced(all_samples, args.seed)
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for idx, sample in enumerate(selected):
            sample["minimal_alignment_id"] = f"7b_minimal_{idx:05d}"
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    stats = {
        "output": str(output_path),
        "total_samples_before_balance": len(all_samples),
        "total_samples": len(selected),
        "unique_tasks": len({s["task_id"] for s in selected}),
        "action_distribution": Counter(s["action"] for s in selected),
        "bug_type_distribution": Counter(s.get("bug_type", "") for s in selected),
        "trace_stats": trace_stats,
        "limits": ACTION_LIMITS,
        "max_steps": args.max_steps,
        "max_edits": args.max_edits,
        "seed": args.seed,
    }
    stats_path = output_path.with_suffix(".stats.json")
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved {len(selected)} samples to {output_path}")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Build DPO preference pairs from success and failed traces.

For each failed trace, creates a DPO pair:
  - chosen: the successful trajectory for the same task (or a similar one)
  - rejected: the failed trajectory

When no success trace exists for the same task, pairs the failed trace with
a random success trace from a task with the same bug_type.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = (
    "You are a coding repair agent. Use structured JSON actions to inspect files, "
    "run tests, edit code, verify fixes, and submit patches."
)


def truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit // 2] + f"\n...[truncated {len(text) - limit} chars]...\n" + text[-limit // 2 :]


def trace_to_messages(root: Path, trace: dict[str, Any]) -> list[dict[str, str]]:
    task_id = trace["task_id"]
    task_dir = root / "benchmark" / "tasks" / task_id
    issue = (task_dir / "issue.md").read_text(encoding="utf-8")
    metadata = json.loads((task_dir / "metadata.json").read_text(encoding="utf-8"))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Fix task {task_id}.\n\n"
                f"Issue:\n{issue}\n\n"
                f"Metadata:\n{json.dumps(metadata, ensure_ascii=False)}"
            ),
        },
    ]

    for step in trace.get("steps", []):
        action = step.get("action", {})
        payload = {
            "thought": step.get("thought", ""),
            "action": action.get("name"),
            "arguments": action.get("arguments", {}),
        }
        messages.append({"role": "assistant", "content": json.dumps(payload, ensure_ascii=False)})
        if action.get("name") != "submit_patch":
            messages.append({"role": "tool", "content": truncate(step.get("observation", ""))})

    return messages


def load_traces(traces_dir: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for p in traces_dir.glob("*.trace.json"):
        trace = json.loads(p.read_text(encoding="utf-8"))
        result[trace["task_id"]] = trace
    return result


def load_task_metadata(root: Path) -> dict[str, dict]:
    tasks_root = root / "benchmark" / "tasks"
    meta = {}
    for task_dir in tasks_root.iterdir():
        if not task_dir.is_dir():
            continue
        meta_path = task_dir / "metadata.json"
        if meta_path.exists():
            meta[task_dir.name] = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta


def find_chosen_trace(
    task_id: str,
    success_traces: dict[str, dict],
    task_meta: dict[str, dict],
) -> dict[str, Any] | None:
    if task_id in success_traces:
        return success_traces[task_id]

    bug_type = task_meta.get(task_id, {}).get("bug_type", "")
    candidates = [
        tid
        for tid, meta in task_meta.items()
        if meta.get("bug_type") == bug_type and tid in success_traces
    ]
    if candidates:
        return success_traces[random.choice(candidates)]

    if success_traces:
        return success_traces[random.choice(list(success_traces.keys()))]

    return None


def build_dpo_dataset(
    root: Path,
    success_dir: Path,
    failed_dir: Path,
    output_path: Path,
) -> list[dict[str, Any]]:
    success_traces = load_traces(success_dir)
    failed_traces = load_traces(failed_dir)
    task_meta = load_task_metadata(root)

    pairs: list[dict[str, Any]] = []

    for task_id, failed in sorted(failed_traces.items()):
        chosen = find_chosen_trace(task_id, success_traces, task_meta)
        if chosen is None:
            continue

        chosen_messages = trace_to_messages(root, chosen)
        rejected_messages = trace_to_messages(root, failed)

        pairs.append(
            {
                "task_id": task_id,
                "chosen": chosen_messages,
                "rejected": rejected_messages,
                "chosen_source": chosen["task_id"],
                "rejected_source": task_id,
                "rejected_failure_type": failed.get("failure_type", "UNKNOWN"),
                "chosen_reward": chosen.get("reward", 0.0),
                "rejected_reward": failed.get("reward", 0.0),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    return pairs


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Build DPO preference pairs from traces.")
    parser.add_argument("--success-dir", type=Path, default=root / "outputs" / "traces" / "success")
    parser.add_argument("--failed-dir", type=Path, default=root / "outputs" / "traces" / "failed")
    parser.add_argument("--output", type=Path, default=root / "outputs" / "data" / "dpo_pairs.jsonl")
    args = parser.parse_args()

    pairs = build_dpo_dataset(root, args.success_dir, args.failed_dir, args.output)
    stats = {
        "pairs": len(pairs),
        "output": str(args.output),
        "same_task_pairs": sum(1 for p in pairs if p["task_id"] == p["chosen_source"]),
        "cross_task_pairs": sum(1 for p in pairs if p["task_id"] != p["chosen_source"]),
    }
    stats_path = args.output.with_suffix(".stats.json")
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SYSTEM_PROMPT = (
    "You are a coding repair agent. Use structured JSON actions to inspect files, "
    "run tests, edit code, verify fixes, and submit patches."
)


def truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-limit // 2 :]
    return f"{head}\n...[truncated {len(text) - limit} chars]...\n{tail}"


def assistant_action_message(step: dict[str, Any]) -> str:
    payload = {
        "thought": step.get("thought", ""),
        "action": step.get("action", {}).get("name"),
        "arguments": step.get("action", {}).get("arguments", {}),
    }
    return json.dumps(payload, ensure_ascii=False)


def load_task_context(root: Path, task_id: str) -> dict[str, Any]:
    task_dir = root / "benchmark" / "tasks" / task_id
    return {
        "issue": (task_dir / "issue.md").read_text(encoding="utf-8"),
        "metadata": json.loads((task_dir / "metadata.json").read_text(encoding="utf-8")),
    }


def trace_to_sft_sample(root: Path, trace: dict[str, Any]) -> dict[str, Any]:
    task_id = trace["task_id"]
    context = load_task_context(root, task_id)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Fix task {task_id}.\n\n"
                f"Issue:\n{context['issue']}\n\n"
                f"Metadata:\n{json.dumps(context['metadata'], ensure_ascii=False)}"
            ),
        },
    ]

    for step in trace["steps"]:
        messages.append({"role": "assistant", "content": assistant_action_message(step)})
        if step.get("action", {}).get("name") != "submit_patch":
            messages.append({"role": "tool", "content": truncate(step.get("observation", ""))})

    return {
        "task_id": task_id,
        "source_trace": f"{task_id}.trace.json",
        "success": trace.get("success", False),
        "reward": trace.get("reward", 0.0),
        "messages": messages,
    }


def build_sft_dataset(root: Path, traces_dir: Path, output_path: Path) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for trace_path in sorted(traces_dir.glob("*.trace.json")):
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        if not trace.get("success"):
            continue
        samples.append(trace_to_sft_sample(root, trace))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for sample in samples:
            file.write(json.dumps(sample, ensure_ascii=False) + "\n")
    return samples


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Build SFT jsonl from successful traces.")
    parser.add_argument(
        "--traces-dir",
        type=Path,
        default=root / "outputs" / "traces" / "success",
        help="Directory containing successful trace json files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "outputs" / "data" / "sft_data.jsonl",
        help="Output jsonl path.",
    )
    args = parser.parse_args()
    samples = build_sft_dataset(root=root, traces_dir=args.traces_dir, output_path=args.output)
    stats = {
        "samples": len(samples),
        "output": str(args.output),
        "avg_messages": sum(len(sample["messages"]) for sample in samples) / max(len(samples), 1),
    }
    stats_path = args.output.with_suffix(".stats.json")
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

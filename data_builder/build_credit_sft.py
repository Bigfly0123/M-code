"""Build Credit-SFT-lite data from failed traces.

Extracts productive segments (consecutive positive-scoring steps) from failed
trajectories and converts them into SFT training samples.

Scoring rules:
  list_files:           +1  (exploration)
  read_file:            +1  (inspection)
  search_code:          +1  (search)
  run_tests:            +1  (verification)
  edit_file success:    +1  (code change)
  edit_file fail:       -1  (bad edit)
  tool failure:         -1  (any failed tool call)
"""
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
    return text[: limit // 2] + f"\n...[truncated {len(text) - limit} chars]...\n" + text[-limit // 2 :]


def score_step(step: dict[str, Any], target_files: set[str]) -> int:
    action = step.get("action", {})
    name = action.get("name", "")
    success = step.get("tool_success", True)

    if not success:
        return -1

    if name in ("list_files", "read_file", "search_code", "run_tests", "submit_patch"):
        return 1
    if name == "edit_file":
        return 1
    return 0

    return score


def extract_productive_segments(
    steps: list[dict[str, Any]],
    target_files: set[str],
    min_segment_len: int = 2,
) -> list[list[dict[str, Any]]]:
    """Extract consecutive positive-scoring step sequences."""
    scored = [(step, score_step(step, target_files)) for step in steps]

    segments: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    for step, sc in scored:
        if sc > 0:
            current.append(step)
        else:
            if len(current) >= min_segment_len:
                segments.append(list(current))
            current = []

    if len(current) >= min_segment_len:
        segments.append(current)

    return segments


def segment_to_sft_sample(
    root: Path,
    trace: dict[str, Any],
    segment: list[dict[str, Any]],
    seg_index: int,
) -> dict[str, Any]:
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

    for step in segment:
        action = step.get("action", {})
        payload = {
            "thought": step.get("thought", ""),
            "action": action.get("name"),
            "arguments": action.get("arguments", {}),
        }
        messages.append({"role": "assistant", "content": json.dumps(payload, ensure_ascii=False)})
        if action.get("name") != "submit_patch":
            messages.append({"role": "tool", "content": truncate(step.get("observation", ""))})

    return {
        "task_id": task_id,
        "source_trace": f"{task_id}.trace.json",
        "segment_index": seg_index,
        "segment_length": len(segment),
        "source": "credit_sft_lite",
        "success": False,
        "reward": 0.0,
        "messages": messages,
    }


def build_credit_sft_dataset(
    root: Path,
    traces_dir: Path,
    output_path: Path,
    min_segment_len: int = 2,
) -> list[dict[str, Any]]:
    tasks_root = root / "benchmark" / "tasks"
    samples: list[dict[str, Any]] = []

    for trace_path in sorted(traces_dir.glob("*.trace.json")):
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        if trace.get("success"):
            continue

        task_id = trace["task_id"]
        meta_path = tasks_root / task_id / "metadata.json"
        target_files = set()
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            target_files = set(meta.get("target_files", []))

        segments = extract_productive_segments(trace.get("steps", []), target_files, min_segment_len)
        for idx, seg in enumerate(segments):
            samples.append(segment_to_sft_sample(root, trace, seg, idx))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    return samples


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Build Credit-SFT-lite jsonl from failed traces.")
    parser.add_argument(
        "--traces-dir",
        type=Path,
        default=root / "outputs" / "traces" / "failed",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "outputs" / "data" / "credit_sft_data.jsonl",
    )
    parser.add_argument("--min-segment-len", type=int, default=2)
    args = parser.parse_args()

    samples = build_credit_sft_dataset(root, args.traces_dir, args.output, args.min_segment_len)
    stats = {
        "samples": len(samples),
        "output": str(args.output),
        "avg_messages": sum(len(s["messages"]) for s in samples) / max(len(samples), 1),
    }
    stats_path = args.output.with_suffix(".stats.json")
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

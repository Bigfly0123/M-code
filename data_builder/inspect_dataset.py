"""Inspect a training dataset for quality metrics.

Checks:
  - sample count
  - avg messages per sample
  - avg token length estimate
  - action distribution
  - bad pattern count
  - submit_patch / run_tests presence rate
  - unknown action count
  - unrelated edit count
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from evocode_orchard_lite.data_builder.filter_sft import ALLOWED_ACTIONS, BAD_PATTERNS


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def inspect_dataset(root: Path, dataset_path: Path) -> dict[str, Any]:
    samples = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    total_messages = 0
    total_tokens = 0
    action_counts: Counter[str] = Counter()
    bug_type_counts: Counter[str] = Counter()
    bad_pattern_count = 0
    has_submit_count = 0
    has_run_tests_count = 0
    unknown_action_count = 0
    unrelated_edit_count = 0
    task_ids: set[str] = set()

    for sample in samples:
        messages = sample.get("messages", [])
        total_messages += len(messages)
        task_id = sample.get("task_id", "")
        task_ids.add(task_id)

        meta_path = root / "benchmark" / "tasks" / task_id / "metadata.json"
        target_files: set[str] = set()
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            target_files = set(meta.get("target_files", []))
            bug_type_counts[meta.get("bug_type", "unknown")] += 1

        has_submit = False
        has_run_tests = False

        for msg in messages:
            content = msg.get("content", "")
            total_tokens += estimate_tokens(content)

            role = msg.get("role", "")
            if role == "tool":
                for pattern in BAD_PATTERNS:
                    if pattern in content:
                        bad_pattern_count += 1

            if role == "assistant":
                try:
                    payload = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    continue

                if not isinstance(payload, dict):
                    continue

                action_name = payload.get("action", "")
                action_counts[action_name] += 1

                if action_name not in ALLOWED_ACTIONS:
                    unknown_action_count += 1
                if action_name == "submit_patch":
                    has_submit = True
                if action_name == "run_tests":
                    has_run_tests = True
                if action_name == "edit_file" and target_files:
                    path = (payload.get("arguments") or {}).get("path", "")
                    if path and path not in target_files:
                        unrelated_edit_count += 1

        if has_submit:
            has_submit_count += 1
        if has_run_tests:
            has_run_tests_count += 1

    n = len(samples) or 1
    return {
        "total_samples": len(samples),
        "unique_tasks": len(task_ids),
        "avg_messages": total_messages / n,
        "avg_tokens_est": total_tokens / n,
        "action_distribution": dict(action_counts.most_common()),
        "bug_type_distribution": dict(bug_type_counts.most_common()),
        "bad_pattern_count": bad_pattern_count,
        "submit_patch_rate": has_submit_count / n,
        "run_tests_rate": has_run_tests_count / n,
        "unknown_action_count": unknown_action_count,
        "unrelated_edit_count": unrelated_edit_count,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Inspect a training dataset.")
    parser.add_argument("--input", type=Path, required=True, help="Path to jsonl dataset.")
    args = parser.parse_args()

    report = inspect_dataset(root, args.input)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

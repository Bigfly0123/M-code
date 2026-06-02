"""Filter SFT data to keep only clean, high-quality samples.

Outputs:
  - sft_clean.jsonl          — samples that pass all checks
  - sft_rejected_noisy.jsonl — rejected samples with rejection reason
  - sft_clean.stats.json     — statistics
"""
from __future__ import annotations

import argparse
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


def check_sample(sample: dict[str, Any], target_files: set[str] | None = None) -> str | None:
    """Return rejection reason, or None if sample is clean."""
    messages = sample.get("messages", [])
    if len(messages) <= 2:
        return "too_few_messages"

    has_submit = False
    has_run_tests = False

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "tool":
            for pattern in BAD_PATTERNS:
                if pattern in content:
                    return f"bad_observation:{pattern}"

        if role == "assistant":
            try:
                payload = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                return "invalid_action_json"

            if not isinstance(payload, dict):
                return "invalid_action_json"

            action_name = payload.get("action")
            if action_name is None:
                return "missing_action_field"

            if action_name not in ALLOWED_ACTIONS:
                return f"unknown_action:{action_name}"

            arguments = payload.get("arguments")
            if action_name != "submit_patch" and not isinstance(arguments, dict):
                return "arguments_not_dict"

            if action_name == "submit_patch":
                has_submit = True
            if action_name == "run_tests":
                has_run_tests = True

            if action_name == "edit_file" and target_files:
                path = (arguments or {}).get("path", "")
                if path and path not in target_files:
                    return f"unrelated_edit:{path}"

    if not has_submit:
        return "missing_submit"
    if not has_run_tests:
        return "missing_run_tests"

    return None


def load_target_files(root: Path, task_id: str) -> set[str]:
    meta_path = root / "benchmark" / "tasks" / task_id / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return set(meta.get("target_files", []))
    return set()


def filter_sft_dataset(
    root: Path,
    input_path: Path,
    clean_path: Path,
    rejected_path: Path,
) -> dict[str, Any]:
    samples = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    clean: list[dict] = []
    rejected: list[dict] = []
    reject_reasons: dict[str, int] = {}

    for sample in samples:
        task_id = sample.get("task_id", "")
        target_files = load_target_files(root, task_id)
        reason = check_sample(sample, target_files or None)

        if reason is None:
            clean.append(sample)
        else:
            rejected.append({**sample, "_reject_reason": reason})
            reject_reasons[reason] = reject_reasons.get(reason, 0) + 1

    clean_path.parent.mkdir(parents=True, exist_ok=True)
    with clean_path.open("w", encoding="utf-8") as f:
        for s in clean:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with rejected_path.open("w", encoding="utf-8") as f:
        for s in rejected:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    return {
        "input_samples": len(samples),
        "clean_samples": len(clean),
        "rejected_samples": len(rejected),
        "reject_reasons": reject_reasons,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Filter SFT data for quality.")
    parser.add_argument("--input", type=Path, default=root / "outputs" / "data" / "sft_combined.jsonl")
    parser.add_argument("--clean-output", type=Path, default=root / "outputs" / "data" / "sft_clean.jsonl")
    parser.add_argument("--rejected-output", type=Path, default=root / "outputs" / "data" / "sft_rejected_noisy.jsonl")
    args = parser.parse_args()

    stats = filter_sft_dataset(root, args.input, args.clean_output, args.rejected_output)

    stats_path = args.clean_output.with_suffix(".stats.json")
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

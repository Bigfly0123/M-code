from __future__ import annotations

import json
from pathlib import Path

from evocode_orchard_lite.schema import Trace


class TraceLogger:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def save(self, trace: Trace) -> Path:
        """Save trace to new directory structure: outputs/rollouts/{run_id}/{status}/{task_id}/rollout_{rollout_id}.trace.json"""
        if trace.run_id:
            # New structure
            status = "success" if trace.success else "failed"
            trace_dir = self.output_dir / "rollouts" / trace.run_id / status / trace.task_id
            trace_dir.mkdir(parents=True, exist_ok=True)
            filename = f"rollout_{trace.rollout_id}.trace.json"
        else:
            # Legacy structure (backward compatible)
            status_dir = self.output_dir / ("success" if trace.success else "failed")
            status_dir.mkdir(parents=True, exist_ok=True)
            trace_dir = status_dir
            filename = f"{trace.task_id}.trace.json"

        path = trace_dir / filename
        path.write_text(json.dumps(trace.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path


class Manifest:
    """Manages manifest.jsonl for tracking rollouts."""

    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def completed_keys(self) -> set[tuple[str, str]]:
        """Return set of (task_id, rollout_id) that are already completed."""
        keys = set()
        if self.manifest_path.exists():
            for line in self.manifest_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    keys.add((item["task_id"], item["rollout_id"]))
        return keys

    def append(self, trace_summary: dict) -> None:
        """Append a trace summary to manifest.jsonl."""
        with self.manifest_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace_summary, ensure_ascii=False) + "\n")

    def load_all(self) -> list[dict]:
        """Load all entries from manifest.jsonl."""
        entries = []
        if self.manifest_path.exists():
            for line in self.manifest_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entries.append(json.loads(line))
        return entries

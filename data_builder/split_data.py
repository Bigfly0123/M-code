"""Split tasks into train/val/test sets.

Usage:
    python -m evocode_orchard_lite.data_builder.split_data
"""
from __future__ import annotations

import json
import random
from pathlib import Path


def split_tasks(root: Path, train_ratio: float = 0.7, val_ratio: float = 0.15, seed: int = 42) -> None:
    """Split tasks into train/val/test sets."""
    # Load task validation
    validation_path = root / "outputs" / "reports" / "task_validation.json"
    if not validation_path.exists():
        print("Error: task_validation.json not found")
        return
    
    data = json.loads(validation_path.read_text(encoding="utf-8"))
    valid_tasks = [t["task_id"] for t in data if t.get("valid")]
    
    # Shuffle
    random.seed(seed)
    random.shuffle(valid_tasks)
    
    # Split
    n = len(valid_tasks)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    
    train_tasks = sorted(valid_tasks[:n_train])
    val_tasks = sorted(valid_tasks[n_train:n_train + n_val])
    test_tasks = sorted(valid_tasks[n_train + n_val:])
    
    # Save
    split_dir = root / "outputs" / "data" / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    
    (split_dir / "train_tasks.txt").write_text("\n".join(train_tasks) + "\n", encoding="utf-8")
    (split_dir / "val_tasks.txt").write_text("\n".join(val_tasks) + "\n", encoding="utf-8")
    (split_dir / "test_tasks.txt").write_text("\n".join(test_tasks) + "\n", encoding="utf-8")
    
    print(f"Total valid tasks: {n}")
    print(f"Train: {len(train_tasks)} ({len(train_tasks)/n:.1%})")
    print(f"Val:   {len(val_tasks)} ({len(val_tasks)/n:.1%})")
    print(f"Test:  {len(test_tasks)} ({len(test_tasks)/n:.1%})")
    print(f"\nSaved to: {split_dir}")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    split_tasks(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

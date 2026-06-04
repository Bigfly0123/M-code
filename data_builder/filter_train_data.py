"""Filter step-level SFT data to prevent train/test leakage.

- Only keep samples from train_tasks.txt
- Remove answer leakage from prompt
- Validate no eval task overlap
"""
from __future__ import annotations

import json
from pathlib import Path


def load_task_ids(file_path: Path) -> set[str]:
    """Load task IDs from file."""
    return set(line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip())


def check_answer_leakage(sample: dict) -> tuple[bool, str]:
    """Check if prompt contains answer (new_text)."""
    action = sample.get("action", "")
    prompt = sample.get("prompt", "")
    completion = sample.get("completion", "")
    
    if action != "edit_file":
        return False, ""
    
    try:
        completion_json = json.loads(completion)
        new_text = completion_json.get("arguments", {}).get("new", "")
        old_text = completion_json.get("arguments", {}).get("old", "")
        
        if new_text and new_text in prompt:
            return True, "new_text_in_prompt"
        if old_text and old_text in prompt and len(old_text) > 20:
            return True, "old_text_in_prompt"
    except:
        pass
    
    return False, ""


def main():
    root = Path(__file__).resolve().parents[2]
    data_dir = root / "outputs" / "data"
    
    # Load task splits
    train_tasks = load_task_ids(data_dir / "splits" / "train_tasks.txt")
    eval_tasks = load_task_ids(data_dir / "splits" / "test_tasks.txt")
    
    print(f"Train tasks: {len(train_tasks)}")
    print(f"Eval tasks: {len(eval_tasks)}")
    print(f"Overlap: {len(train_tasks & eval_tasks)}")
    
    # Load all step-level samples
    input_path = data_dir / "step_sft_clean.jsonl"
    all_samples = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"\nTotal samples: {len(all_samples)}")
    
    # Filter by train tasks only
    train_samples = [s for s in all_samples if s.get("task_id") in train_tasks]
    eval_samples = [s for s in all_samples if s.get("task_id") in eval_tasks]
    other_samples = [s for s in all_samples if s.get("task_id") not in train_tasks and s.get("task_id") not in eval_tasks]
    
    print(f"Train task samples: {len(train_samples)}")
    print(f"Eval task samples: {len(eval_samples)}")
    print(f"Other samples: {len(other_samples)}")
    
    # Check for answer leakage in train samples
    leaked_samples = []
    clean_samples = []
    
    for s in train_samples:
        has_leak, leak_type = check_answer_leakage(s)
        if has_leak:
            leaked_samples.append((s, leak_type))
        else:
            clean_samples.append(s)
    
    print(f"\nAnswer leakage check:")
    print(f"  Clean samples: {len(clean_samples)}")
    print(f"  Leaked samples: {len(leaked_samples)}")
    
    # Count leak types
    leak_types = {}
    for _, leak_type in leaked_samples:
        leak_types[leak_type] = leak_types.get(leak_type, 0) + 1
    print(f"  Leak types: {leak_types}")
    
    # Save clean train data
    output_path = data_dir / "step_sft_train_clean.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for s in clean_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"\nSaved clean train data: {output_path}")
    print(f"Clean train samples: {len(clean_samples)}")
    
    # Save eval data separately
    eval_output_path = data_dir / "step_sft_eval.jsonl"
    with eval_output_path.open("w", encoding="utf-8") as f:
        for s in eval_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"Saved eval data: {eval_output_path}")
    print(f"Eval samples: {len(eval_samples)}")
    
    # Verify no overlap
    train_task_ids = set(s["task_id"] for s in clean_samples)
    eval_task_ids = set(s["task_id"] for s in eval_samples)
    overlap = train_task_ids & eval_task_ids
    
    print(f"\nVerification:")
    print(f"  Train task IDs: {len(train_task_ids)}")
    print(f"  Eval task IDs: {len(eval_task_ids)}")
    print(f"  Overlap: {len(overlap)}")
    
    if overlap:
        print(f"  ⚠️  WARNING: Overlap detected: {sorted(overlap)}")
    else:
        print(f"  ✅ No overlap - safe to train!")


if __name__ == "__main__":
    main()

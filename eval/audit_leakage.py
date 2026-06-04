"""Audit train/test overlap and data leakage."""
from __future__ import annotations

import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    
    # Load train task ids from step_sft_clean.jsonl
    step_sft_path = root / "outputs" / "data" / "step_sft_clean.jsonl"
    train_samples = [json.loads(line) for line in step_sft_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    train_task_ids = set(s["task_id"] for s in train_samples)
    
    # Load eval task ids from test_tasks.txt
    test_tasks_path = root / "outputs" / "data" / "splits" / "test_tasks.txt"
    eval_task_ids = set(line.strip() for line in test_tasks_path.read_text(encoding="utf-8").splitlines() if line.strip())
    
    # Load train tasks from splits
    train_tasks_path = root / "outputs" / "data" / "splits" / "train_tasks.txt"
    train_split_ids = set(line.strip() for line in train_tasks_path.read_text(encoding="utf-8").splitlines() if line.strip())
    
    # Check intersection
    intersection = train_task_ids & eval_task_ids
    train_split_intersection = train_split_ids & eval_task_ids
    
    print("=" * 60)
    print("CHECK 1: Train/Eval Task ID Overlap")
    print("=" * 60)
    print(f"Step-SFT train task IDs: {len(train_task_ids)}")
    print(f"Eval task IDs: {len(eval_task_ids)}")
    print(f"Intersection: {len(intersection)}")
    print()
    
    if intersection:
        print("⚠️  WARNING: Train/Eval overlap detected!")
        print(f"Overlapping tasks: {sorted(intersection)}")
        print()
        print("This means 96.4% result is NOT valid for generalization claims.")
        print("The model has likely memorized these tasks.")
    else:
        print("✅ No train/eval overlap. Result may be valid.")
    
    print()
    print("=" * 60)
    print("CHECK 2: Train Split vs Eval Split Overlap")
    print("=" * 60)
    print(f"Train split task IDs: {len(train_split_ids)}")
    print(f"Train split ∩ Eval: {len(train_split_intersection)}")
    
    if train_split_intersection:
        print(f"⚠️  WARNING: Train split and eval split overlap: {sorted(train_split_intersection)}")
    
    # Check step-level data leakage
    print()
    print("=" * 60)
    print("CHECK 3: Step-level Sample Analysis")
    print("=" * 60)
    
    # Check if train samples contain completion info in prompt
    samples_with_old_in_prompt = 0
    samples_with_new_in_prompt = 0
    total_edit_samples = 0
    
    for s in train_samples:
        if s.get("action") == "edit_file":
            total_edit_samples += 1
            prompt = s.get("prompt", "")
            completion = s.get("completion", "")
            
            try:
                completion_json = json.loads(completion)
                old_text = completion_json.get("arguments", {}).get("old", "")
                new_text = completion_json.get("arguments", {}).get("new", "")
                
                if old_text and old_text in prompt:
                    samples_with_old_in_prompt += 1
                if new_text and new_text in prompt:
                    samples_with_new_in_prompt += 1
            except:
                pass
    
    print(f"Total edit_file samples: {total_edit_samples}")
    print(f"Samples with old_text in prompt: {samples_with_old_in_prompt}")
    print(f"Samples with new_text in prompt: {samples_with_new_in_prompt}")
    
    if samples_with_new_in_prompt > 0:
        print(f"⚠️  WARNING: {samples_with_new_in_prompt} samples have new_text (answer) in prompt!")
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    issues = []
    if len(intersection) > 0:
        issues.append(f"Train/eval task overlap: {len(intersection)} tasks")
    if samples_with_new_in_prompt > 0:
        issues.append(f"Answer leakage in prompt: {samples_with_new_in_prompt} samples")
    
    if issues:
        print("⚠️  ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("96.4% result is likely inflated due to data leakage.")
        print("Recommendation: Re-split data and re-evaluate.")
    else:
        print("✅ No obvious issues found.")


if __name__ == "__main__":
    main()

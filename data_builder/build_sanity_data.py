"""Sanity check training with small dataset.

Tests if the model can learn to output valid JSON actions.
"""
from __future__ import annotations

import json
import random
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    input_path = root / "outputs" / "data" / "step_sft_clean.jsonl"
    output_dir = root / "outputs" / "data"
    
    # Load all samples
    samples = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Total samples: {len(samples)}")
    
    # Group by action
    by_action = {}
    for s in samples:
        action = s.get("action", "unknown")
        if action not in by_action:
            by_action[action] = []
        by_action[action].append(s)
    
    print("\nAction distribution:")
    for action, items in sorted(by_action.items(), key=lambda x: -len(x[1])):
        print(f"  {action}: {len(items)}")
    
    # Sample 100 balanced samples
    random.seed(42)
    sanity_samples = []
    target_per_action = 100 // len(by_action) + 1
    
    for action, items in by_action.items():
        sampled = random.sample(items, min(target_per_action, len(items)))
        sanity_samples.extend(sampled)
    
    # Trim to 100
    sanity_samples = sanity_samples[:100]
    
    # Save
    output_path = output_dir / "step_sft_sanity_100.jsonl"
    with output_path.open("w", encoding="utf-8") as f:
        for s in sanity_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    
    print(f"\nSaved {len(sanity_samples)} sanity samples: {output_path}")
    
    # Verify all completions are parseable
    from evocode_orchard_lite.harness.action_parser import parse_action, ActionParseError
    
    parse_errors = 0
    for s in sanity_samples:
        try:
            parsed = parse_action(s["completion"])
            if parsed.name != s["action"]:
                parse_errors += 1
        except ActionParseError:
            parse_errors += 1
    
    print(f"Parse errors: {parse_errors}/{len(sanity_samples)}")
    print(f"Parse success rate: {(len(sanity_samples) - parse_errors) / len(sanity_samples) * 100:.1f}%")


if __name__ == "__main__":
    main()

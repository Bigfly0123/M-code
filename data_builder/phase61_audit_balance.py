"""Phase 6.1: DPO data re-audit, reclassification, and balancing.

Input: data/dpo_main_pairs_expanded.jsonl (190 pairs)
Output:
  - data/dpo_sanity_pairs.jsonl (40-50 pairs)
  - data/dpo_patch_main_balanced.jsonl (120-160 pairs)
  - data/dpo_all_mixed_190.jsonl (full 190 backup)
  - data/dpo_phase6_1_data_audit.json
  - docs/dpo_phase6_1_data_audit.md
"""
import json
from pathlib import Path
from collections import defaultdict


def classify_failure_detail(pair):
    """Reclassify OTHER into more specific failure types."""
    ft = pair.get("rejected_failure_type", "OTHER")
    if ft != "OTHER":
        return ft

    # Analyze rejected action sequence for reclassification
    rejected = pair.get("rejected", "")
    chosen = pair.get("chosen", "")
    pair_type = pair.get("pair_type", "")

    # Check if rejected has no edit actions
    if "edit_file" not in rejected and "submit_patch" not in rejected:
        return "NO_EDIT"

    # Check if rejected has edit but no run_tests
    if "edit_file" in rejected and "run_tests" not in rejected:
        return "NO_TEST_AFTER_EDIT"

    # Check if rejected has run_tests but ends without submit
    if "run_tests" in rejected and "submit_patch" not in rejected:
        if "edit_file" in rejected:
            return "TEST_STILL_FAIL"
        return "NO_SUBMIT"

    # Check if rejected has multiple edits (potential over-edit)
    edit_count = rejected.count('"edit_file"')
    if edit_count > 2:
        return "OVER_EDIT"

    # Default: if it's from a failure trace, likely wrong patch
    if pair_type in ("patch_correctness", "same_task_v21_vs_base", "same_task_v21_vs_v2"):
        return "WRONG_PATCH"

    return "UNKNOWN"


def main():
    root = Path(__file__).resolve().parents[2]
    data_dir = root / "outputs" / "data"
    docs_dir = root / "docs"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Load splits
    train_tasks = set(l.strip() for l in open(root / "outputs" / "data" / "splits" / "train_tasks.txt") if l.strip())
    test_tasks = set(l.strip() for l in open(root / "outputs" / "data" / "splits" / "test_tasks.txt") if l.strip())
    val_path = root / "outputs" / "data" / "splits" / "val_tasks.txt"
    val_tasks = set(l.strip() for l in open(val_path) if l.strip()) if val_path.exists() else set()
    new50 = set(f"bugfix_{i}" for i in range(201, 251))
    new100 = set(f"bugfix_{i}" for i in range(251, 351))

    # Load pairs
    pairs = [json.loads(l) for l in open(data_dir / "dpo_main_pairs_expanded.jsonl") if l.strip()]
    print(f"Loaded {len(pairs)} pairs")

    # ============================================================
    # Step 1-2: Re-audit with detailed overlap fields
    # ============================================================
    all_tasks = set(p["task_id"] for p in pairs)
    audit = {
        "total_pairs": len(pairs),
        "unique_tasks": len(all_tasks),
        "new50_overlap": len(all_tasks & new50),
        "new100_as_dpo_source": len([p for p in pairs if p["task_id"] in new100]),
        "dpo_independent_eval_overlap": "not_created_yet",
        "old28_overlap": len(all_tasks & test_tasks),
        "train_split_pairs": len([p for p in pairs if p["task_id"] in train_tasks]),
        "val_split_overlap": len(all_tasks & val_tasks),
        "test_split_overlap": len(all_tasks & test_tasks),
        "unknown_task_pairs": len([p for p in pairs if p["task_id"] not in train_tasks and p["task_id"] not in test_tasks and p["task_id"] not in val_tasks and p["task_id"] not in new50 and p["task_id"] not in new100]),
    }
    print(f"\nOverlap audit:")
    for k, v in audit.items():
        if k != "total_pairs" and k != "unique_tasks":
            print(f"  {k}: {v}")

    # ============================================================
    # Step 3: Reclassify OTHER
    # ============================================================
    print(f"\n=== Reclassifying OTHER ===")
    old_ft = defaultdict(int)
    for p in pairs:
        old_ft[p.get("rejected_failure_type", "UNKNOWN")] += 1
    print(f"Before: {dict(old_ft)}")

    reclassified = 0
    for p in pairs:
        if p.get("rejected_failure_type") == "OTHER":
            new_type = classify_failure_detail(p)
            p["rejected_failure_type"] = new_type
            reclassified += 1
    print(f"Reclassified {reclassified} OTHER pairs")

    new_ft = defaultdict(int)
    for p in pairs:
        new_ft[p.get("rejected_failure_type", "UNKNOWN")] += 1
    print(f"After: {dict(new_ft)}")

    # ============================================================
    # Step 4: Quality scoring for FORMAT_ERROR pairs
    # ============================================================
    # Score each pair for quality
    for p in pairs:
        score = 50  # base score
        ft = p.get("rejected_failure_type", "")

        # Higher score for target failure types
        if ft in ("TEST_STILL_FAIL", "WRONG_PATCH"):
            score += 30
        elif ft == "NO_TEST_AFTER_EDIT":
            score += 20
        elif ft == "PATCH_APPLY_ERROR":
            score += 20
        elif ft == "NO_EDIT":
            score += 10
        elif ft == "FORMAT_ERROR":
            score -= 10  # deprioritize
        elif ft in ("UNKNOWN", "OVER_EDIT", "UNDER_EDIT"):
            score += 5

        # Bonus for same-task pairs
        if "same_task" in p.get("pair_type", ""):
            score += 15

        # Bonus for patch_correctness
        if p.get("pair_type") == "patch_correctness":
            score += 15

        # Penalty if chosen/rejected are too short
        if len(p.get("chosen", "")) < 20:
            score -= 20
        if len(p.get("rejected", "")) < 20:
            score -= 20

        p["_quality_score"] = score

    # Sort by quality
    pairs.sort(key=lambda p: p.get("_quality_score", 0), reverse=True)

    # ============================================================
    # Step 5: Generate DPO-sanity (40-50 pairs)
    # ============================================================
    print(f"\n=== Generating DPO-sanity ===")
    sanity = []
    sanity_ft = defaultdict(int)

    # Target: 20-25 TEST_STILL_FAIL/WRONG_PATCH, 10-15 same-task, 5 NO_TEST, 5 NO_EDIT, max 5 FORMAT_ERROR
    targets = {
        "TEST_STILL_FAIL": 15,
        "WRONG_PATCH": 10,
        "NO_TEST_AFTER_EDIT": 5,
        "NO_EDIT": 5,
        "PATCH_APPLY_ERROR": 3,
        "FORMAT_ERROR": 5,
        "OVER_EDIT": 2,
        "UNDER_EDIT": 2,
        "UNKNOWN": 3,
    }
    counts = defaultdict(int)
    used_tasks = set()

    for p in pairs:
        ft = p.get("rejected_failure_type", "UNKNOWN")
        limit = targets.get(ft, 3)
        if counts[ft] >= limit:
            continue
        if p["task_id"] in used_tasks:
            continue
        sanity.append(p)
        counts[ft] += 1
        used_tasks.add(p["task_id"])
        if len(sanity) >= 50:
            break

    # Fill remaining with best available
    if len(sanity) < 40:
        for p in pairs:
            if p["task_id"] in used_tasks:
                continue
            sanity.append(p)
            used_tasks.add(p["task_id"])
            if len(sanity) >= 40:
                break

    # Clean up quality score
    for p in sanity:
        p.pop("_quality_score", None)

    sanity_ft = defaultdict(int)
    for p in sanity:
        sanity_ft[p["rejected_failure_type"]] += 1
    print(f"Sanity: {len(sanity)} pairs")
    print(f"  Failure types: {dict(sanity_ft)}")

    # ============================================================
    # Step 6: Generate balanced DPO-main (120-160 pairs)
    # ============================================================
    print(f"\n=== Generating balanced DPO-main ===")
    # Use all pairs except sanity, rebalance
    main_used = set(p["task_id"] for p in sanity)
    remaining = [p for p in pairs if p["task_id"] not in main_used]
    remaining.sort(key=lambda p: p.get("_quality_score", 0), reverse=True)

    balanced = []
    bal_ft = defaultdict(int)
    bal_targets = {
        "TEST_STILL_FAIL": 40,
        "WRONG_PATCH": 25,
        "NO_TEST_AFTER_EDIT": 12,
        "NO_EDIT": 15,
        "PATCH_APPLY_ERROR": 5,
        "FORMAT_ERROR": 20,  # max 15% of ~150
        "OVER_EDIT": 5,
        "UNDER_EDIT": 5,
        "UNKNOWN": 5,
        "NO_SUBMIT": 5,
    }
    bal_counts = defaultdict(int)
    bal_used = set()

    for p in remaining:
        ft = p.get("rejected_failure_type", "UNKNOWN")
        limit = bal_targets.get(ft, 5)
        if bal_counts[ft] >= limit:
            continue
        if p["task_id"] in bal_used:
            continue
        balanced.append(p)
        bal_counts[ft] += 1
        bal_used.add(p["task_id"])
        if len(balanced) >= 160:
            break

    # Fill to 120 minimum
    if len(balanced) < 120:
        for p in remaining:
            if p["task_id"] in bal_used and p["task_id"] not in bal_used:
                continue
            if p["task_id"] in bal_used:
                continue
            balanced.append(p)
            bal_used.add(p["task_id"])
            if len(balanced) >= 120:
                break

    for p in balanced:
        p.pop("_quality_score", None)

    bal_ft = defaultdict(int)
    for p in balanced:
        bal_ft[p["rejected_failure_type"]] += 1
    print(f"Balanced main: {len(balanced)} pairs")
    print(f"  Failure types: {dict(bal_ft)}")

    # Check FORMAT_ERROR ratio
    fmt_ratio = bal_ft.get("FORMAT_ERROR", 0) / max(len(balanced), 1) * 100
    print(f"  FORMAT_ERROR ratio: {fmt_ratio:.1f}%")

    # ============================================================
    # Step 7: All-mixed-190 backup
    # ============================================================
    all_mixed = [p for p in pairs]
    for p in all_mixed:
        p.pop("_quality_score", None)

    # ============================================================
    # Save all datasets
    # ============================================================
    def save_jsonl(path, data):
        with path.open("w", encoding="utf-8") as f:
            for p in data:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(f"Saved {len(data)} pairs to {path.name}")

    save_jsonl(data_dir / "dpo_sanity_pairs.jsonl", sanity)
    save_jsonl(data_dir / "dpo_patch_main_balanced.jsonl", balanced)
    save_jsonl(data_dir / "dpo_all_mixed_190.jsonl", all_mixed)

    # ============================================================
    # Step 8: Generate audit report
    # ============================================================
    # Bug type distribution
    def bug_type_dist(data):
        bt = defaultdict(int)
        for p in data:
            bt[p.get("bug_type", "unknown")] += 1
        return dict(sorted(bt.items(), key=lambda x: -x[1]))

    final_audit = {
        "phase": "6.1",
        "original_pairs": len(pairs),
        "sanity_pairs": len(sanity),
        "balanced_main_pairs": len(balanced),
        "all_mixed_pairs": len(all_mixed),
        "overlap": audit,
        "failure_type_distribution": {
            "original_190": dict(new_ft),
            "sanity": dict(sanity_ft),
            "balanced_main": dict(bal_ft),
        },
        "bug_type_distribution": {
            "original_190": bug_type_dist(all_mixed),
            "sanity": bug_type_dist(sanity),
            "balanced_main": bug_type_dist(balanced),
        },
        "format_error_ratio": {
            "original_190": f"{new_ft.get('FORMAT_ERROR',0)/len(pairs)*100:.1f}%",
            "sanity": f"{sanity_ft.get('FORMAT_ERROR',0)/max(len(sanity),1)*100:.1f}%",
            "balanced_main": f"{bal_ft.get('FORMAT_ERROR',0)/max(len(balanced),1)*100:.1f}%",
        },
        "other_ratio": {
            "original_190": f"{new_ft.get('OTHER',0)/len(pairs)*100:.1f}%",
            "balanced_main": f"{bal_ft.get('OTHER',0)/max(len(balanced),1)*100:.1f}%",
        },
        "recommendation": "balanced_main >= 120, FORMAT_ERROR <= 15%, proceed to DPO-sanity",
    }

    audit_path = data_dir / "dpo_phase6_1_data_audit.json"
    audit_path.write_text(json.dumps(final_audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nAudit saved: {audit_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"PHASE 6.1 SUMMARY")
    print(f"{'='*60}")
    print(f"Original: {len(pairs)} pairs")
    print(f"Sanity: {len(sanity)} pairs")
    print(f"Balanced main: {len(balanced)} pairs")
    print(f"All-mixed backup: {len(all_mixed)} pairs")
    print(f"\nFailure type rebalance:")
    print(f"  {'Type':<25} {'Orig':>6} {'Sanity':>8} {'Balanced':>10}")
    all_types = sorted(set(list(new_ft.keys()) + list(sanity_ft.keys()) + list(bal_ft.keys())))
    for ft in all_types:
        print(f"  {ft:<25} {new_ft.get(ft,0):>6} {sanity_ft.get(ft,0):>8} {bal_ft.get(ft,0):>10}")

    # Decision
    print(f"\nDecision: ", end="")
    if len(balanced) >= 120 and bal_ft.get("FORMAT_ERROR", 0) / max(len(balanced), 1) <= 0.15:
        print("READY for DPO-sanity. No more data expansion needed.")
    else:
        print("Need more data or rebalancing.")


if __name__ == "__main__":
    main()

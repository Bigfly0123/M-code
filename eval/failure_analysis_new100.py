"""Analyze v2.1-clean failures on New100 held-out tasks."""
import json
from pathlib import Path
from collections import defaultdict


def main():
    root = Path(__file__).resolve().parents[2]
    traces_dir = root / "outputs" / "reports" / "full_metrics_new100" / "3b_sft_v21_clean"
    tasks_root = root / "benchmark" / "tasks"
    output_dir = root / "outputs" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all traces (from success/ and failed/ subdirectories)
    traces = []
    for subdir in ["success", "failed"]:
        sub = traces_dir / subdir
        if sub.exists():
            for trace_file in sorted(sub.glob("*.json")):
                try:
                    traces.append(json.loads(trace_file.read_text(encoding="utf-8")))
                except Exception:
                    pass
    # Also try direct files
    for trace_file in sorted(traces_dir.glob("*.json")):
        try:
            traces.append(json.loads(trace_file.read_text(encoding="utf-8")))
        except Exception:
            pass

    print(f"Loaded {len(traces)} traces")

    # Classify failures
    failures = []
    success_count = 0
    failure_types = defaultdict(int)
    bug_type_stats = defaultdict(lambda: {"success": 0, "fail": 0})
    difficulty_stats = defaultdict(lambda: {"success": 0, "fail": 0})

    for trace in traces:
        task_id = trace.get("task_id", "")
        success = trace.get("success", False)
        steps = trace.get("steps", [])

        # Load metadata
        meta_path = tasks_root / task_id / "metadata.json"
        bug_type = "unknown"
        difficulty = "unknown"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            bug_type = meta.get("bug_type", "unknown")
            difficulty = meta.get("difficulty", "unknown")

        if success:
            success_count += 1
            bug_type_stats[bug_type]["success"] += 1
            difficulty_stats[difficulty]["success"] += 1
            continue

        bug_type_stats[bug_type]["fail"] += 1
        difficulty_stats[difficulty]["fail"] += 1

        # Analyze failure
        has_edit = False
        has_run_tests = False
        last_test_passed = False
        edited_files = []
        actions = []
        patch_applied = False

        for step in steps:
            action = step.get("action", {})
            name = action.get("name", "")
            args = action.get("arguments", {})
            actions.append(name)

            if name == "edit_file":
                has_edit = True
                edited_files.append(args.get("path", ""))
            if name == "run_tests":
                has_run_tests = True
                obs = str(step.get("observation", ""))
                if "passed" in obs.lower() or "PASSED" in obs:
                    last_test_passed = True
            if name == "submit_patch":
                patch_applied = True

        # Classify failure type
        if not has_edit:
            ftype = "NO_EDIT"
        elif patch_applied and not last_test_passed:
            ftype = "PREMATURE_SUBMIT"
        elif has_edit and has_run_tests and not last_test_passed:
            ftype = "TEST_STILL_FAIL"
        elif has_edit and not has_run_tests:
            ftype = "NO_TEST_AFTER_EDIT"
        else:
            ftype = "TEST_STILL_FAIL"

        failure_types[ftype] += 1

        failures.append({
            "task_id": task_id,
            "bug_type": bug_type,
            "difficulty": difficulty,
            "success": False,
            "failure_type": ftype,
            "num_steps": len(steps),
            "has_edit": has_edit,
            "has_run_tests": has_run_tests,
            "last_test_passed": last_test_passed,
            "edited_files": edited_files,
            "action_sequence": actions,
            "candidate_dpo_type": "correct_patch_vs_wrong_patch" if ftype == "TEST_STILL_FAIL" else "read_to_edit",
        })

    # Summary
    print(f"\n{'='*60}")
    print(f"NEW100 v2.1-clean FAILURE ANALYSIS")
    print(f"{'='*60}")
    print(f"Total: {len(traces)}")
    print(f"Success: {success_count} ({100*success_count/len(traces):.1f}%)")
    print(f"Failure: {len(failures)} ({100*len(failures)/len(traces):.1f}%)")

    print(f"\nFailure Types:")
    for ftype, count in sorted(failure_types.items(), key=lambda x: -x[1]):
        print(f"  {ftype}: {count}")

    print(f"\nBy Bug Type:")
    for bt, stats in sorted(bug_type_stats.items(), key=lambda x: -(x[1]["success"]+x[1]["fail"])):
        total = stats["success"] + stats["fail"]
        rate = stats["success"] / total * 100 if total else 0
        print(f"  {bt}: {stats['success']}/{total} ({rate:.0f}%)")

    print(f"\nBy Difficulty:")
    for diff, stats in sorted(difficulty_stats.items()):
        total = stats["success"] + stats["fail"]
        rate = stats["success"] / total * 100 if total else 0
        print(f"  {diff}: {stats['success']}/{total} ({rate:.0f}%)")

    # Save
    report = {
        "total": len(traces),
        "success": success_count,
        "failure": len(failures),
        "success_rate": success_count / len(traces),
        "failure_types": dict(failure_types),
        "bug_type_stats": {k: dict(v) for k, v in bug_type_stats.items()},
        "difficulty_stats": {k: dict(v) for k, v in difficulty_stats.items()},
        "failures": failures,
    }

    (output_dir / "new100_v21_clean_failure_analysis.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nSaved: {output_dir / 'new100_v21_clean_failure_analysis.json'}")

    # DPO candidate stats
    dpo_candidates = [f for f in failures if f["candidate_dpo_type"] == "correct_patch_vs_wrong_patch"]
    print(f"\nDPO candidates (correct_patch_vs_wrong_patch): {len(dpo_candidates)}")


if __name__ == "__main__":
    main()

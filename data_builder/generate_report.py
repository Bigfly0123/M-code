"""Generate data generation report for all rollout batches.

Usage:
    python -m evocode_orchard_lite.data_builder.generate_report
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def load_manifest(manifest_path: Path) -> list[dict]:
    """Load manifest.jsonl."""
    entries = []
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
    return entries


def analyze_rollouts(root: Path) -> dict:
    """Analyze all rollout batches."""
    rollouts_dir = root / "outputs" / "rollouts"
    
    all_entries = []
    batch_stats = {}
    
    for run_dir in sorted(rollouts_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        
        manifest_path = run_dir / "manifest.jsonl"
        entries = load_manifest(manifest_path)
        
        if not entries:
            continue
        
        # Count stats
        success_count = sum(1 for e in entries if e.get("success"))
        failed_count = len(entries) - success_count
        failure_types = Counter(e.get("failure_type") for e in entries if not e.get("success"))
        
        batch_stats[run_dir.name] = {
            "total": len(entries),
            "success": success_count,
            "failed": failed_count,
            "success_rate": success_count / len(entries) if entries else 0,
            "failure_types": dict(failure_types),
            "avg_steps": sum(e.get("num_steps", 0) for e in entries) / len(entries) if entries else 0,
        }
        
        all_entries.extend(entries)
    
    # Overall stats
    total = len(all_entries)
    success = sum(1 for e in all_entries if e.get("success"))
    failed = total - success
    failure_types = Counter(e.get("failure_type") for e in all_entries if not e.get("success"))
    
    # Task coverage
    tasks = set(e.get("task_id") for e in all_entries)
    task_rollouts = Counter(e.get("task_id") for e in all_entries)
    
    # Unique tasks with success
    tasks_with_success = set(e.get("task_id") for e in all_entries if e.get("success"))
    tasks_with_failure = set(e.get("task_id") for e in all_entries if not e.get("success"))
    
    # BAR-lite grouping
    task_success_count = Counter(e.get("task_id") for e in all_entries if e.get("success"))
    task_total_count = Counter(e.get("task_id") for e in all_entries)
    
    too_easy = []
    too_hard = []
    informative = []
    
    for task_id in tasks:
        s = task_success_count.get(task_id, 0)
        t = task_total_count.get(task_id, 0)
        if s == t:
            too_easy.append(task_id)
        elif s == 0:
            too_hard.append(task_id)
        else:
            informative.append(task_id)
    
    return {
        "total_traces": total,
        "success_traces": success,
        "failed_traces": failed,
        "success_rate": success / total if total else 0,
        "failure_types": dict(failure_types),
        "avg_steps": sum(e.get("num_steps", 0) for e in all_entries) / total if total else 0,
        "unique_tasks": len(tasks),
        "tasks_with_success": len(tasks_with_success),
        "tasks_with_failure": len(tasks_with_failure),
        "avg_rollouts_per_task": total / len(tasks) if tasks else 0,
        "bar_lite": {
            "too_easy": len(too_easy),
            "too_hard": len(too_hard),
            "informative": len(informative),
        },
        "batch_stats": batch_stats,
    }


def generate_report(root: Path) -> None:
    """Generate data generation report."""
    stats = analyze_rollouts(root)
    
    # Save JSON
    report_dir = root / "outputs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = report_dir / "data_generation_report.json"
    json_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Generate markdown report
    md_lines = [
        "# Data Generation Report",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|---|---:|",
        f"| Total Traces | {stats['total_traces']} |",
        f"| Success Traces | {stats['success_traces']} |",
        f"| Failed Traces | {stats['failed_traces']} |",
        f"| Success Rate | {stats['success_rate']:.2%} |",
        f"| Avg Steps | {stats['avg_steps']:.2f} |",
        f"| Unique Tasks | {stats['unique_tasks']} |",
        f"| Tasks with Success | {stats['tasks_with_success']} |",
        f"| Tasks with Failure | {stats['tasks_with_failure']} |",
        f"| Avg Rollouts/Task | {stats['avg_rollouts_per_task']:.1f} |",
        "",
        "## BAR-lite Grouping",
        "",
        f"| Group | Count |",
        f"|---|---:|",
        f"| Too Easy (all success) | {stats['bar_lite']['too_easy']} |",
        f"| Too Hard (all failure) | {stats['bar_lite']['too_hard']} |",
        f"| Informative (mixed) | {stats['bar_lite']['informative']} |",
        "",
        "## Failure Types",
        "",
        "| Type | Count |",
        "|---|---:|",
    ]
    
    for ftype, count in sorted(stats['failure_types'].items(), key=lambda x: -x[1]):
        md_lines.append(f"| {ftype or 'None'} | {count} |")
    
    md_lines.extend([
        "",
        "## Batch Statistics",
        "",
        "| Batch | Total | Success | Failed | Success Rate | Avg Steps |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    
    for batch_name, batch in sorted(stats['batch_stats'].items()):
        md_lines.append(
            f"| {batch_name} | {batch['total']} | {batch['success']} | {batch['failed']} | {batch['success_rate']:.2%} | {batch['avg_steps']:.2f} |"
        )
    
    md_path = report_dir / "data_generation_report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    
    print(f"Report generated:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")
    print()
    print(f"Total traces: {stats['total_traces']}")
    print(f"Success rate: {stats['success_rate']:.2%}")
    print(f"BAR-lite: {stats['bar_lite']}")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    generate_report(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

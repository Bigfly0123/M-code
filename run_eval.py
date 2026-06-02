from __future__ import annotations

import argparse
import json
from pathlib import Path

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.eval.metrics import summarize_traces
from evocode_orchard_lite.eval.report_generator import write_baseline_report
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.harness.scripted_model import ScriptedModel
from evocode_orchard_lite.schema import Trace
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger


def build_scripted_model(task_id: str, fix: dict) -> ScriptedModel:
    responses = [
        '{"thought": "Run the failing test first.", "action": "run_tests", "arguments": {}}',
        json.dumps(
            {
                "thought": "Inspect the target file.",
                "action": "read_file",
                "arguments": {"path": fix["path"]},
            }
        ),
        json.dumps(
            {
                "thought": "Apply the minimal known fix.",
                "action": "edit_file",
                "arguments": {"path": fix["path"], "old": fix["old"], "new": fix["new"]},
            }
        ),
        '{"thought": "Verify the fix.", "action": "run_tests", "arguments": {}}',
        '{"thought": "Submit the working patch.", "action": "submit_patch", "arguments": {}}',
    ]
    return ScriptedModel(responses, name=f"scripted-baseline:{task_id}")


def run_eval(task_ids: list[str] | None = None) -> tuple[list[Trace], dict]:
    root = Path(__file__).resolve().parents[1]
    tasks_root = root / "benchmark" / "tasks"
    all_task_ids = sorted(path.name for path in tasks_root.iterdir() if path.is_dir())
    selected = task_ids or all_task_ids

    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "workspaces")
    trace_logger = TraceLogger(root / "outputs" / "traces")
    traces: list[Trace] = []

    for task_id in selected:
        task = env.load_task(task_id)
        fix = task.metadata.get("scripted_fix")
        if not fix:
            raise ValueError(f"Task {task_id} is missing metadata.scripted_fix")
        agent = AgentLoop(
            model=build_scripted_model(task_id, fix),
            tools=default_tool_registry(),
            trace_logger=trace_logger,
            max_steps=8,
        )
        traces.append(agent.run(task))

    summary = summarize_traces(traces)
    reports_dir = root / "outputs" / "reports"
    write_baseline_report(reports_dir / "baseline_report.md", traces, summary)
    (reports_dir / "baseline_summary.json").write_text(
        json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return traces, summary.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EvoCode-Orchard-Lite scripted baseline eval.")
    parser.add_argument("--task", action="append", dest="tasks", help="Task id to run. Can be passed multiple times.")
    args = parser.parse_args()
    traces, summary = run_eval(args.tasks)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all(trace.success for trace in traces) else 1


if __name__ == "__main__":
    raise SystemExit(main())

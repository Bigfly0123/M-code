from __future__ import annotations

from pathlib import Path

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.harness.scripted_model import ScriptedModel
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = CodeRepairEnv(
        tasks_root=root / "benchmark" / "tasks",
        workspaces_root=root / "outputs" / "workspaces",
    )
    task = env.load_task("bugfix_001")
    model = ScriptedModel(
        [
            '{"thought": "Run the failing test first.", "action": "run_tests", "arguments": {}}',
            '{"thought": "Inspect the target file.", "action": "read_file", "arguments": {"path": "auth.py"}}',
            '{"thought": "The equality boundary should be expired.", "action": "edit_file", "arguments": {"path": "auth.py", "old": "return token_time < now", "new": "return token_time <= now"}}',
            '{"thought": "Verify the fix.", "action": "run_tests", "arguments": {}}',
            '{"thought": "Submit the working patch.", "action": "submit_patch", "arguments": {}}',
        ]
    )
    agent = AgentLoop(
        model=model,
        tools=default_tool_registry(),
        trace_logger=TraceLogger(root / "outputs" / "traces"),
        max_steps=8,
    )
    trace = agent.run(task)
    print(f"task_id={trace.task_id}")
    print(f"success={trace.success}")
    print(f"reward={trace.reward}")
    print(f"steps={len(trace.steps)}")
    print(f"failure_type={trace.failure_type}")
    return 0 if trace.success else 1


if __name__ == "__main__":
    raise SystemExit(main())

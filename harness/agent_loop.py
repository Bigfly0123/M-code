from __future__ import annotations

from evocode_orchard_lite.eval.reward import evaluate_trace
from evocode_orchard_lite.harness.action_parser import ActionParseError, parse_action
from evocode_orchard_lite.harness.format_error_handler import FormatErrorHandler
from evocode_orchard_lite.harness.prompt_builder import PromptBuilder
from evocode_orchard_lite.schema import Step, Task, Trace
from evocode_orchard_lite.tools.registry import ToolRegistry
from evocode_orchard_lite.trajectory.trace_logger import TraceLogger


class AgentLoop:
    def __init__(
        self,
        model,
        tools: ToolRegistry,
        trace_logger: TraceLogger,
        prompt_builder: PromptBuilder | None = None,
        max_steps: int = 8,
        max_format_retries: int = 3,
        auto_save: bool = True,
    ):
        self.model = model
        self.tools = tools
        self.trace_logger = trace_logger
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.max_steps = max_steps
        self.format_handler = FormatErrorHandler(max_retries=max_format_retries)
        self.auto_save = auto_save

    def run(self, task: Task) -> Trace:
        trace = Trace(task_id=task.task_id, model=getattr(self.model, "name", self.model.__class__.__name__))
        history: list[Step] = []

        for step_no in range(1, self.max_steps + 1):
            prompt = self.prompt_builder.build(task, history, sorted(self.tools.tools))
            response = self.model.generate(prompt)
            try:
                action = parse_action(response)
            except ActionParseError as exc:
                action = self.format_handler.handle(response, exc, prompt, self.model)
                if action is None:
                    trace.metrics["format_errors"] = trace.metrics.get("format_errors", 0) + 1
                    step = Step(
                        step=step_no,
                        thought="",
                        action={"raw_response": response},
                        observation=f"Format error after retries: {exc}",
                        tool_success=False,
                    )
                    trace.steps.append(step)
                    history.append(step)
                    continue

            if action.name == "submit_patch":
                trace.steps.append(
                    Step(
                        step=step_no,
                        thought=action.thought,
                        action={"name": action.name, "arguments": action.arguments},
                        observation="Submitted.",
                        tool_success=True,
                    )
                )
                break

            try:
                result = self.tools.execute(task, action)
            except Exception as exc:
                from evocode_orchard_lite.schema import ToolResult

                result = ToolResult(False, f"Tool error: {exc}", {"failure_type": "TOOL_ERROR"})
            step = Step(
                step=step_no,
                thought=action.thought,
                action={"name": action.name, "arguments": action.arguments},
                observation=result.observation,
                tool_success=result.success,
            )
            trace.steps.append(step)
            history.append(step)
            if not result.success and action.name != "run_tests" and trace.failure_type is None:
                trace.failure_type = result.data.get("failure_type", "TOOL_ERROR")

        diff_result = self.tools.execute(task, parse_action('{"action": "git_diff", "arguments": {}}'))
        trace.final_patch = diff_result.data.get("diff", diff_result.observation)
        evaluate_trace(task, trace)
        
        if self.auto_save:
            self.trace_logger.save(trace)
        
        return trace

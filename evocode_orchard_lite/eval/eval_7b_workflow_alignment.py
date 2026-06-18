"""Evaluate 7B workflow-aligned adapters on Independent50.

Default: adapter + hard test guard + Repair v3.
Use --adapter_path "" to evaluate the base 7B model with the same runtime.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

os.environ["TMPDIR"] = str(Path(__file__).resolve().parents[2] / ".tmp")

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger

JSON_EXAMPLE = 'Respond with JSON: {"thought": "...", "action": "...", "arguments": {...}}'


class HFModel(Model):
    def __init__(self, model, tokenizer, name: str):
        self.model = model
        self.tokenizer = tokenizer
        self.name = name

    def generate(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=2048,
                do_sample=False,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        return self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)


def classify_failure(trace) -> str:
    if trace.success:
        return "SUCCESS"
    if getattr(trace, "failure_type", None) == "EDIT_BUDGET_EXCEEDED":
        return "EDIT_BUDGET_EXCEEDED"
    has_edit = False
    has_tests = False
    test_passed = False
    for step in trace.steps:
        action = step.action if hasattr(step, "action") else {}
        name = action.get("name", "") if isinstance(action, dict) else ""
        if name == "edit_file":
            has_edit = True
        if name == "run_tests":
            has_tests = True
            obs = str(step.observation if hasattr(step, "observation") else "")
            if "passed" in obs.lower():
                test_passed = True
    if not has_edit:
        return "NO_EDIT"
    if has_edit and not has_tests:
        return "NO_TEST_AFTER_EDIT"
    if has_edit and has_tests and not test_passed:
        return "TEST_STILL_FAIL"
    return "OTHER"


def get_test_output(trace) -> str:
    for step in reversed(trace.steps):
        action = step.action if hasattr(step, "action") else {}
        name = action.get("name", "") if isinstance(action, dict) else ""
        if name == "run_tests":
            return str(step.observation if hasattr(step, "observation") else "")[:800]
    return ""


def extract_failure_details(test_output: str) -> str:
    lines = test_output.splitlines()
    failure_lines = []
    capture = False
    for line in lines:
        if "FAILED" in line or "FAIL" in line or "ERROR" in line:
            capture = True
        if capture:
            failure_lines.append(line)
            if len(failure_lines) >= 10:
                break
    return "\n".join(failure_lines) if failure_lines else test_output[:500]


def build_repair_prompt_v3(task, trace, failure_type: str) -> str:
    details = extract_failure_details(get_test_output(trace))
    last_edit = ""
    for step in trace.steps:
        action = step.action if hasattr(step, "action") else {}
        if isinstance(action, dict) and action.get("name") == "edit_file":
            last_edit = json.dumps(action, ensure_ascii=False)[:500]

    base = f"""You attempted to fix the bug but tests still fail.

Task:
{task.issue}

Test failure details:
{details[:600]}

Previous edit:
{last_edit}
"""
    if failure_type == "NO_EDIT":
        instruction = """
CRITICAL: You MUST make a source-code edit.
- Read the source file to see the current code
- Identify the specific line that needs to change
- Use edit_file to apply a minimal fix
- Then run tests
"""
    elif failure_type == "TEST_STILL_FAIL":
        instruction = """
Your previous patch did not fix the test failure.
- Read the failure output carefully
- Compare your edit with the expected behavior
- Make a different, more targeted source-code fix
- Do NOT modify tests
"""
    elif failure_type == "OTHER":
        instruction = """
Your fix was applied but is logically incorrect.
- Read the failing test expectation
- Read the current source implementation
- Add only the missing logic
- Keep the patch minimal
"""
    else:
        instruction = """
Repair the failing tests by editing the source code.
- Do NOT modify tests
- Keep the patch minimal
- Run tests after editing
"""
    return base + instruction + "\n" + JSON_EXAMPLE


def load_model(base_model: str, adapter_path: str, name: str) -> HFModel:
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    if adapter_path:
        model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    return HFModel(model, tokenizer, name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="/mnt/disk/mxf/models/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--adapter_path", default="outputs/models/7b_workflow_alignment")
    parser.add_argument("--output_dir", default="outputs/reports/eval_7b_workflow_alignment")
    parser.add_argument("--start", type=int, default=351)
    parser.add_argument("--end", type=int, default=400)
    parser.add_argument("--num_tasks", type=int, default=0, help="0 means all tasks in range")
    parser.add_argument("--max_steps", type=int, default=10)
    parser.add_argument("--repair_steps", type=int, default=8)
    parser.add_argument("--no_hard_guard", action="store_true")
    parser.add_argument("--no_repair", action="store_true")
    parser.add_argument("--max_successful_edits", type=int, default=0, help="0 disables the successful-edit budget")
    parser.add_argument("--max_total_edit_attempts", type=int, default=0, help="0 disables the total edit-attempt budget")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "eval_workspaces")
    tasks = sorted(
        p.name
        for p in tasks_root.iterdir()
        if p.is_dir() and p.name.startswith("bugfix_") and args.start <= int(p.name.split("_")[1]) <= args.end
    )
    if args.num_tasks:
        tasks = tasks[: args.num_tasks]

    output_dir = root / args.output_dir
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    adapter = str(root / args.adapter_path) if args.adapter_path else ""
    model_name = Path(args.adapter_path).name if args.adapter_path else "7b_base"
    hf = load_model(args.base_model, adapter, model_name)

    first_ok = 0
    repair_ok = 0
    failure_first: dict[str, int] = {}
    failure_final: dict[str, int] = {}
    details = []
    hard_guard = not args.no_hard_guard
    max_successful_edits = args.max_successful_edits or None
    max_total_edit_attempts = args.max_total_edit_attempts or None

    for task_id in tasks:
        task = env.load_task(task_id)
        agent = AgentLoop(
            model=hf,
            tools=default_tool_registry(),
            trace_logger=TraceLogger(trace_dir / "first"),
            max_steps=args.max_steps,
            auto_save=True,
            auto_run_tests_after_edit=hard_guard,
            max_successful_edits=max_successful_edits,
            max_total_edit_attempts=max_total_edit_attempts,
        )
        trace = agent.run(task)
        if trace.success:
            first_ok += 1
            details.append({"task_id": task_id, "result": "first_pass_ok"})
            print(f"  {task_id}: FIRST_PASS OK", flush=True)
            continue

        first_type = classify_failure(trace)
        failure_first[first_type] = failure_first.get(first_type, 0) + 1

        if args.no_repair:
            failure_final[first_type] = failure_final.get(first_type, 0) + 1
            details.append({"task_id": task_id, "result": "first_fail", "failure_type": first_type})
            print(f"  {task_id}: FAIL ({first_type})", flush=True)
            continue

        repair_prompt = build_repair_prompt_v3(task, trace, first_type)
        task2 = env.load_task(task_id)
        task2_repair = type(
            "Task",
            (),
            {
                "task_id": task2.task_id,
                "task_dir": task2.task_dir,
                "workspace": task2.workspace,
                "issue": repair_prompt,
                "metadata": task2.metadata,
            },
        )()
        agent2 = AgentLoop(
            model=hf,
            tools=default_tool_registry(),
            trace_logger=TraceLogger(trace_dir / "repair"),
            max_steps=args.repair_steps,
            auto_save=True,
            auto_run_tests_after_edit=hard_guard,
            max_successful_edits=max_successful_edits,
            max_total_edit_attempts=max_total_edit_attempts,
        )
        trace2 = agent2.run(task2_repair)
        if trace2.success:
            repair_ok += 1
            details.append({"task_id": task_id, "result": "repair_ok", "failure_type": first_type})
            print(f"  {task_id}: REPAIR OK ({first_type})", flush=True)
        else:
            final_type = classify_failure(trace2)
            failure_final[final_type] = failure_final.get(final_type, 0) + 1
            details.append(
                {"task_id": task_id, "result": "repair_fail", "failure_type": first_type, "final_type": final_type}
            )
            print(f"  {task_id}: REPAIR FAIL ({first_type} -> {final_type})", flush=True)

    total = len(tasks)
    final = first_ok + repair_ok
    results = {
        "model": model_name,
        "base_model": args.base_model,
        "adapter_path": args.adapter_path,
        "tasks": total,
        "task_range": [args.start, args.end],
        "hard_guard": hard_guard,
        "repair": not args.no_repair,
        "max_successful_edits": max_successful_edits,
        "max_total_edit_attempts": max_total_edit_attempts,
        "first_pass_success": first_ok,
        "repair_success": repair_ok,
        "final_success": final,
        "first_pass_rate": first_ok / total if total else 0,
        "final_rate": final / total if total else 0,
        "failure_first": failure_first,
        "failure_final": failure_final,
        "details": details,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 70)
    print("7B WORKFLOW ALIGNMENT EVAL")
    print("=" * 70)
    print(f"Model: {model_name}")
    print(f"Total: {total}")
    print(f"First-pass: {first_ok}/{total} ({100*first_ok/total:.1f}%)")
    print(f"Repair: +{repair_ok}")
    print(f"Final: {final}/{total} ({100*final/total:.1f}%)")
    print(f"First failures: {failure_first}")
    print(f"Final failures: {failure_final}")
    print(f"Saved: {output_dir / 'results.json'}")


if __name__ == "__main__":
    main()

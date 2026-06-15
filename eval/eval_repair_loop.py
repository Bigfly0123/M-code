"""Phase 7: Verifier-Guided Repair eval on New100.

Compares:
  A: single-pass (v2.1-clean)
  B: single-pass + one repair attempt with test feedback
"""
import json, os, torch, subprocess
from pathlib import Path

os.environ["TMPDIR"] = str(Path(__file__).resolve().parent / ".tmp")

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.harness.action_parser import parse_action, ActionParseError
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger


class HFModel(Model):
    def __init__(self, model, tokenizer, name):
        self.model = model
        self.tokenizer = tokenizer
        self.name = name

    def generate(self, prompt):
        msgs = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inp = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(**inp, max_new_tokens=2048, do_sample=False,
                                      eos_token_id=self.tokenizer.eos_token_id)
        return self.tokenizer.decode(out[0][inp["input_ids"].shape[1]:], skip_special_tokens=True)


def classify_failure(trace):
    """Classify failure from trace."""
    if trace.success:
        return "SUCCESS"
    has_edit = False
    has_tests = False
    test_passed = False
    for s in trace.steps:
        a = s.action if hasattr(s, "action") else {}
        name = a.get("name", "") if isinstance(a, dict) else ""
        if name == "edit_file":
            has_edit = True
        if name == "run_tests":
            has_tests = True
            obs = str(s.observation if hasattr(s, "observation") else "")
            if "passed" in obs.lower() or "PASSED" in obs:
                test_passed = True
    if not has_edit:
        return "NO_EDIT"
    if has_edit and not has_tests:
        return "NO_TEST_AFTER_EDIT"
    if has_edit and has_tests and not test_passed:
        return "TEST_STILL_FAIL"
    return "OTHER"


def build_repair_prompt(task, trace):
    """Build repair prompt with test failure feedback."""
    # Get last test output
    test_output = ""
    last_edit = ""
    diff_info = ""
    for s in trace.steps:
        a = s.action if hasattr(s, "action") else {}
        name = a.get("name", "") if isinstance(a, dict) else ""
        obs = str(s.observation if hasattr(s, "observation") else "")
        if name == "run_tests":
            test_output = obs[:500]
        if name == "edit_file":
            last_edit = json.dumps(a, ensure_ascii=False)[:300]
        if name == "git_diff":
            diff_info = obs[:500]

    failure_type = classify_failure(trace)

    prompt = f"""You attempted to fix the bug, but the fix was not correct.

Task:
{task.issue}

Your previous edit:
{last_edit}

Test failure output:
{test_output[:400]}

Failure type: {failure_type}

Repair instruction:
- Focus on fixing the remaining test failure
- Do NOT modify the test files
- Keep the patch minimal - only change what is needed
- Read the source file again if needed to see the current state
- After editing, run tests to verify

Respond with JSON: {{"thought": "...", "action": "...", "arguments": {{...}}}}"""

    return prompt


def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "eval_workspaces")

    # New100 tasks
    tasks = sorted([p.name for p in tasks_root.iterdir()
                   if p.is_dir() and p.name.startswith("bugfix_")
                   and 251 <= int(p.name.split("_")[1]) <= 350])
    print(f"New100 tasks: {len(tasks)}")

    # Load model
    base_path = "/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct"
    adapter_path = str(root / "outputs" / "models" / "3b_step_sft_v21_clean")
    tok = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    base = AutoModelForCausalLM.from_pretrained(base_path, quantization_config=bnb,
                                                device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(base, adapter_path)
    hf = HFModel(model, tok, "v21_clean")

    first_pass_success = 0
    repair_success = 0
    final_success = 0
    failure_types_first = {"NO_EDIT": 0, "TEST_STILL_FAIL": 0, "OTHER": 0}
    failure_types_repair = {"NO_EDIT": 0, "TEST_STILL_FAIL": 0, "OTHER": 0}
    repair_gains = []

    trace_dir = root / "outputs" / "reports" / "repair_eval" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    for i, tid in enumerate(tasks):
        task = env.load_task(tid)

        # First pass
        agent = AgentLoop(model=hf, tools=default_tool_registry(),
                         trace_logger=TraceLogger(trace_dir / "first"),
                         max_steps=10, auto_save=True)
        trace = agent.run(task)

        if trace.success:
            first_pass_success += 1
            final_success += 1
            print(f"  {tid}: FIRST_PASS OK", flush=True)
            repair_gains.append({"task_id": tid, "first_pass": True, "repair_needed": False})
            continue

        # First pass failed - classify
        ft = classify_failure(trace)
        failure_types_first[ft] = failure_types_first.get(ft, 0) + 1

        # Build repair prompt
        repair_prompt = build_repair_prompt(task, trace)

        # Reset environment for repair
        task2 = env.load_task(tid)

        # Second pass with repair prompt
        agent2 = AgentLoop(model=hf, tools=default_tool_registry(),
                          trace_logger=TraceLogger(trace_dir / "repair"),
                          max_steps=8, auto_save=True)
        # Override the task issue with repair prompt
        task2_repair = type('Task', (), {
            'task_id': task2.task_id,
            'task_dir': task2.task_dir,
            'workspace': task2.workspace,
            'issue': repair_prompt,
            'metadata': task2.metadata,
        })()

        trace2 = agent2.run(task2_repair)

        if trace2.success:
            repair_success += 1
            final_success += 1
            print(f"  {tid}: REPAIR OK (was {ft})", flush=True)
            repair_gains.append({"task_id": tid, "first_pass": False, "repair_needed": True, "repair_success": True, "failure_type": ft})
        else:
            ft2 = classify_failure(trace2)
            failure_types_repair[ft2] = failure_types_repair.get(ft2, 0) + 1
            print(f"  {tid}: REPAIR FAIL ({ft} -> {ft2})", flush=True)
            repair_gains.append({"task_id": tid, "first_pass": False, "repair_needed": True, "repair_success": False, "failure_type_first": ft, "failure_type_repair": ft2})

    # Summary
    total = len(tasks)
    print(f"\n{'='*60}")
    print(f"VERIFIER-GUIDED REPAIR RESULTS (New100)")
    print(f"{'='*60}")
    print(f"Total tasks: {total}")
    print(f"First-pass success: {first_pass_success}/{total} ({100*first_pass_success/total:.1f}%)")
    print(f"Repair success: {repair_success}/{total} ({100*repair_success/total:.1f}%)")
    print(f"Final success: {final_success}/{total} ({100*final_success/total:.1f}%)")
    print(f"Repair gain: +{repair_success} tasks (+{100*repair_success/total:.1f}%)")
    print(f"\nFirst-pass failures: {failure_types_first}")
    print(f"Repair failures: {failure_types_repair}")

    # Save
    results = {
        "total": total,
        "first_pass_success": first_pass_success,
        "repair_success": repair_success,
        "final_success": final_success,
        "repair_gain": repair_success,
        "first_pass_rate": first_pass_success / total,
        "final_rate": final_success / total,
        "failure_types_first": failure_types_first,
        "failure_types_repair": failure_types_repair,
        "details": repair_gains,
    }
    out = root / "outputs" / "reports" / "repair_eval" / "repair_eval_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()

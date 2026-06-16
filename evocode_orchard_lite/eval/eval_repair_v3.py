"""Phase 7.2: Repair v3 with OTHER sub-type-specific prompts.

Key change from v2: OTHER prompt now focuses on expected vs actual comparison,
targeting PATCH_WRONG_LOGIC (68% of OTHER failures).
"""
import json, os, re, torch
from pathlib import Path

os.environ["TMPDIR"] = str(Path(__file__).resolve().parents[2] / ".tmp")

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger

_JSON_EXAMPLE = 'Respond with JSON: {"thought": "...", "action": "...", "arguments": {...}}'


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


def get_test_output(trace):
    for s in reversed(trace.steps):
        a = s.action if hasattr(s, "action") else {}
        name = a.get("name", "") if isinstance(a, dict) else ""
        if name == "run_tests":
            return str(s.observation if hasattr(s, "observation") else "")[:600]
    return ""


def extract_failure_details(test_output):
    """Extract specific failure info from pytest output."""
    # Try to find FAILED assertion details
    lines = test_output.split('\n')
    failure_lines = []
    capture = False
    for line in lines:
        if 'FAILED' in line or 'FAIL' in line:
            capture = True
        if capture:
            failure_lines.append(line)
            if len(failure_lines) > 8:
                break
        if 'short test summary' in line:
            capture = True
    return '\n'.join(failure_lines[:8]) if failure_lines else test_output[:400]


def build_repair_prompt_v3(task, trace, failure_type):
    """Build failure-type-specific repair prompt with v3 OTHER handling."""
    test_output = get_test_output(trace)
    failure_details = extract_failure_details(test_output)
    last_edit = ""
    for s in trace.steps:
        a = s.action if hasattr(s, "action") else {}
        if isinstance(a, dict) and a.get("name") == "edit_file":
            last_edit = json.dumps(a, ensure_ascii=False)[:300]

    base_instruction = f"""You attempted to fix the bug but tests still fail.

Task:
{task.issue}

Test failure details:
{failure_details[:400]}

Previous edit:
{last_edit}
"""

    if failure_type == "NO_EDIT":
        return base_instruction + """
CRITICAL: You MUST make a source-code edit. Do not only explain the issue.
- Read the source file to see the current code
- Identify the specific line that needs to change
- Use edit_file to apply a minimal fix
- Then run tests
You must not stop without making an edit.

""" + _JSON_EXAMPLE

    elif failure_type == "TEST_STILL_FAIL":
        return base_instruction + """Your previous patch did not fix the test failure.
- Read the test failure output carefully
- Compare your edit with the expected behavior
- The old text may not match exactly - re-read the file
- Make a different, more targeted fix
- Do NOT modify tests

""" + _JSON_EXAMPLE

    elif failure_type == "OTHER":
        # v3: Focus on expected vs actual, targeting PATCH_WRONG_LOGIC
        return base_instruction + """Your fix was applied but is logically incorrect.

ANALYSIS STEPS:
1. Read the failing test to see what it expects (the expected value)
2. Read your code to see what it actually returns (the actual value)
3. Ask: what specific condition or check is MISSING?
4. Apply ONLY the missing logic - do not rewrite working code

Common patterns you might be missing:
- A boundary check (e.g., range validation, empty input)
- A format conversion (e.g., lowercase, normalization)
- An edge case (e.g., midnight crossing, leap year, special characters)
- A missing branch (e.g., 3-digit vs 6-digit hex, quoted vs unquoted)

Focus on the GAP between expected and actual. Fix ONLY that gap.

""" + _JSON_EXAMPLE

    else:
        return base_instruction + """Repair the failing tests by editing the source code.
- Do NOT modify tests
- Keep the patch minimal
- Run tests after editing

""" + _JSON_EXAMPLE


def build_forced_edit_prompt(task, trace):
    test_output = get_test_output(trace)
    return f"""Your previous repair attempt made no code edit.
This task requires a source-code change.

Task:
{task.issue}

Test output:
{test_output[:300]}

You MUST now:
1. Read the source file
2. Identify the buggy line
3. Apply one minimal edit_file
4. Run tests

Do not explain. Do not stop without editing.

""" + _JSON_EXAMPLE


def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "eval_workspaces")

    tasks = sorted([p.name for p in tasks_root.iterdir()
                   if p.is_dir() and p.name.startswith("bugfix_")
                   and 251 <= int(p.name.split("_")[1]) <= 350])
    print(f"New100 tasks: {len(tasks)}")

    base_path = "/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct"
    adapter_path = str(root / "outputs" / "models" / "3b_step_sft_v21_clean")
    tok = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    base = AutoModelForCausalLM.from_pretrained(base_path, quantization_config=bnb,
                                                device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(base, adapter_path)
    hf = HFModel(model, tok, "v21_clean")

    first_pass_ok = 0
    repair_ok = 0
    forced_edit_ok = 0
    failure_first = {"NO_EDIT": 0, "TEST_STILL_FAIL": 0, "OTHER": 0}
    failure_repair = {"NO_EDIT": 0, "TEST_STILL_FAIL": 0, "OTHER": 0}
    details = []

    trace_dir = root / "outputs" / "reports" / "repair_v3_eval" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    for tid in tasks:
        task = env.load_task(tid)

        agent = AgentLoop(model=hf, tools=default_tool_registry(),
                         trace_logger=TraceLogger(trace_dir / "first"),
                         max_steps=10, auto_save=True)
        trace = agent.run(task)

        if trace.success:
            first_pass_ok += 1
            print(f"  {tid}: FIRST_PASS OK", flush=True)
            details.append({"task_id": tid, "result": "first_pass_ok"})
            continue

        ft = classify_failure(trace)
        failure_first[ft] = failure_first.get(ft, 0) + 1

        repair_prompt = build_repair_prompt_v3(task, trace, ft)

        task2 = env.load_task(tid)
        task2_repair = type('Task', (), {
            'task_id': task2.task_id, 'task_dir': task2.task_dir,
            'workspace': task2.workspace, 'issue': repair_prompt, 'metadata': task2.metadata,
        })()

        agent2 = AgentLoop(model=hf, tools=default_tool_registry(),
                          trace_logger=TraceLogger(trace_dir / "repair"),
                          max_steps=8, auto_save=True)
        trace2 = agent2.run(task2_repair)

        if trace2.success:
            repair_ok += 1
            print(f"  {tid}: REPAIR OK ({ft})", flush=True)
            details.append({"task_id": tid, "result": "repair_ok", "failure_type": ft})
            continue

        ft2 = classify_failure(trace2)
        if ft2 == "NO_EDIT":
            forced_prompt = build_forced_edit_prompt(task, trace2)
            task3 = env.load_task(tid)
            task3_forced = type('Task', (), {
                'task_id': task3.task_id, 'task_dir': task3.task_dir,
                'workspace': task3.workspace, 'issue': forced_prompt, 'metadata': task3.metadata,
            })()

            agent3 = AgentLoop(model=hf, tools=default_tool_registry(),
                              trace_logger=TraceLogger(trace_dir / "forced"),
                              max_steps=6, auto_save=True)
            trace3 = agent3.run(task3_forced)

            if trace3.success:
                forced_edit_ok += 1
                print(f"  {tid}: FORCED_EDIT OK ({ft} -> NO_EDIT -> SUCCESS)", flush=True)
                details.append({"task_id": tid, "result": "forced_edit_ok", "failure_type": ft})
                continue
            ft3 = classify_failure(trace3)
            failure_repair[ft3] = failure_repair.get(ft3, 0) + 1
            print(f"  {tid}: FAIL ({ft} -> {ft2} -> {ft3})", flush=True)
            details.append({"task_id": tid, "result": "fail", "ft_first": ft, "ft_repair": ft2, "ft_forced": ft3})
        else:
            failure_repair[ft2] = failure_repair.get(ft2, 0) + 1
            print(f"  {tid}: REPAIR FAIL ({ft} -> {ft2})", flush=True)
            details.append({"task_id": tid, "result": "repair_fail", "failure_type": ft, "ft_repair": ft2})

    total = len(tasks)
    final = first_pass_ok + repair_ok + forced_edit_ok
    print(f"\n{'='*60}")
    print(f"REPAIR v3 + OTHER DECOMPOSITION RESULTS (New100)")
    print(f"{'='*60}")
    print(f"Total: {total}")
    print(f"First-pass: {first_pass_ok} ({100*first_pass_ok/total:.1f}%)")
    print(f"Repair: +{repair_ok}")
    print(f"Forced-edit: +{forced_edit_ok}")
    print(f"Final: {final}/{total} ({100*final/total:.1f}%)")
    print(f"\nFirst-pass failures: {failure_first}")
    print(f"Repair failures: {failure_repair}")

    results = {
        "total": total,
        "first_pass_success": first_pass_ok,
        "repair_success": repair_ok,
        "forced_edit_success": forced_edit_ok,
        "final_success": final,
        "final_rate": final / total,
        "failure_first": failure_first,
        "failure_repair": failure_repair,
        "details": details,
    }
    out = root / "outputs" / "reports" / "repair_v3_eval" / "results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()

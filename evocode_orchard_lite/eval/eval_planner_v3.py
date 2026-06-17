"""Phase 8.1: Planner-Guided Coding + Repair v3.

Experiment design (4 groups on Independent50):
  A. 3B single-pass (baseline)
  B. 3B + Repair v3 (existing)
  C. Planner-guided 3B single-pass
  D. Planner-guided 3B + Repair v3

This script runs groups C and D (planner-guided).
Groups A and B already have results from repair_v3_gen.
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


# ============================================================
# Rule Planner: extract plan from issue text
# ============================================================

def rule_planner(task):
    """Extract structured plan from task issue description.

    Does NOT use metadata.target_files (that would be cheating).
    Extracts information purely from the issue text.
    """
    issue = task.issue

    # Extract function/class names from backtick-quoted text
    symbols = re.findall(r'`(\w+(?:\.\w+)*)`', issue)
    # Deduplicate, keep order
    seen = set()
    symbols = [s for s in symbols if not (s in seen or seen.add(s))]

    # Extract test file from "Run:" line
    test_file = ""
    run_match = re.search(r'python\s+-m\s+pytest\s+(\S+)', issue)
    if run_match:
        test_file = run_match.group(1)

    # Extract test file name for search
    test_name = ""
    if test_file:
        test_name = Path(test_file).stem  # e.g., "test_safe_json"

    # Infer source file names from function names and test names
    # Common patterns: test_X.py -> X.py, test_X.py -> X.py
    suspected_files = []
    if test_name:
        # test_safe_json -> safe_json
        source_stem = test_name.replace("test_", "")
        suspected_files.append(f"{source_stem}.py")

    # Build search queries from symbols
    search_queries = list(set(symbols[:5]))  # Top 5 unique symbols

    # Build repair plan
    plan_steps = []
    if test_file:
        plan_steps.append(f"Read the test file {test_file} to understand expected behavior.")
    if suspected_files:
        plan_steps.append(f"Read the suspected source file {suspected_files[0]} to see current code.")
    if symbols:
        plan_steps.append(f"Find the function(s): {', '.join(symbols[:3])}.")
    plan_steps.append("Make a minimal source-code edit to fix the bug.")
    plan_steps.append("Run tests to verify.")

    plan = {
        "suspected_files": suspected_files,
        "symbols": symbols[:5],
        "search_queries": search_queries,
        "test_file": test_file,
        "repair_plan": plan_steps,
        "do_not": [
            "Do not modify test files.",
            "Do not stop after only reading files. You MUST make an edit."
        ]
    }
    return plan


def build_planner_prompt(task, plan):
    """Build the initial planner-guided prompt for the coder."""
    plan_json = json.dumps(plan, indent=2, ensure_ascii=False)
    return f"""You are a code repair agent. Fix the bug described below.

Task:
{task.issue}

Here is a structured plan to help you:
{plan_json}

Follow the plan steps. Start by reading the suspected source file, then make a minimal edit.
After editing, run tests to verify.

Respond with JSON: {{"thought": "...", "action": "...", "arguments": {{...}}}}"""


# ============================================================
# Repair prompts (same as Repair v3)
# ============================================================

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
CRITICAL: You MUST make a source-code edit.
- Read the source file to see the current code
- Identify the specific line that needs to change
- Use edit_file to apply a minimal fix
- Then run tests

""" + _JSON_EXAMPLE

    elif failure_type == "TEST_STILL_FAIL":
        return base_instruction + """Your previous patch did not fix the test failure.
- Read the test failure output carefully
- Compare your edit with the expected behavior
- Make a different, more targeted fix
- Do NOT modify tests

""" + _JSON_EXAMPLE

    elif failure_type == "OTHER":
        return base_instruction + """Your fix was applied but is logically incorrect.

ANALYSIS STEPS:
1. Read the failing test to see what it expects
2. Read your code to see what it actually returns
3. Ask: what specific condition or check is MISSING?
4. Apply ONLY the missing logic

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


# ============================================================
# HF Model wrapper
# ============================================================

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


# ============================================================
# Main eval
# ============================================================

def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "eval_workspaces")

    # Independent50: bugfix_351-400
    tasks = sorted([p.name for p in tasks_root.iterdir()
                   if p.is_dir() and p.name.startswith("bugfix_")
                   and 351 <= int(p.name.split("_")[1]) <= 400])
    print(f"Independent50 tasks: {len(tasks)}")

    base_path = "/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct"
    adapter_path = str(root / "outputs" / "models" / "3b_step_sft_v21_clean")
    tok = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    base_model = AutoModelForCausalLM.from_pretrained(base_path, quantization_config=bnb,
                                                device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(base_model, adapter_path)
    hf = HFModel(model, tok, "v21_clean")

    # Metrics
    first_pass_ok = 0
    repair_ok = 0
    forced_edit_ok = 0
    failure_first = {"NO_EDIT": 0, "TEST_STILL_FAIL": 0, "OTHER": 0}
    failure_repair = {"NO_EDIT": 0, "TEST_STILL_FAIL": 0, "OTHER": 0}
    details = []
    plans = []

    trace_dir = root / "outputs" / "reports" / "planner_v3_eval" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    for tid in tasks:
        task = env.load_task(tid)

        # Step 1: Rule Planner
        plan = rule_planner(task)
        plans.append({"task_id": tid, "plan": plan})

        # Step 2: Planner-guided first pass
        planner_prompt = build_planner_prompt(task, plan)

        # Create a modified task with planner prompt
        task_guided = type('Task', (), {
            'task_id': task.task_id, 'task_dir': task.task_dir,
            'workspace': task.workspace, 'issue': planner_prompt, 'metadata': task.metadata,
        })()

        agent = AgentLoop(model=hf, tools=default_tool_registry(),
                         trace_logger=TraceLogger(trace_dir / "first"),
                         max_steps=10, auto_save=True)
        trace = agent.run(task_guided)

        if trace.success:
            first_pass_ok += 1
            print(f"  {tid}: FIRST_PASS OK (planner)", flush=True)
            details.append({"task_id": tid, "result": "first_pass_ok", "planner": True})
            continue

        ft = classify_failure(trace)
        failure_first[ft] = failure_first.get(ft, 0) + 1

        # Step 3: Repair v3
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
            details.append({"task_id": tid, "result": "repair_ok", "failure_type": ft, "planner": True})
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
                details.append({"task_id": tid, "result": "forced_edit_ok", "failure_type": ft, "planner": True})
                continue
            ft3 = classify_failure(trace3)
            failure_repair[ft3] = failure_repair.get(ft3, 0) + 1
            print(f"  {tid}: FAIL ({ft} -> {ft2} -> {ft3})", flush=True)
            details.append({"task_id": tid, "result": "fail", "ft_first": ft, "ft_repair": ft2, "ft_forced": ft3, "planner": True})
        else:
            failure_repair[ft2] = failure_repair.get(ft2, 0) + 1
            print(f"  {tid}: REPAIR FAIL ({ft} -> {ft2})", flush=True)
            details.append({"task_id": tid, "result": "repair_fail", "failure_type": ft, "ft_repair": ft2, "planner": True})

    total = len(tasks)
    final = first_pass_ok + repair_ok + forced_edit_ok
    print(f"\n{'='*60}")
    print(f"PLANNER-GUIDED + REPAIR v3 (Independent50)")
    print(f"{'='*60}")
    print(f"Total: {total}")
    print(f"First-pass (planner): {first_pass_ok} ({100*first_pass_ok/total:.1f}%)")
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
    out = root / "outputs" / "reports" / "planner_v3_eval" / "results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))

    plans_out = root / "outputs" / "reports" / "planner_v3_eval" / "plans.json"
    plans_out.write_text(json.dumps(plans, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()

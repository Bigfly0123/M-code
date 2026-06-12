"""A/B evaluation: v2.1-clean vs v2.1-clean + skill injection.

Compares performance on New100 tasks with and without skill injection.
"""
import json, os, torch
from pathlib import Path
from collections import defaultdict
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

os.environ["TMPDIR"] = str(Path(__file__).resolve().parent / ".tmp")

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger


# Skill retrieval by keyword matching
SKILL_KEYWORDS = {
    "patch_apply_stability": ["edit", "replace", "old_text", "new_text", "patch", "indent"],
    "test_feedback_correction": ["test", "assert", "fail", "expected", "actual", "pytest"],
    "regex_parsing": ["regex", "pattern", "re.match", "re.search", "regular expression", "re.compile", "re.findall"],
    "type_conversion": ["int", "float", "str", "type", "TypeError", "ValueError", "conversion"],
    "date_time": ["date", "time", "datetime", "timedelta", "strftime", "strptime", "calendar", "leap"],
}


def retrieve_skills(issue_text, metadata):
    """Retrieve relevant skills based on issue text and metadata."""
    issue_lower = issue_text.lower()
    bug_type = metadata.get("bug_type", "").lower()

    # Direct bug_type mapping
    type_to_skill = {
        "regex": "regex_parsing",
        "type_conversion": "type_conversion",
        "date_time": "date_time",
    }
    if bug_type in type_to_skill:
        return [type_to_skill[bug_type], "patch_apply_stability"]

    # Keyword matching
    matched = []
    for skill_id, keywords in SKILL_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in issue_lower:
                matched.append(skill_id)
                break

    # Always include patch_apply_stability
    if "patch_apply_stability" not in matched:
        matched.append("patch_apply_stability")

    return list(set(matched))


def load_skill_text(skill_id, skills_dir):
    """Load skill markdown text."""
    path = skills_dir / f"{skill_id}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


class SkillInjectedModel(Model):
    """Model wrapper that injects skills into the prompt."""
    def __init__(self, model, tokenizer, skills_dir, name="skill_model"):
        self.model = model
        self.tokenizer = tokenizer
        self.skills_dir = skills_dir
        self.name = name

    def generate(self, prompt):
        # The prompt from PromptBuilder already contains the task info
        # We inject skills at the beginning
        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=2048, do_sample=False)
        return self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


class SkillInjectedPromptBuilder:
    """PromptBuilder that injects relevant skills."""
    def __init__(self, original_builder, skills_dir):
        self.original = original_builder
        self.skills_dir = skills_dir

    def build(self, task, history, tools):
        original_prompt = self.original.build(task, history, tools)

        # Retrieve relevant skills
        skills = retrieve_skills(task.issue, task.metadata)

        # Build skill injection block
        skill_text = "\n\nRelevant debugging skills:\n"
        for skill_id in skills:
            skill_content = load_skill_text(skill_id, self.skills_dir)
            if skill_content:
                # Extract key sections only (not full markdown)
                lines = skill_content.split("\n")
                key_lines = []
                in_action = False
                for line in lines:
                    if "## Action Checklist" in line:
                        in_action = True
                        key_lines.append(line)
                        continue
                    if "## Edit Guidance" in line:
                        in_action = True
                        key_lines.append(line)
                        continue
                    if "## Test Feedback" in line:
                        in_action = True
                        key_lines.append(line)
                        continue
                    if line.startswith("## ") and in_action:
                        in_action = False
                    if in_action:
                        key_lines.append(line)
                if key_lines:
                    skill_text += "\n".join(key_lines) + "\n"

        return original_prompt + skill_text


class PlainModel(Model):
    """Plain model wrapper without skill injection."""
    def __init__(self, model, tokenizer, name="plain_model"):
        self.model = model
        self.tokenizer = tokenizer
        self.name = name

    def generate(self, prompt):
        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=2048, do_sample=False)
        return self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


def run_eval(model, tasks, env, trace_dir, max_steps=10):
    traces = []
    for task_id in tasks:
        task = env.load_task(task_id)
        agent = AgentLoop(model=model, tools=default_tool_registry(),
                         trace_logger=TraceLogger(trace_dir),
                         max_steps=max_steps, auto_save=False)
        trace = agent.run(task)
        traces.append(trace)
        status = "OK" if trace.success else "FAIL"
        print(f"  {task_id}: {status}", flush=True)
    return traces


def analyze_traces(traces):
    """Compute detailed metrics."""
    total = len(traces)
    success = sum(1 for t in traces if t.success)
    no_edit = 0
    test_fail = 0
    patch_error = 0
    total_steps = 0

    for trace in traces:
        total_steps += len(trace.steps)
        if not trace.success:
            has_edit = False
            for s in trace.steps:
                a = s.action if hasattr(s, 'action') else s.get("action", {})
                if isinstance(a, dict) and a.get("name") == "edit_file":
                    has_edit = True
            if not has_edit:
                no_edit += 1
            elif trace.reward < 0:
                patch_error += 1
            else:
                test_fail += 1

    return {
        "total": total,
        "success": success,
        "success_rate": success / total if total else 0,
        "no_edit": no_edit,
        "test_still_fail": test_fail,
        "patch_apply_error": patch_error,
        "avg_steps": total_steps / total if total else 0,
    }


def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    skills_dir = root / "skills"

    # Load new100 tasks
    heldout_tasks = sorted([p.name for p in tasks_root.iterdir()
                           if p.is_dir() and p.name.startswith("bugfix_")
                           and 251 <= int(p.name.split("_")[1]) <= 350])
    print(f"New100 tasks: {len(heldout_tasks)}")

    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "eval_workspaces")

    # Load model
    base_path = "/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct"
    adapter_path = str(root / "outputs" / "models" / "3b_step_sft_v21_clean")

    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    base_model = AutoModelForCausalLM.from_pretrained(base_path, quantization_config=bnb,
                                                      device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(base_model, adapter_path)

    # A: Plain v2.1-clean
    print(f"\n{'='*60}")
    print("A: v2.1-clean (no skills)")
    print(f"{'='*60}")
    plain = PlainModel(model, tokenizer, name="v21_clean_plain")
    traces_a = run_eval(plain, heldout_tasks, env, root / "outputs" / "reports" / "ab_test" / "plain")
    metrics_a = analyze_traces(traces_a)

    # B: v2.1-clean + skill injection
    print(f"\n{'='*60}")
    print("B: v2.1-clean + skills")
    print(f"{'='*60}")
    skill_model = SkillInjectedModel(model, tokenizer, skills_dir, name="v21_clean_skills")

    # Override prompt builder in AgentLoop for skill injection
    from evocode_orchard_lite.harness.prompt_builder import PromptBuilder
    original_builder = PromptBuilder()
    skill_builder = SkillInjectedPromptBuilder(original_builder, skills_dir)

    traces_b = []
    trace_dir_b = root / "outputs" / "reports" / "ab_test" / "skills"
    trace_dir_b.mkdir(parents=True, exist_ok=True)

    for task_id in heldout_tasks:
        task = env.load_task(task_id)
        # Build skill-injected prompt manually
        skills = retrieve_skills(task.issue, task.metadata)
        skill_text = "\n\nRelevant debugging skills:\n"
        for skill_id in skills:
            path = skills_dir / f"{skill_id}.md"
            if path.exists():
                content = path.read_text(encoding="utf-8")
                # Extract checklist and guidance sections
                sections = []
                current_section = None
                for line in content.split("\n"):
                    if "## Action Checklist" in line or "## Edit Guidance" in line or "## Test Feedback" in line:
                        current_section = line
                        sections.append(line)
                    elif current_section and line.startswith("## "):
                        current_section = None
                    elif current_section:
                        sections.append(line)
                if sections:
                    skill_text += "\n".join(sections) + "\n\n"

        # Use AgentLoop with plain model but inject skills into task issue
        task_with_skills = type('Task', (), {
            'task_id': task.task_id,
            'task_dir': task.task_dir,
            'workspace': task.workspace,
            'issue': task.issue + skill_text,
            'metadata': task.metadata,
        })()

        agent = AgentLoop(model=skill_model, tools=default_tool_registry(),
                         trace_logger=TraceLogger(trace_dir_b),
                         max_steps=10, auto_save=False)
        trace = agent.run(task_with_skills)
        traces_b.append(trace)
        status = "OK" if trace.success else "FAIL"
        print(f"  {task_id}: {status}", flush=True)

    metrics_b = analyze_traces(traces_b)

    # Print comparison
    print(f"\n{'='*60}")
    print("A/B COMPARISON")
    print(f"{'='*60}")
    print(f"{'Metric':<25} {'A (plain)':>12} {'B (+skills)':>12} {'Delta':>8}")
    print("-" * 60)
    for key, label in [("success_rate", "Success"), ("no_edit", "NO_EDIT"), ("test_still_fail", "TEST_FAIL"), ("patch_apply_error", "PATCH_ERR"), ("avg_steps", "Avg Steps")]:
        va = metrics_a[key]
        vb = metrics_b[key]
        if key == "success_rate":
            print(f"{label:<25} {va:>11.1%} {vb:>11.1%} {vb-va:>+7.1%}")
        elif key == "avg_steps":
            print(f"{label:<25} {va:>12.1f} {vb:>12.1f} {vb-va:>+8.1f}")
        else:
            print(f"{label:<25} {va:>12} {vb:>12} {vb-va:>+8}")

    # Save results
    results = {"A_plain": metrics_a, "B_skills": metrics_b}
    out_path = root / "outputs" / "reports" / "ab_test" / "ab_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()

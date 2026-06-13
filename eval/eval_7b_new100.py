"""Evaluate 7B models on New100 held-out tasks."""
import json, os, torch
from pathlib import Path
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

os.environ["TMPDIR"] = str(Path(__file__).resolve().parent / ".tmp")

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger


class LocalHFModel(Model):
    def __init__(self, model, tokenizer, name="local"):
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


def run_eval(model, tasks, env, trace_dir):
    traces = []
    for tid in tasks:
        task = env.load_task(tid)
        agent = AgentLoop(model=model, tools=default_tool_registry(),
                         trace_logger=TraceLogger(trace_dir), max_steps=10, auto_save=False)
        trace = agent.run(task)
        traces.append(trace)
        s = "OK" if trace.success else "FAIL"
        print(f"  {tid}: {s}", flush=True)
    return traces


def analyze(traces):
    total = len(traces)
    success = sum(1 for t in traces if t.success)
    no_edit = 0
    test_fail = 0
    patch_err = 0
    total_steps = 0
    for t in traces:
        total_steps += len(t.steps)
        if not t.success:
            has_edit = any(s.action.get("name") == "edit_file" if isinstance(s.action, dict) else False for s in t.steps)
            if not has_edit:
                no_edit += 1
            elif t.reward < 0:
                patch_err += 1
            else:
                test_fail += 1
    return {
        "total": total,
        "success": success,
        "success_rate": success / total,
        "no_edit": no_edit,
        "test_fail": test_fail,
        "patch_error": patch_err,
        "avg_steps": total_steps / total,
    }


def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "eval_workspaces")

    # New100 tasks
    tasks = sorted([p.name for p in tasks_root.iterdir()
                   if p.is_dir() and p.name.startswith("bugfix_")
                   and 251 <= int(p.name.split("_")[1]) <= 350])
    print(f"New100 tasks: {len(tasks)}")

    model_7b = "/mnt/disk/mxf/models/Qwen2.5-Coder-7B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_7b, trust_remote_code=True)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)

    results = {}

    # 7B Base
    print("\n=== 7B Base ===")
    base = AutoModelForCausalLM.from_pretrained(model_7b, quantization_config=bnb,
                                                device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    hf = LocalHFModel(base, tokenizer, "7b_base")
    traces = run_eval(hf, tasks, env, root / "outputs" / "reports" / "7b_new100_eval" / "7b_base")
    results["7b_base"] = analyze(traces)
    print(f"  Success: {results['7b_base']['success_rate']:.1%}")
    del base, hf
    torch.cuda.empty_cache()

    # 7B Step-SFT v2
    print("\n=== 7B Step-SFT v2 ===")
    base = AutoModelForCausalLM.from_pretrained(model_7b, quantization_config=bnb,
                                                device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    v2 = PeftModel.from_pretrained(base, str(root / "outputs" / "models" / "7b_step_sft_v2"))
    hf = LocalHFModel(v2, tokenizer, "7b_sft_v2")
    traces = run_eval(hf, tasks, env, root / "outputs" / "reports" / "7b_new100_eval" / "7b_sft_v2")
    results["7b_sft_v2"] = analyze(traces)
    print(f"  Success: {results['7b_sft_v2']['success_rate']:.1%}")
    del v2, base, hf
    torch.cuda.empty_cache()

    # 7B v2.1-clean
    print("\n=== 7B v2.1-clean ===")
    base = AutoModelForCausalLM.from_pretrained(model_7b, quantization_config=bnb,
                                                device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    v21 = PeftModel.from_pretrained(base, str(root / "outputs" / "models" / "7b_v21_clean"))
    hf = LocalHFModel(v21, tokenizer, "7b_v21_clean")
    traces = run_eval(hf, tasks, env, root / "outputs" / "reports" / "7b_new100_eval" / "7b_v21_clean")
    results["7b_v21_clean"] = analyze(traces)
    print(f"  Success: {results['7b_v21_clean']['success_rate']:.1%}")
    del v21, base, hf
    torch.cuda.empty_cache()

    # Print comparison
    print(f"\n{'='*60}")
    print("7B SAME-PIPELINE COMPARISON (New100)")
    print(f"{'='*60}")
    print(f"{'Model':<20} {'Success':>8} {'NO_EDIT':>8} {'TEST_FAIL':>10} {'PATCH_ERR':>10} {'AvgSteps':>9}")
    print("-" * 60)
    for name in ["7b_base", "7b_sft_v2", "7b_v21_clean"]:
        m = results[name]
        print(f"{name:<20} {m['success_rate']:>7.1%} {m['no_edit']:>8} {m['test_fail']:>10} {m['patch_error']:>10} {m['avg_steps']:>9.1f}")

    # Save
    out = root / "outputs" / "reports" / "7b_new100_eval" / "7b_comparison.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()

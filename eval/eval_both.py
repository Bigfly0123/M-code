"""Run Base and SFT evaluation in parallel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.eval.metrics import summarize_traces
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.schema import Trace
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger


class LocalHFModel(Model):
    def __init__(self, model, tokenizer, name="local_model"):
        self.model = model
        self.tokenizer = tokenizer
        self.name = name

    def generate(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=2048, do_sample=False)
        response = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return response


def run_eval(model, tasks, env, trace_logger, max_steps=10):
    traces = []
    for task_id in tasks:
        print(f"  [{model.name}] Running {task_id}...")
        task = env.load_task(task_id)
        agent = AgentLoop(model=model, tools=default_tool_registry(), trace_logger=trace_logger, max_steps=max_steps, auto_save=False)
        trace = agent.run(task)
        trace.run_id = f"eval_{model.name}"
        trace.rollout_id = "0000"
        trace_logger.save(trace)
        traces.append(trace)
        status = "SUCCESS" if trace.success else "FAILED"
        print(f"    [{model.name}] {status} | reward={trace.reward:.2f} | steps={len(trace.steps)}")
    return traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", type=str, default="/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--sft_adapter", type=str, default="outputs/models/sft_qwen_3b_v2")
    parser.add_argument("--tasks_file", type=str, default="outputs/data/splits/test_tasks.txt")
    parser.add_argument("--max_steps", type=int, default=10)
    parser.add_argument("--output_dir", type=str, default="outputs/reports")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = [l.strip() for l in open(root / args.tasks_file).readlines() if l.strip()]
    print(f"Evaluating on {len(tasks)} tasks")

    env = CodeRepairEnv(tasks_root=root / "benchmark" / "tasks", workspaces_root=root / "outputs" / "eval_workspaces")

    # Load base model
    print("\n=== Loading Base Model ===")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(args.base_model, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    base_hf = LocalHFModel(base_model, tokenizer, name="base")

    # Run base eval
    print("\n=== Base Model Evaluation ===")
    base_traces = run_eval(base_hf, tasks, env, TraceLogger(output_dir / "eval_base"), args.max_steps)
    base_stats = summarize_traces(base_traces)
    print(f"Base success rate: {base_stats['task_success_rate']:.2%}")

    # Load SFT adapter
    print("\n=== Loading SFT Model ===")
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    sft_base = AutoModelForCausalLM.from_pretrained(args.base_model, quantization_config=bnb_config, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    sft_model = PeftModel.from_pretrained(sft_base, str(root / args.sft_adapter))
    sft_hf = LocalHFModel(sft_model, tokenizer, name="sft")

    # Run SFT eval
    print("\n=== SFT Model Evaluation ===")
    sft_traces = run_eval(sft_hf, tasks, env, TraceLogger(output_dir / "eval_sft"), args.max_steps)
    sft_stats = summarize_traces(sft_traces)
    print(f"SFT success rate: {sft_stats['task_success_rate']:.2%}")

    # Generate report
    lines = ["# Base vs SFT Report", "", "| Metric | Base | SFT | Delta |", "|---|---:|---:|---:|"]
    for m in ["task_success_rate", "test_pass_rate", "tool_valid_rate", "format_error_rate", "avg_steps"]:
        b, s = base_stats.get(m, 0), sft_stats.get(m, 0)
        lines.append(f"| {m} | {b:.4f} | {s:.4f} | {s-b:+.4f} |")
    lines.extend(["", "## Failure Counts", "", "### Base"])
    for ft, c in sorted(base_stats.get("failure_counts", {}).items(), key=lambda x: -x[1]):
        lines.append(f"| {ft} | {c} |")
    lines.extend(["", "### SFT"])
    for ft, c in sorted(sft_stats.get("failure_counts", {}).items(), key=lambda x: -x[1]):
        lines.append(f"| {ft} | {c} |")

    report_path = output_dir / "base_vs_sft_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    stats = {"base_stats": base_stats, "sft_stats": sft_stats}
    (output_dir / "base_vs_sft_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"\n=== Results ===")
    print(f"Base: {base_stats['task_success_rate']:.2%}")
    print(f"SFT: {sft_stats['task_success_rate']:.2%}")
    print(f"Delta: {sft_stats['task_success_rate'] - base_stats['task_success_rate']:+.2%}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()

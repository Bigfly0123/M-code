"""Evaluate Step-SFT v2 with Runtime Guard."""
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", type=str, default="/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--sft_adapter", type=str, default="outputs/models/3b_step_sft_v2")
    parser.add_argument("--tasks_file", type=str, default="outputs/data/splits/test_tasks.txt")
    parser.add_argument("--max_steps", type=int, default=10)
    parser.add_argument("--output_dir", type=str, default="outputs/reports/eval_3b_step_sft_v2_guard")
    parser.add_argument("--num_tasks", type=int, default=28)
    parser.add_argument("--use_guard", action="store_true", default=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = [l.strip() for l in open(root / args.tasks_file).readlines() if l.strip()][:args.num_tasks]
    print(f"Testing 3B Step-SFT v2 with guard on {len(tasks)} tasks")

    env = CodeRepairEnv(tasks_root=root / "benchmark" / "tasks", workspaces_root=root / "outputs" / "eval_workspaces")

    # Load SFT model
    print(f"Loading SFT model: {args.base_model} + {args.sft_adapter}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    base_model = AutoModelForCausalLM.from_pretrained(args.base_model, quantization_config=bnb_config, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    sft_model = PeftModel.from_pretrained(base_model, str(root / args.sft_adapter))
    model = LocalHFModel(sft_model, tokenizer, name="qwen2.5-coder-3b-step-sft-guard")

    # Run eval
    print(f"Running evaluation with guard={args.use_guard}...")
    trace_logger = TraceLogger(output_dir)
    traces = []
    for task_id in tasks:
        print(f"  Running {task_id}...")
        task = env.load_task(task_id)
        agent = AgentLoop(
            model=model,
            tools=default_tool_registry(),
            trace_logger=trace_logger,
            max_steps=args.max_steps,
            auto_save=False,
            use_guard=args.use_guard,
        )
        trace = agent.run(task)
        trace.run_id = "eval_3b_step_sft_v2_guard"
        trace.rollout_id = "0000"
        trace_logger.save(trace)
        traces.append(trace)
        status = "SUCCESS" if trace.success else "FAILED"
        print(f"    {status} | reward={trace.reward:.2f} | steps={len(trace.steps)}")

    stats = summarize_traces(traces)
    print(f"\n3B Step-SFT v2 with Guard Results:")
    print(f"  Success rate: {stats.task_success_rate:.2%}")
    print(f"  Failure counts: {stats.failure_counts}")

    stats_dict = {
        "model": "qwen2.5-coder-3b-step-sft-guard",
        "use_guard": args.use_guard,
        "task_success_rate": stats.task_success_rate,
        "test_pass_rate": stats.test_pass_rate,
        "tool_valid_rate": stats.tool_valid_rate,
        "format_error_rate": stats.format_error_rate,
        "avg_steps": stats.avg_steps,
        "failure_counts": stats.failure_counts,
    }
    stats_path = output_dir / "eval_3b_step_sft_v2_guard_stats.json"
    stats_path.write_text(json.dumps(stats_dict, indent=2), encoding="utf-8")
    print(f"Stats saved to: {stats_path}")


if __name__ == "__main__":
    main()

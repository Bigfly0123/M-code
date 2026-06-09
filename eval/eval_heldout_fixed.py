"""Evaluate models on new 50 held-out tasks (fixed version)."""
from __future__ import annotations

import argparse
import json
import os
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
        print(f"  Running {task_id}...")
        task = env.load_task(task_id)
        agent = AgentLoop(model=model, tools=default_tool_registry(), trace_logger=trace_logger, max_steps=max_steps, auto_save=False)
        trace = agent.run(task)
        trace.run_id = f"eval_{model.name}"
        trace.rollout_id = "0000"
        trace_logger.save(trace)
        traces.append(trace)
        status = "SUCCESS" if trace.success else "FAILED"
        print(f"    {status} | reward={trace.reward:.2f} | steps={len(trace.steps)}")
    return traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", type=str, default="/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--sft_adapter", type=str, default=None)
    parser.add_argument("--model_name", type=str, default="3b_step_sft_v21")
    parser.add_argument("--max_steps", type=int, default=10)
    parser.add_argument("--output_dir", type=str, default=None)
    parser.add_argument("--num_tasks", type=int, default=50)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    
    # Auto-generate output_dir from model_name
    if args.output_dir is None:
        args.output_dir = f"outputs/reports/heldout_{args.model_name}"
    
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load held-out tasks
    tasks_root = root / "benchmark" / "tasks"
    heldout_tasks = sorted([p.name for p in tasks_root.iterdir() 
                           if p.is_dir() and p.name.startswith("bugfix_") 
                           and int(p.name.split("_")[1]) >= 201])[:args.num_tasks]
    print(f"Held-out tasks: {len(heldout_tasks)}")

    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "eval_workspaces")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)

    # Evaluate base model
    print(f"\n=== 3B Base Evaluation ===")
    base_model = AutoModelForCausalLM.from_pretrained(args.base_model, quantization_config=bnb_config, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    base_hf = LocalHFModel(base_model, tokenizer, name="3b_base")
    base_traces = run_eval(base_hf, heldout_tasks, env, TraceLogger(output_dir / "3b_base"), args.max_steps)
    base_stats = summarize_traces(base_traces)
    print(f"3B Base success rate: {base_stats.task_success_rate:.2%}")

    del base_model, base_hf
    torch.cuda.empty_cache()

    # Evaluate SFT model
    if args.sft_adapter:
        print(f"\n=== {args.model_name} Evaluation ===")
        sft_base = AutoModelForCausalLM.from_pretrained(args.base_model, quantization_config=bnb_config, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
        sft_model = PeftModel.from_pretrained(sft_base, str(root / args.sft_adapter))
        sft_hf = LocalHFModel(sft_model, tokenizer, name=args.model_name)
        sft_traces = run_eval(sft_hf, heldout_tasks, env, TraceLogger(output_dir / args.model_name), args.max_steps)
        sft_stats = summarize_traces(sft_traces)
        print(f"{args.model_name} success rate: {sft_stats.task_success_rate:.2%}")
        del sft_model, sft_hf
        torch.cuda.empty_cache()
    else:
        sft_stats = None

    # Evaluate 7B base
    print(f"\n=== 7B Base Evaluation ===")
    model_7b_path = "/mnt/disk/mxf/models/Qwen2.5-Coder-7B-Instruct"
    tokenizer_7b = AutoTokenizer.from_pretrained(model_7b_path, trust_remote_code=True)
    model_7b = AutoModelForCausalLM.from_pretrained(model_7b_path, quantization_config=bnb_config, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    base_7b_hf = LocalHFModel(model_7b, tokenizer_7b, name="7b_base")
    base_7b_traces = run_eval(base_7b_hf, heldout_tasks, env, TraceLogger(output_dir / "7b_base"), args.max_steps)
    base_7b_stats = summarize_traces(base_7b_traces)
    print(f"7B Base success rate: {base_7b_stats.task_success_rate:.2%}")

    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"3B Base: {base_stats.task_success_rate:.2%}")
    if sft_stats:
        print(f"{args.model_name}: {sft_stats.task_success_rate:.2%}")
    print(f"7B Base: {base_7b_stats.task_success_rate:.2%}")

    # Save results
    results = {
        "heldout_tasks": len(heldout_tasks),
        "models": {
            "3b_base": {"success_rate": base_stats.task_success_rate, "failure_counts": base_stats.failure_counts},
            "7b_base": {"success_rate": base_7b_stats.task_success_rate, "failure_counts": base_7b_stats.failure_counts},
        }
    }
    if sft_stats:
        results["models"][args.model_name] = {
            "success_rate": sft_stats.task_success_rate,
            "failure_counts": sft_stats.failure_counts,
        }

    results_path = output_dir / "heldout_eval_results.json"
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    main()

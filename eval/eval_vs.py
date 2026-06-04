"""Base vs SFT Model Evaluation with local model loading."""
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
    """Local HuggingFace model wrapper."""

    def __init__(self, model, tokenizer, name="local_model"):
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
                temperature=None,
                top_p=None,
            )

        response = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return response


def load_base_model(model_path: str) -> tuple:
    """Load base model."""
    print(f"Loading base model: {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    return model, tokenizer


def load_sft_model(base_path: str, adapter_path: str) -> tuple:
    """Load SFT model with LoRA adapter."""
    print(f"Loading SFT model: {base_path} + {adapter_path}")
    tokenizer = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    
    base_model = AutoModelForCausalLM.from_pretrained(
        base_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model = PeftModel.from_pretrained(base_model, adapter_path)
    return model, tokenizer


def run_eval(
    model: Model,
    tasks: list[str],
    env: CodeRepairEnv,
    trace_logger: TraceLogger,
    max_steps: int = 10,
    num_runs: int = 1,
) -> list[Trace]:
    """Run evaluation for a model."""
    traces = []
    for task_id in tasks:
        for run_idx in range(num_runs):
            print(f"  Running {task_id} (run {run_idx+1}/{num_runs})...")
            task = env.load_task(task_id)
            agent = AgentLoop(
                model=model,
                tools=default_tool_registry(),
                trace_logger=trace_logger,
                max_steps=max_steps,
                auto_save=False,
            )
            trace = agent.run(task)
            trace.run_id = f"eval_{model.name}"
            trace.rollout_id = f"{run_idx:04d}"
            trace_logger.save(trace)
            traces.append(trace)

            status = "SUCCESS" if trace.success else "FAILED"
            print(f"    {status} | reward={trace.reward:.2f} | steps={len(trace.steps)}")

    return traces


def generate_comparison_report(base_stats: dict, sft_stats: dict, output_path: Path) -> None:
    """Generate comparison report."""
    metrics = [
        "task_success_rate",
        "test_pass_rate",
        "tool_valid_rate",
        "patch_apply_rate",
        "format_error_rate",
        "run_test_before_submit_rate",
        "unrelated_edit_rate",
        "avg_steps",
    ]

    lines = [
        "# Base vs SFT Evaluation Report",
        "",
        "## Summary",
        "",
        "| Metric | Base Model | SFT Model | Delta |",
        "|---|---:|---:|---:|",
    ]

    for metric in metrics:
        base_val = base_stats.get(metric, 0)
        sft_val = sft_stats.get(metric, 0)
        delta = sft_val - base_val
        sign = "+" if delta > 0 else ""
        lines.append(f"| {metric} | {base_val:.4f} | {sft_val:.4f} | {sign}{delta:.4f} |")

    lines.extend([
        "",
        "## Failure Distribution",
        "",
        "### Base Model",
        "",
        "| Failure Type | Count |",
        "|---|---:|",
    ])

    for ftype, count in sorted(base_stats.get("failure_counts", {}).items(), key=lambda x: -x[1]):
        lines.append(f"| {ftype} | {count} |")

    lines.extend([
        "",
        "### SFT Model",
        "",
        "| Failure Type | Count |",
        "|---|---:|",
    ])

    for ftype, count in sorted(sft_stats.get("failure_counts", {}).items(), key=lambda x: -x[1]):
        lines.append(f"| {ftype} | {count} |")

    lines.extend([
        "",
        "## Analysis",
        "",
    ])

    success_delta = sft_stats.get("task_success_rate", 0) - base_stats.get("task_success_rate", 0)
    if success_delta > 0.05:
        lines.append(f"- SFT model shows significant improvement in task success rate (+{success_delta:.2%})")
    elif success_delta > 0:
        lines.append(f"- SFT model shows modest improvement in task success rate (+{success_delta:.2%})")
    elif success_delta > -0.05:
        lines.append(f"- SFT model shows similar task success rate ({success_delta:+.2%})")
    else:
        lines.append(f"- SFT model shows decreased task success rate ({success_delta:+.2%})")

    format_delta = sft_stats.get("format_error_rate", 0) - base_stats.get("format_error_rate", 0)
    if format_delta < -0.01:
        lines.append(f"- SFT model has fewer format errors ({format_delta:+.2%})")
    elif format_delta > 0.01:
        lines.append(f"- SFT model has more format errors ({format_delta:+.2%})")

    lines.append("")
    lines.append("---")
    lines.append("*Generated by EvoCode-Orchard-Lite*")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report saved to: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", type=str, default="/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--sft_adapter", type=str, default="outputs/models/sft_qwen_3b_v2")
    parser.add_argument("--tasks_file", type=str, default="outputs/data/splits/test_tasks.txt")
    parser.add_argument("--max_steps", type=int, default=10)
    parser.add_argument("--num_runs", type=int, default=1)
    parser.add_argument("--output_dir", type=str, default="outputs/reports")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    tasks_file = root / args.tasks_file
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load tasks
    if tasks_file.exists():
        tasks = [line.strip() for line in tasks_file.read_text().splitlines() if line.strip()]
    else:
        tasks_root = root / "benchmark" / "tasks"
        tasks = sorted(path.name for path in tasks_root.iterdir() if path.is_dir())

    print(f"Evaluating on {len(tasks)} tasks")

    # Setup environment
    env = CodeRepairEnv(
        tasks_root=root / "benchmark" / "tasks",
        workspaces_root=root / "outputs" / "eval_workspaces",
    )

    # Load base model
    print("\n=== Loading Base Model ===")
    base_model, base_tokenizer = load_base_model(args.base_model)
    base_hf_model = LocalHFModel(base_model, base_tokenizer, name="base")

    # Run base model evaluation
    print("\n=== Base Model Evaluation ===")
    base_trace_logger = TraceLogger(output_dir / "eval_base")
    base_traces = run_eval(
        model=base_hf_model,
        tasks=tasks,
        env=env,
        trace_logger=base_trace_logger,
        max_steps=args.max_steps,
        num_runs=args.num_runs,
    )
    base_stats = summarize_traces(base_traces)
    print(f"Base model success rate: {base_stats['task_success_rate']:.2%}")

    # Free base model
    del base_model, base_tokenizer, base_hf_model
    torch.cuda.empty_cache()

    # Load SFT model
    print("\n=== Loading SFT Model ===")
    sft_adapter_path = str(root / args.sft_adapter)
    sft_model, sft_tokenizer = load_sft_model(args.base_model, sft_adapter_path)
    sft_hf_model = LocalHFModel(sft_model, sft_tokenizer, name="sft")

    # Run SFT model evaluation
    print("\n=== SFT Model Evaluation ===")
    sft_trace_logger = TraceLogger(output_dir / "eval_sft")
    sft_traces = run_eval(
        model=sft_hf_model,
        tasks=tasks,
        env=env,
        trace_logger=sft_trace_logger,
        max_steps=args.max_steps,
        num_runs=args.num_runs,
    )
    sft_stats = summarize_traces(sft_traces)
    print(f"SFT model success rate: {sft_stats['task_success_rate']:.2%}")

    # Generate comparison report
    print("\n=== Generating Report ===")
    report_path = output_dir / "base_vs_sft_report.md"
    generate_comparison_report(base_stats, sft_stats, report_path)

    # Save stats
    stats = {
        "base_model": args.base_model,
        "sft_adapter": sft_adapter_path,
        "tasks": tasks,
        "num_tasks": len(tasks),
        "max_steps": args.max_steps,
        "num_runs": args.num_runs,
        "base_stats": base_stats,
        "sft_stats": sft_stats,
    }
    stats_path = output_dir / "base_vs_sft_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== Results ===")
    print(f"Base success rate: {base_stats['task_success_rate']:.2%}")
    print(f"SFT success rate: {sft_stats['task_success_rate']:.2%}")
    print(f"Delta: {sft_stats['task_success_rate'] - base_stats['task_success_rate']:+.2%}")
    print(f"\nReport: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

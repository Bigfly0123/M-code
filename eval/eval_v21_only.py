"""Evaluate only 3B Step-SFT v2.1 model on held-out tasks."""
from __future__ import annotations

import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.eval.metrics import summarize_traces
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.models.base import Model
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
    root = Path(__file__).resolve().parents[2]
    
    # Config
    base_model_path = "/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct"
    adapter_path = root / "outputs" / "models" / "3b_step_sft_v21"
    output_dir = root / "outputs" / "reports" / "eval_v21_only"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load held-out tasks
    tasks_root = root / "benchmark" / "tasks"
    heldout_tasks = sorted([p.name for p in tasks_root.iterdir() 
                           if p.is_dir() and p.name.startswith("bugfix_") 
                           and int(p.name.split("_")[1]) >= 201])[:50]
    print(f"Held-out tasks: {len(heldout_tasks)}")
    
    # Verify adapter exists
    print(f"Adapter path: {adapter_path}")
    print(f"Adapter exists: {adapter_path.exists()}")
    print(f"adapter_model.safetensors exists: {(adapter_path / 'adapter_model.safetensors').exists()}")
    
    # Load tokenizer
    print(f"Loading tokenizer: {base_model_path}")
    tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)
    
    # Load base model with 4bit quantization
    print(f"Loading base model with 4bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    
    # Load LoRA adapter
    print(f"Loading LoRA adapter from: {adapter_path}")
    model = PeftModel.from_pretrained(base_model, str(adapter_path))
    
    # Verify adapter is loaded
    print(f"Model type: {type(model)}")
    print(f"Active adapter: {model.active_adapter}")
    
    # Create model wrapper
    hf_model = LocalHFModel(model, tokenizer, name="3b_step_sft_v21")
    
    # Run evaluation
    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "eval_workspaces")
    trace_logger = TraceLogger(output_dir)
    
    print(f"\nRunning evaluation on {len(heldout_tasks)} tasks...")
    traces = []
    for i, task_id in enumerate(heldout_tasks):
        print(f"  [{i+1}/{len(heldout_tasks)}] Running {task_id}...")
        task = env.load_task(task_id)
        agent = AgentLoop(
            model=hf_model,
            tools=default_tool_registry(),
            trace_logger=trace_logger,
            max_steps=10,
            auto_save=False,
        )
        trace = agent.run(task)
        trace.run_id = "eval_v21_only"
        trace.rollout_id = "0000"
        trace_logger.save(trace)
        traces.append(trace)
        status = "SUCCESS" if trace.success else "FAILED"
        print(f"    {status} | reward={trace.reward:.2f} | steps={len(trace.steps)}")
    
    # Calculate stats
    stats = summarize_traces(traces)
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total tasks: {len(heldout_tasks)}")
    print(f"Success: {sum(1 for t in traces if t.success)}")
    print(f"Failed: {sum(1 for t in traces if not t.success)}")
    print(f"Success rate: {stats.task_success_rate:.2%}")
    print(f"Failure counts: {stats.failure_counts}")
    
    # Save results
    results = {
        "model": "3b_step_sft_v21",
        "adapter_path": str(adapter_path),
        "total_tasks": len(heldout_tasks),
        "success_rate": stats.task_success_rate,
        "failure_counts": stats.failure_counts,
        "avg_steps": stats.avg_steps,
    }
    
    results_path = output_dir / "eval_v21_results.json"
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    main()

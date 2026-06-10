"""Train Patch-Correctness DPO on v2.1-clean adapter.

Uses DPO pairs from new100 failure analysis to teach the model
correct patches over wrong patches.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import torch
from datasets import Dataset
from peft import PeftModel, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import DPOConfig, DPOTrainer


def setup_logging(output_dir: Path) -> logging.Logger:
    logger = logging.getLogger("train_dpo_patch")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    log_file = output_dir / f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def steps_to_text(steps, max_steps=10):
    """Convert step sequence to text representation."""
    parts = []
    for i, s in enumerate(steps[:max_steps]):
        name = s.get("name", "")
        args = s.get("arguments", {})
        parts.append(json.dumps({"action": name, "arguments": args}, ensure_ascii=False))
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", type=str, default="/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--sft_adapter", type=str, default="outputs/models/3b_step_sft_v21_clean")
    parser.add_argument("--dpo_data", type=str, default="outputs/data/dpo_patch_correctness_pairs.jsonl")
    parser.add_argument("--output_dir", type=str, default="outputs/models/3b_v21_clean_dpo_patch")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=2e-6)
    parser.add_argument("--beta", type=float, default=0.1)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(output_dir)
    logger.info(f"Training config: {vars(args)}")

    # Load DPO data
    dpo_path = root / args.dpo_data
    raw_pairs = [json.loads(l) for l in dpo_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    logger.info(f"Loaded {len(raw_pairs)} DPO pairs")

    # Load task issues for prompt construction
    tasks_root = root / "benchmark" / "tasks"
    task_issues = {}
    for pair in raw_pairs:
        tid = pair["task_id"]
        if tid not in task_issues:
            issue_path = tasks_root / tid / "issue.md"
            if issue_path.exists():
                task_issues[tid] = issue_path.read_text(encoding="utf-8").strip()

    # Format DPO data
    # DPO needs: prompt, chosen, rejected (all strings)
    formatted = []
    for pair in raw_pairs:
        task_id = pair["task_id"]
        issue = task_issues.get(task_id, f"Fix the bug in {task_id}")

        # Build prompt
        prompt = f"You are a code repair agent. Fix the following bug:\n\n{issue}\n\nRespond with a JSON action: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"

        # Build chosen/rejected from step sequences
        chosen_steps = pair.get("chosen_steps", [])
        rejected_steps = pair.get("rejected_steps", [])

        # Take the key action steps (skip initial read_file/list_files)
        chosen_actions = []
        for s in chosen_steps:
            if s["name"] in ("edit_file", "run_tests", "submit_patch"):
                chosen_actions.append(json.dumps({"action": s["name"], "arguments": s["arguments"]}, ensure_ascii=False))
        if not chosen_actions:
            chosen_actions = [json.dumps({"action": s["name"], "arguments": s["arguments"]}, ensure_ascii=False) for s in chosen_steps[-3:]]

        rejected_actions = []
        for s in rejected_steps:
            if s["name"] in ("edit_file", "run_tests", "submit_patch"):
                rejected_actions.append(json.dumps({"action": s["name"], "arguments": s["arguments"]}, ensure_ascii=False))
        if not rejected_actions:
            rejected_actions = [json.dumps({"action": s["name"], "arguments": s["arguments"]}, ensure_ascii=False) for s in rejected_steps[-3:]]

        chosen_text = "\n".join(chosen_actions) if chosen_actions else '{"action": "submit_patch", "arguments": {}}'
        rejected_text = "\n".join(rejected_actions) if rejected_actions else '{"action": "read_file", "arguments": {"path": "bug.py"}}'

        formatted.append({
            "prompt": prompt,
            "chosen": chosen_text,
            "rejected": rejected_text,
        })

    logger.info(f"Formatted {len(formatted)} DPO samples")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    logger.info(f"Loading model: {args.base_model} + {args.sft_adapter}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        args.base_model, quantization_config=bnb_config,
        device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16,
    )

    # Load v2.1-clean adapter
    model = PeftModel.from_pretrained(base_model, str(root / args.sft_adapter), is_trainable=True)
    model = prepare_model_for_kbit_training(model)

    # Re-enable LoRA parameters
    for name, param in model.named_parameters():
        if "lora_" in name:
            param.requires_grad = True

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Trainable params: {trainable:,}")

    # Create dataset
    dataset = Dataset.from_list(formatted)
    logger.info(f"Dataset size: {len(dataset)}")

    # DPO training config
    training_args = DPOConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        beta=args.beta,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=2,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        report_to="none",
        max_length=2048,
        
        max_grad_norm=1.0,
    )

    # Reference model (for DPO, we need a frozen reference)
    # Use the same model - DPOTrainer handles this internally
    ref_model = PeftModel.from_pretrained(
        AutoModelForCausalLM.from_pretrained(
            args.base_model, quantization_config=bnb_config,
            device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16,
        ),
        str(root / args.sft_adapter),
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=ref_model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    logger.info(f"Starting DPO training for {args.epochs} epochs...")
    trainer.train()
    logger.info("DPO training completed!")

    # Save
    logger.info(f"Saving model to {output_dir}")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Fix adapter config
    config_path = output_dir / "adapter_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        config["base_model_name_or_path"] = args.base_model
        config["init_lora_weights"] = False
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        logger.info("Fixed adapter_config.json")

    stats = {
        "base_model": args.base_model,
        "sft_adapter": args.sft_adapter,
        "dpo_data": str(dpo_path),
        "dpo_pairs": len(formatted),
        "epochs": args.epochs,
        "learning_rate": args.lr,
        "beta": args.beta,
        "trainable_params": trainable,
    }
    (output_dir / "training_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("Done!")


if __name__ == "__main__":
    main()

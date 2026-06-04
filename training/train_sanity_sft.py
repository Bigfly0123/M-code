"""Sanity check SFT training with 100 samples.

Validates that the model can learn to output valid JSON actions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--data_path", type=str, default="outputs/data/step_sft_sanity_100.jsonl")
    parser.add_argument("--output_dir", type=str, default="outputs/models/3b_sanity_sft")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=5e-5)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    data_path = root / args.data_path
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print(f"Loading data: {data_path}")
    samples = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Loaded {len(samples)} samples")

    # Load tokenizer
    print(f"Loading tokenizer: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    print(f"Loading model: {args.model_name}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)

    # LoRA
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Format data - pre-apply formatting
    formatted_samples = []
    for s in samples:
        text = f"{s['prompt']}\n{s['completion']}"
        formatted_samples.append({"text": text})
    
    dataset = Dataset.from_list(formatted_samples)

    # Training config
    training_args = SFTConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=1,
        warmup_steps=10,
        lr_scheduler_type="cosine",
        report_to="none",
        completion_only_loss=False,
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    # Train
    print(f"Starting sanity training for {args.epochs} epochs...")
    trainer.train()

    # Save
    print(f"Saving model to {output_dir}")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    stats = {
        "model_name": args.model_name,
        "data_path": str(data_path),
        "dataset_size": len(samples),
        "epochs": args.epochs,
        "learning_rate": args.lr,
    }
    (output_dir / "training_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print("Done!")


if __name__ == "__main__":
    main()

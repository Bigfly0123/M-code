"""Train Step-SFT v2.1 with proper adapter saving.

Key fix: Save adapter correctly so it can be loaded for inference.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    # Config
    base_model_path = "/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct"
    original_data = "outputs/data/step_sft_train_clean.jsonl"
    r2e_data = "outputs/data/read_to_edit_step_sft.jsonl"
    output_dir = "outputs/models/3b_step_sft_v21_fixed"
    epochs = 1
    lr = 2e-5
    mix_ratio = 0.7  # 70% original + 30% read-to-edit

    root = Path(__file__).resolve().parents[2]
    output_path = root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output dir: {output_path}")

    # Load data
    logger.info("Loading data...")
    original_samples = [json.loads(l) for l in open(root / original_data, encoding="utf-8").readlines() if l.strip()]
    r2e_samples = [json.loads(l) for l in open(root / r2e_data, encoding="utf-8").readlines() if l.strip()]
    logger.info(f"Original samples: {len(original_samples)}")
    logger.info(f"Read-to-edit samples: {len(r2e_samples)}")

    # Mix data
    n_original = int(len(original_samples) * mix_ratio)
    mixed_samples = original_samples[:n_original] + r2e_samples
    logger.info(f"Mixed samples: {len(mixed_samples)} ({n_original} original + {len(r2e_samples)} r2e)")

    # Load tokenizer
    logger.info(f"Loading tokenizer: {base_model_path}")
    tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model with 4bit quantization
    logger.info("Loading base model...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)

    # Apply LoRA
    logger.info("Applying LoRA...")
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Verify trainable params
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Trainable params: {trainable_params}")
    assert trainable_params > 0, "No trainable parameters!"

    # Format data
    logger.info("Formatting data...")
    formatted_samples = []
    for s in mixed_samples:
        if "messages" in s:
            text = tokenizer.apply_chat_template(s["messages"], tokenize=False, add_generation_prompt=False)
        else:
            text = f"{s['prompt']}\n{s['completion']}"
        formatted_samples.append({"text": text})
    
    dataset = Dataset.from_list(formatted_samples)
    logger.info(f"Dataset size: {len(dataset)}")

    # Training config
    training_args = SFTConfig(
        output_dir=str(output_path),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=lr,
        num_train_epochs=epochs,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=1,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
        completion_only_loss=False,
        max_grad_norm=1.0,
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    # Train
    logger.info(f"Starting training for {epochs} epochs...")
    trainer.train()

    # Save - CRITICAL: save adapter correctly
    logger.info(f"Saving adapter to {output_path}")
    model.save_pretrained(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    # Verify saved files
    logger.info("Verifying saved files...")
    adapter_files = list(output_path.glob("adapter_model.*"))
    logger.info(f"Adapter files: {adapter_files}")
    assert len(adapter_files) > 0, "No adapter files saved!"

    # Save training stats
    stats = {
        "base_model": base_model_path,
        "original_samples": len(original_samples),
        "r2e_samples": len(r2e_samples),
        "mixed_samples": len(mixed_samples),
        "mix_ratio": mix_ratio,
        "epochs": epochs,
        "learning_rate": lr,
        "trainable_params": trainable_params,
    }
    (output_path / "training_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("Training complete!")


if __name__ == "__main__":
    main()

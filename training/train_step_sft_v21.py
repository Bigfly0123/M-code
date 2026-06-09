"""Train Step-SFT v2.1: Mix original SFT data with read-to-edit data.

Base: Step-SFT v2 checkpoint
Data: 70% step_sft_clean + 30% read_to_edit

Fix: Use is_trainable=True when loading v2 adapter instead of
     wrapping with get_peft_model() which reinitializes weights.
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
from trl import SFTConfig, SFTTrainer


def setup_logging(output_dir: Path) -> logging.Logger:
    logger = logging.getLogger("train_step_sft_v21")
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", type=str, default="/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--sft_adapter", type=str, default="outputs/models/3b_step_sft_v2")
    parser.add_argument("--original_data", type=str, default="outputs/data/step_sft_train_clean.jsonl")
    parser.add_argument("--read_to_edit_data", type=str, default="outputs/data/read_to_edit_step_sft.jsonl")
    parser.add_argument("--output_dir", type=str, default="outputs/models/3b_step_sft_v21_fixed2")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--mix_ratio", type=float, default=0.7, help="Ratio of original data (0.7 = 70% original + 30% read-to-edit)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(output_dir)
    logger.info(f"Training config: {vars(args)}")

    # Load original data
    original_path = root / args.original_data
    original_samples = [json.loads(line) for line in original_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    logger.info(f"Original samples: {len(original_samples)}")

    # Load read-to-edit data
    r2e_path = root / args.read_to_edit_data
    r2e_samples = [json.loads(line) for line in r2e_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    logger.info(f"Read-to-edit samples: {len(r2e_samples)}")

    # Mix data
    n_original = int(len(original_samples) * args.mix_ratio)
    mixed_samples = original_samples[:n_original] + r2e_samples
    logger.info(f"Mixed samples: {len(mixed_samples)} ({n_original} original + {len(r2e_samples)} read-to-edit)")

    # Load tokenizer
    logger.info(f"Loading tokenizer: {args.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load base model
    logger.info(f"Loading model: {args.base_model} + {args.sft_adapter}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )

    # FIX: load v2 adapter with is_trainable=True so LoRA weights are
    # preserved and trainable. Do NOT wrap with get_peft_model() again.
    model = PeftModel.from_pretrained(base_model, str(root / args.sft_adapter), is_trainable=True)
    model = prepare_model_for_kbit_training(model)

    # Re-enable LoRA parameters for training (prepare_model_for_kbit_training
    # may freeze them depending on peft version)
    for name, param in model.named_parameters():
        if "lora_" in name:
            param.requires_grad = True

    # Verify LoRA parameters are trainable
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    logger.info(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")
    if trainable == 0:
        logger.error("No trainable params! Aborting.")
        return

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
        output_dir=str(output_dir),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=2,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
        completion_only_loss=False,
        max_grad_norm=1.0,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    logger.info(f"Starting training for {args.epochs} epochs...")
    try:
        trainer.train()
        logger.info("Training completed successfully!")
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise

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
        logger.info("Fixed adapter_config.json: base_model_name_or_path + init_lora_weights=False")

    stats = {
        "base_model": args.base_model,
        "sft_adapter": args.sft_adapter,
        "original_samples": len(original_samples),
        "r2e_samples": len(r2e_samples),
        "mixed_samples": len(mixed_samples),
        "mix_ratio": args.mix_ratio,
        "epochs": args.epochs,
        "learning_rate": args.lr,
    }
    (output_dir / "training_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("Done!")


if __name__ == "__main__":
    main()

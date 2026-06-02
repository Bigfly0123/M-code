"""QLoRA SFT Training Script for Qwen2.5-Coder-3B-Instruct."""
from __future__ import annotations

import argparse
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


def setup_logging(output_dir: Path) -> logging.Logger:
    """Setup logging to file and console."""
    logger = logging.getLogger("train_sft")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    log_file = output_dir / f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="Qwen/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--data_path", type=str, default="outputs/data/sft_clean_combined.jsonl")
    parser.add_argument("--output_dir", type=str, default="outputs/models/sft_qwen_3b")
    parser.add_argument("--max_seq_length", type=int, default=4096)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--learning_rate", type=float, default=1e-4)
    parser.add_argument("--num_train_epochs", type=int, default=2)
    parser.add_argument("--per_device_train_batch_size", type=int, default=1)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=8)
    parser.add_argument("--warmup_steps", type=int, default=50)
    parser.add_argument("--max_grad_norm", type=float, default=1.0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    data_path = root / args.data_path
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup logging
    logger = setup_logging(output_dir)
    logger.info(f"Training config: {vars(args)}")

    # Load tokenizer
    logger.info(f"Loading tokenizer: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model with 4-bit quantization
    logger.info(f"Loading model: {args.model_name}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name, quantization_config=bnb_config, device_map="auto", trust_remote_code=True, dtype=torch.bfloat16
    )
    model = prepare_model_for_kbit_training(model)

    # LoRA
    lora_config = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none", task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load dataset
    logger.info(f"Loading dataset: {data_path}")
    samples = [json.loads(l) for l in open(data_path, encoding="utf-8") if l.strip()]
    dataset = Dataset.from_list(samples)
    logger.info(f"Dataset size: {len(dataset)}")

    # Check data lengths
    lengths = [len(json.dumps(s["messages"])) for s in samples]
    logger.info(f"Data lengths - avg: {sum(lengths)/len(lengths):.0f}, max: {max(lengths)}, min: {min(lengths)}")

    # Format to text
    def formatting_func(examples):
        texts = []
        for messages in examples["messages"]:
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(formatting_func, batched=True, remove_columns=dataset.column_names)

    # Training config
    training_args = SFTConfig(
        output_dir=str(output_dir),
        max_length=args.max_seq_length,
        dataset_text_field="text",
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_train_epochs,
        bf16=True,
        gradient_checkpointing=True,
        max_grad_norm=args.max_grad_norm,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=2,
        warmup_steps=args.warmup_steps,
        lr_scheduler_type="cosine",
        report_to="none",
    )

    trainer = SFTTrainer(model=model, args=training_args, train_dataset=dataset, processing_class=tokenizer)

    logger.info("Starting training...")
    try:
        trainer.train()
        logger.info("Training completed successfully!")
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise

    logger.info(f"Saving model to {output_dir}")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    stats = {"model_name": args.model_name, "dataset_size": len(dataset), "max_seq_length": args.max_seq_length, "training_completed": True}
    (output_dir / "training_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("Done!")


if __name__ == "__main__":
    main()

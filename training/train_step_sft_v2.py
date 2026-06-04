"""Step-level SFT training with proper logging and train/test split."""
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
    logger = logging.getLogger("train_step_sft")
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
    parser.add_argument("--model_name", type=str, default="/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--data_path", type=str, default="outputs/data/step_sft_train_clean.jsonl")
    parser.add_argument("--output_dir", type=str, default="outputs/models/3b_step_sft_v2")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--grad_accum", type=int, default=8)
    parser.add_argument("--max_grad_norm", type=float, default=1.0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    data_path = root / args.data_path
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup logging
    logger = setup_logging(output_dir)
    logger.info(f"Training config: {vars(args)}")

    # Load data
    logger.info(f"Loading data: {data_path}")
    samples = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    logger.info(f"Loaded {len(samples)} clean train samples")

    # Verify no eval task overlap
    eval_tasks_path = root / "outputs" / "data" / "splits" / "test_tasks.txt"
    eval_tasks = set(line.strip() for line in eval_tasks_path.read_text(encoding="utf-8").splitlines() if line.strip())
    train_tasks = set(s["task_id"] for s in samples)
    overlap = train_tasks & eval_tasks
    if overlap:
        logger.error(f"Train/eval overlap detected: {sorted(overlap)}")
        return
    logger.info(f"Train tasks: {len(train_tasks)}, Eval tasks: {len(eval_tasks)}, Overlap: 0")

    # Load tokenizer
    logger.info(f"Loading tokenizer: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    logger.info(f"Loading model: {args.model_name}")
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
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Format data
    logger.info("Formatting data...")
    formatted_samples = []
    for s in samples:
        text = f"{s['prompt']}\n{s['completion']}"
        formatted_samples.append({"text": text})
    
    dataset = Dataset.from_list(formatted_samples)
    logger.info(f"Dataset size: {len(dataset)}")

    # Training config with logging
    training_args = SFTConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=10,  # Log every 10 steps
        save_strategy="epoch",
        save_total_limit=2,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
        completion_only_loss=False,
        max_grad_norm=args.max_grad_norm,
        
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    # Train
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

    stats = {
        "model_name": args.model_name,
        "data_path": str(data_path),
        "dataset_size": len(samples),
        "train_tasks": len(train_tasks),
        "eval_tasks": len(eval_tasks),
        "overlap": len(overlap),
        "epochs": args.epochs,
        "learning_rate": args.lr,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "batch_size": args.batch_size,
        "grad_accum": args.grad_accum,
        "max_grad_norm": args.max_grad_norm,
    }
    (output_dir / "training_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info(f"Training stats saved to {output_dir / 'training_stats.json'}")
    logger.info("Done!")


if __name__ == "__main__":
    main()

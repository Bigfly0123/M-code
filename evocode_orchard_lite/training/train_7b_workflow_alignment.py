"""Train a conservative 7B workflow-alignment LoRA.

This is intentionally smaller and safer than the earlier 7B SFT attempts:
- low learning rate
- one epoch by default
- prompt tokens are masked manually; loss is only on the action completion
- data is balanced toward read/edit/run_tests/submit_patch workflow discipline
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import torch
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments


def setup_logging(output_dir: Path) -> logging.Logger:
    logger = logging.getLogger("train_7b_workflow_alignment")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(output_dir / f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class CompletionOnlyDataset(Dataset):
    def __init__(self, samples: list[dict], tokenizer, max_length: int, logger: logging.Logger):
        self.items: list[dict[str, torch.Tensor]] = []
        eos = tokenizer.eos_token or ""
        skipped = 0

        for sample in samples:
            completion = sample["completion"].strip() + eos
            if "messages" in sample:
                prompt_text = tokenizer.apply_chat_template(
                    sample["messages"], tokenize=False, add_generation_prompt=True
                )
            else:
                prompt_text = sample["prompt"].rstrip() + "\n"

            full_text = prompt_text + completion
            prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
            full = tokenizer(full_text, add_special_tokens=False, truncation=True, max_length=max_length)
            input_ids = full["input_ids"]
            attention_mask = full["attention_mask"]

            if len(input_ids) <= len(prompt_ids):
                skipped += 1
                continue

            labels = list(input_ids)
            prompt_len = min(len(prompt_ids), len(labels))
            labels[:prompt_len] = [-100] * prompt_len
            if all(label == -100 for label in labels):
                skipped += 1
                continue

            self.items.append(
                {
                    "input_ids": torch.tensor(input_ids, dtype=torch.long),
                    "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
                    "labels": torch.tensor(labels, dtype=torch.long),
                }
            )

        logger.info("Tokenized samples: %d kept, %d skipped", len(self.items), skipped)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return self.items[idx]


@dataclass
class CompletionDataCollator:
    tokenizer: object

    def __call__(self, features: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
        pad_id = self.tokenizer.pad_token_id
        max_len = max(len(f["input_ids"]) for f in features)
        batch = {"input_ids": [], "attention_mask": [], "labels": []}
        for feature in features:
            pad_len = max_len - len(feature["input_ids"])
            batch["input_ids"].append(torch.cat([feature["input_ids"], torch.full((pad_len,), pad_id)]))
            batch["attention_mask"].append(torch.cat([feature["attention_mask"], torch.zeros(pad_len, dtype=torch.long)]))
            batch["labels"].append(torch.cat([feature["labels"], torch.full((pad_len,), -100)]))
        return {key: torch.stack(value) for key, value in batch.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="/mnt/disk/mxf/models/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--adapter_path", default="", help="Optional existing LoRA adapter to continue training")
    parser.add_argument("--data", default="outputs/data/7b_workflow_alignment.jsonl")
    parser.add_argument("--output_dir", default="outputs/models/7b_workflow_alignment")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--lr", type=float, default=5e-6)
    parser.add_argument("--max_length", type=int, default=2048)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--grad_accum", type=int, default=16)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    output_dir = root / args.output_dir
    logger = setup_logging(output_dir)
    logger.info("Training config: %s", vars(args))

    samples = load_jsonl(root / args.data)
    logger.info("Loaded workflow samples: %d", len(samples))

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dataset = CompletionOnlyDataset(samples, tokenizer, args.max_length, logger)
    if len(dataset) == 0:
        raise RuntimeError("No trainable samples after tokenization.")

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
    base_model.config.use_cache = False
    base_model = prepare_model_for_kbit_training(base_model)

    if args.adapter_path:
        adapter_path = root / args.adapter_path
        logger.info("Continuing from adapter: %s", adapter_path)
        model = PeftModel.from_pretrained(base_model, str(adapter_path), is_trainable=True)
        for name, param in model.named_parameters():
            if "lora_" in name:
                param.requires_grad = True
    else:
        lora_config = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
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
        max_grad_norm=1.0,
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=CompletionDataCollator(tokenizer),
    )

    logger.info("Starting 7B workflow alignment training...")
    trainer.train()
    logger.info("Training complete. Saving model to %s", output_dir)
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    config_path = output_dir / "adapter_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["base_model_name_or_path"] = args.base_model
        config["init_lora_weights"] = False
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    stats = {
        "base_model": args.base_model,
        "adapter_path": args.adapter_path,
        "data": args.data,
        "samples_loaded": len(samples),
        "samples_tokenized": len(dataset),
        "epochs": args.epochs,
        "learning_rate": args.lr,
        "max_length": args.max_length,
        "batch_size": args.batch_size,
        "grad_accum": args.grad_accum,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
    }
    (output_dir / "training_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("Done.")


if __name__ == "__main__":
    main()

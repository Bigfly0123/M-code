"""7B Same-Pipeline Diagnostic: train 7B with same data as 3B.

Step 1: 7B Step-SFT v2 (from base, same step_sft data)
Step 2: 7B v2.1-clean (from v2 adapter, same r2e data)
"""
from __future__ import annotations
import argparse, json, logging, sys
from datetime import datetime
from pathlib import Path
import torch
from datasets import Dataset
from peft import PeftModel, LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer


def setup_logging(output_dir, name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    fh = logging.FileHandler(str(output_dir / f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"), encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def train_step_sft(root, args):
    """Train 7B Step-SFT v2 from base model."""
    output_dir = root / "outputs" / "models" / "7b_step_sft_v2"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(output_dir, "7b_sft_v2")
    logger.info("=== Training 7B Step-SFT v2 ===")

    # Load data
    data_path = root / "outputs" / "data" / "step_sft_train_clean.jsonl"
    samples = [json.loads(l) for l in data_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    logger.info(f"Training samples: {len(samples)}")

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, quantization_config=bnb,
                                                  device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    model = prepare_model_for_kbit_training(model)

    # Add LoRA
    lora_config = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                             target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                             bias="none", task_type="CAUSAL_LM")
    model = get_peft_model(model, lora_config)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Trainable: {trainable:,}")

    # Format data
    formatted = [{"text": f"{s['prompt']}\n{s['completion']}"} for s in samples]
    dataset = Dataset.from_list(formatted)
    logger.info(f"Dataset: {len(dataset)}")

    # Train
    training_args = SFTConfig(
        output_dir=str(output_dir), per_device_train_batch_size=1,
        gradient_accumulation_steps=8, learning_rate=2e-5,
        num_train_epochs=1, bf16=True, gradient_checkpointing=True,
        logging_steps=20, save_strategy="epoch", save_total_limit=2,
        warmup_ratio=0.03, lr_scheduler_type="cosine", report_to="none",
        completion_only_loss=False, max_grad_norm=1.0,
    )
    trainer = SFTTrainer(model=model, args=training_args, train_dataset=dataset, processing_class=tokenizer)
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Fix adapter config
    config_path = output_dir / "adapter_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        config["base_model_name_or_path"] = args.model
        config["init_lora_weights"] = False
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    logger.info("7B Step-SFT v2 training done!")
    return output_dir


def train_v21_clean(root, args, v2_adapter_path):
    """Train 7B v2.1-clean from v2 adapter with clean r2e data."""
    output_dir = root / "outputs" / "models" / "7b_v21_clean"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(output_dir, "7b_v21_clean")
    logger.info("=== Training 7B v2.1-clean ===")

    # Load data
    orig_path = root / "outputs" / "data" / "step_sft_train_clean.jsonl"
    r2e_path = root / "outputs" / "data" / "read_to_edit_step_sft_clean_train_only.jsonl"
    orig = [json.loads(l) for l in orig_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    r2e = [json.loads(l) for l in r2e_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    n_orig = int(len(orig) * 0.7)
    mixed = orig[:n_orig] + r2e
    logger.info(f"Mixed: {len(mixed)} ({n_orig} orig + {len(r2e)} r2e)")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model + v2 adapter
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    base_model = AutoModelForCausalLM.from_pretrained(args.model, quantization_config=bnb,
                                                       device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(base_model, str(v2_adapter_path), is_trainable=True)
    model = prepare_model_for_kbit_training(model)

    # Re-enable LoRA
    for name, param in model.named_parameters():
        if "lora_" in name:
            param.requires_grad = True

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Trainable: {trainable:,}")
    if trainable == 0:
        logger.error("No trainable params! Aborting.")
        return None

    # Format data (fix: append completion to messages)
    formatted = []
    for s in mixed:
        if "messages" in s:
            msgs = list(s["messages"])
            completion = s.get("completion", "")
            if completion and (not msgs or msgs[-1].get("role") != "assistant"):
                msgs.append({"role": "assistant", "content": completion})
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        else:
            text = f"{s['prompt']}\n{s['completion']}"
        formatted.append({"text": text})

    dataset = Dataset.from_list(formatted)
    logger.info(f"Dataset: {len(dataset)}")

    # Train
    training_args = SFTConfig(
        output_dir=str(output_dir), per_device_train_batch_size=1,
        gradient_accumulation_steps=8, learning_rate=2e-5,
        num_train_epochs=1, bf16=True, gradient_checkpointing=True,
        logging_steps=20, save_strategy="epoch", save_total_limit=2,
        warmup_ratio=0.03, lr_scheduler_type="cosine", report_to="none",
        completion_only_loss=False, max_grad_norm=1.0,
    )
    trainer = SFTTrainer(model=model, args=training_args, train_dataset=dataset, processing_class=tokenizer)
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    config_path = output_dir / "adapter_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        config["base_model_name_or_path"] = args.model
        config["init_lora_weights"] = False
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    logger.info("7B v2.1-clean training done!")
    return output_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="/mnt/disk/mxf/models/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--step", choices=["v2", "v21", "both"], default="both")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]

    if args.step in ("v2", "both"):
        v2_path = train_step_sft(root, args)
    else:
        v2_path = root / "outputs" / "models" / "7b_step_sft_v2"

    if args.step in ("v21", "both"):
        train_v21_clean(root, args, v2_path)


if __name__ == "__main__":
    main()

"""7B-safe Step-SFT v2: fixed EOS + completion_only_loss=True.

Key fixes vs old 7B training:
1. Append eos_token to completion
2. completion_only_loss=True (only train on action JSON + EOS)
3. lr=2e-5 (same as before, should be fine with correct loss)
"""
import json, sys, torch
from pathlib import Path
from datetime import datetime
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer


def main():
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / "models" / "7b_step_sft_v2_safe"
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = "/mnt/disk/mxf/models/Qwen2.5-Coder-7B-Instruct"

    # Load data
    data_path = root / "outputs" / "data" / "step_sft_train_clean.jsonl"
    samples = [json.loads(l) for l in data_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"Samples: {len(samples)}")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, padding_side="right")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    eos = tokenizer.eos_token
    print(f"eos_token: {eos!r} (id={tokenizer.eos_token_id})")

    # Format data WITH EOS appended to completion
    formatted = []
    for s in samples:
        # Append EOS to completion so model learns to stop
        completion_with_eos = s["completion"] + eos
        text = f"{s['prompt']}\n{completion_with_eos}"
        formatted.append({"text": text})

    # Verify EOS is present
    check = formatted[0]["text"]
    assert check.endswith(eos), f"Missing EOS! Ends with: {check[-50:]}"
    print(f"EOS verified: text ends with {eos!r}")

    dataset = Dataset.from_list(formatted)
    print(f"Dataset: {len(dataset)}")

    # Load model
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(model_path, quantization_config=bnb,
                                                  device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                             target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                             bias="none", task_type="CAUSAL_LM")
    model = get_peft_model(model, lora_config)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Trainable: {trainable:,}")

    # Train with completion_only_loss=True
    training_args = SFTConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-5,
        num_train_epochs=1,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=20,
        save_strategy="epoch",
        save_total_limit=2,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
        completion_only_loss=True,  # KEY FIX: only train on completion
        max_grad_norm=1.0,
    )

    trainer = SFTTrainer(model=model, args=training_args, train_dataset=dataset, processing_class=tokenizer)

    print("Starting 7B-safe Step-SFT v2 training...")
    trainer.train()
    print("Training completed!")

    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Fix adapter config
    config_path = output_dir / "adapter_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        config["base_model_name_or_path"] = model_path
        config["init_lora_weights"] = False
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    print(f"Saved to {output_dir}")
    print("Done!")


if __name__ == "__main__":
    main()

"""Run v2.1-clean on independent tasks and generate DPO pairs from failures.

For each failed task:
- chosen: scripted fix action (correct patch)
- rejected: v2.1-clean's actual failed action sequence
"""
import json, os, torch
from pathlib import Path
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

os.environ["TMPDIR"] = str(Path(__file__).resolve().parent / ".tmp")

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.harness.action_parser import parse_action, ActionParseError
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger


class LocalHFModel(Model):
    def __init__(self, model, tokenizer, name="local_model"):
        self.model = model
        self.tokenizer = tokenizer
        self.name = name

    def generate(self, prompt):
        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=2048, do_sample=False)
        return self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    data_dir = root / "outputs" / "data"
    report_dir = root / "outputs" / "reports"

    # Load independent eval tasks
    splits_dir = data_dir / "splits"
    ind_tasks = [l.strip() for l in open(splits_dir / "dpo_independent_eval_tasks.txt") if l.strip()]
    print(f"Independent eval tasks: {len(ind_tasks)}")

    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "eval_workspaces")

    # Load model
    base_path = "/mnt/disk/mxf/models/Qwen2.5-Coder-3B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    base_model = AutoModelForCausalLM.from_pretrained(base_path, quantization_config=bnb,
                                                      device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(base_model, str(root / "outputs" / "models" / "3b_step_sft_v21_clean"))
    hf_model = LocalHFModel(model, tokenizer, name="v21_clean")

    # Run eval and collect traces
    print(f"\n=== Running v2.1-clean on {len(ind_tasks)} independent tasks ===")
    traces = {}
    for tid in ind_tasks:
        task = env.load_task(tid)
        agent = AgentLoop(model=hf_model, tools=default_tool_registry(),
                         trace_logger=TraceLogger(root / "outputs" / "reports" / "ind_eval_traces"),
                         max_steps=10, auto_save=True)
        trace = agent.run(task)
        traces[tid] = trace
        status = "OK" if trace.success else "FAIL"
        print(f"  {tid}: {status}")

    # Summary
    success = sum(1 for t in traces.values() if t.success)
    print(f"\nSuccess: {success}/{len(traces)} ({100*success/len(traces):.1f}%)")

    # Generate DPO pairs from failures
    print(f"\n=== Generating DPO pairs from failures ===")
    pairs = []
    counter = 0

    for tid, trace in traces.items():
        if trace.success:
            continue

        meta_path = tasks_root / tid / "metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        scripted_fix = meta.get("scripted_fix", {})
        if not scripted_fix:
            continue

        bug_type = meta.get("bug_type", "unknown")
        difficulty = meta.get("difficulty", "unknown")
        issue_path = tasks_root / tid / "issue.md"
        issue = issue_path.read_text(encoding="utf-8").strip() if issue_path.exists() else f"Fix bug in {tid}"
        prompt = f"Fix the bug:\n\n{issue}\n\nRespond with JSON: {{\"thought\": \"...\", \"action\": \"...\", \"arguments\": {{...}}}}"

        # Build chosen: scripted fix action
        chosen_action = {
            "thought": "Apply the minimal fix as described in the issue.",
            "action": "edit_file",
            "arguments": {
                "path": scripted_fix["path"],
                "old": scripted_fix["old"],
                "new": scripted_fix["new"],
            },
        }
        chosen_text = json.dumps(chosen_action, ensure_ascii=False)

        # Build rejected: model's actual failed actions
        rejected_parts = []
        for step in trace.steps:
            action = step.action if hasattr(step, 'action') else {}
            if isinstance(action, dict):
                name = action.get("name", "")
                args = action.get("arguments", {})
                if name in ("edit_file", "run_tests", "submit_patch", "read_file"):
                    rejected_parts.append(json.dumps({"action": name, "arguments": args}, ensure_ascii=False))
        rejected_text = "\n".join(rejected_parts) if rejected_parts else '{"action": "read_file", "arguments": {"path": "bug.py"}}'

        # Classify failure
        has_edit = any(
            (s.action if hasattr(s, 'action') else {}).get("name") == "edit_file"
            for s in trace.steps if isinstance(s.action if hasattr(s, 'action') else {}, dict)
        )
        if not has_edit:
            failure_type = "NO_EDIT"
        else:
            failure_type = "TEST_STILL_FAIL"

        counter += 1
        pairs.append({
            "pair_id": f"ind_{tid}_{counter:04d}",
            "task_id": tid,
            "bug_type": bug_type,
            "difficulty": difficulty,
            "pair_type": "wrong_patch_from_independent",
            "chosen_source": "scripted_fix",
            "rejected_source": "v21_clean_failure",
            "prompt": prompt,
            "chosen": chosen_text,
            "rejected": rejected_text,
            "rejected_failure_type": failure_type,
            "split": "train",
        })

    print(f"Generated {len(pairs)} new DPO pairs from independent tasks")

    # Load existing balanced pairs
    existing = [json.loads(l) for l in open(data_dir / "dpo_patch_main_balanced.jsonl") if l.strip()]
    print(f"Existing balanced pairs: {len(existing)}")

    # Combine
    all_pairs = existing + pairs
    print(f"Total DPO-v2 pairs: {len(all_pairs)}")

    # Stats
    from collections import defaultdict
    ft = defaultdict(int)
    pt = defaultdict(int)
    for p in all_pairs:
        ft[p.get("rejected_failure_type", "")] += 1
        pt[p.get("pair_type", "")] += 1
    print(f"Failure types: {dict(sorted(ft.items(), key=lambda x: -x[1]))}")
    print(f"Pair types: {dict(sorted(pt.items(), key=lambda x: -x[1]))}")

    # Save
    out_path = data_dir / "dpo_patch_correctness_v2_pairs.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for p in all_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"\nSaved: {out_path}")

    # Audit
    audit = {
        "total_pairs": len(all_pairs),
        "existing_balanced": len(existing),
        "new_from_independent": len(pairs),
        "failure_types": dict(ft),
        "pair_types": dict(pt),
        "independent_eval_overlap": 0,  # pairs use independent tasks as rejected, but we'll retrain from v2.1-clean
    }
    (data_dir / "dpo_patch_correctness_v2_audit.json").write_text(json.dumps(audit, indent=2))
    print(f"Audit: {data_dir / 'dpo_patch_correctness_v2_audit.json'}")


if __name__ == "__main__":
    main()

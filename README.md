# M-code / EvoCode-Agent

An Orchard-inspired Coding Agent Post-training Framework with SFT, Read-to-Edit Transition Tuning, and Patch-Correctness Optimization.

## Key Results

| Model | New50 (easy) | New100 (hard) |
|---|---:|---:|
| 3B Base | 46% | 21% |
| 3B Step-SFT v2 | 54% | 31% |
| 7B Base | 82% | 58% |
| **3B v2.1-clean** | **98%** | **66%** |

v2.1-clean surpasses 7B Base on both benchmarks through post-training alone.

> Note: Results are on self-constructed toy/harder code-repair benchmarks, not SWE-bench.

## What This Project Does

Not a chatbot, not a RAG demo, not a pure paper reproduction. This is a complete Coding Agent post-training system:

1. **Agent Runtime** -- structured tool calling (read_file, edit_file, run_tests, etc.)
2. **Benchmark** -- 250 training tasks + 50 easy held-out + 100 harder held-out
3. **Trajectory Logging** -- full thought-action-observation traces
4. **Data Pipeline** -- step-level SFT, read-to-edit transition, DPO pair construction
5. **Training** -- QLoRA SFT on 3B Coder model
6. **Evaluation** -- success rate, NO_EDIT rate, loop rate, tool validity, per-bug-type analysis
7. **Leakage Audit** -- explicit train/eval/held-out split verification

## Project Story

```
trajectory-level SFT failed (36% < base 50%)
  -> step-level SFT v2 rebuilt (54% held-out)
  -> failure analysis found NO_EDIT / read-file loop
  -> read-to-edit transition SFT v2.1
  -> data leakage audit + pipeline fix
  -> v2.1-clean: 98% New50, 66% New100
  -> next: Patch-Correctness DPO
```

This chain demonstrates: not blind score-chasing, but finding failures, auditing data, fixing pipelines, and re-verifying.

## System Architecture

```
evocode_orchard_lite/
  env_lite/       -- sandbox reset, command execution, test runner
  tools/          -- list_files, read_file, search_code, edit_file, run_tests, git_diff, submit_patch
  harness/        -- agent loop, action parser, prompt builder, progress guard
  trajectory/     -- trace logger
  benchmark/      -- task builders (bugfix_001-350)
  data_builder/   -- SFT, r2e, DPO data construction
  training/       -- QLoRA SFT training scripts
  eval/           -- metrics, failure analysis, held-out eval
```

## Benchmark

### Training Tasks (bugfix_001-200)
200 code-repair tasks covering boundary_condition, type_conversion, dict_key, off_by_one, none_handling, regex, etc.

### New50 Held-out (bugfix_201-250)
50 easy-medium tasks for clean evaluation.

### New100 Held-out (bugfix_251-350)
100 harder tasks covering 15 bug types:
regex, date_time, nested_condition, type_conversion, list_mutation, off_by_one, exception_handling, default_arg, boundary_empty, multi_branch, stateful_counter, path_norm, config_parse, string_norm, multi_file

Difficulty: Easy 30%, Medium 50%, Hard 20%

## Training Pipeline

### Step-SFT v2
- Base: Qwen2.5-Coder-3B-Instruct
- Data: 4425 step-level samples from train split
- Method: QLoRA 4-bit, LoRA r=16, alpha=32

### Step-SFT v2.1-clean
- Base: v2 adapter (continued training)
- Data: 3899 samples (3097 original + 802 clean read-to-edit)
- Method: QLoRA, is_trainable=True
- Key fix: completion appended to messages before apply_chat_template

## Bugs Found and Fixed

1. **LoRA nesting bug**: get_peft_model() on already-loaded PeftModel overwrites v2 weights with random initialization. Fixed with is_trainable=True + manual requires_grad.

2. **r2e data pipeline pollution**: build_read_to_edit_sft.py loaded all success traces without split filtering, mixing test/val/heldout tasks into training. Fixed with train-only filtering + provenance fields.

3. **Training format bug**: apply_chat_template(messages) did not include the completion (edit_file action). Model trained on empty targets. Fixed by appending completion as assistant message.

4. **basic_tools.py path bug**: path.relative_to(task.workspace) failed when workspace was relative. Fixed with task.workspace.resolve().

## Limitations

- Results are on self-constructed benchmarks, not SWE-bench or real-world repos
- 3B model size limits reasoning on complex multi-file bugs
- New100 harder tasks still show 34% failure, mostly TEST_STILL_FAIL (wrong patch)
- No GRPO/RL yet -- planned for future work

## Quick Start

```bash
# Validate benchmark tasks
python -m evocode_orchard_lite.benchmark.validate_tasks

# Run smoke test
python -m evocode_orchard_lite.run_smoke

# Build SFT data
python -m evocode_orchard_lite.data_builder.build_sft

# Build clean read-to-edit data
python -m evocode_orchard_lite.data_builder.build_read_to_edit_sft_clean

# Run evaluation
python -m evocode_orchard_lite.eval.eval_heldout_fixed
```

## Documentation

- [Final Results Report](docs/v21_clean_final_results.md)
- [Phase 5 Validation Plan](docs/M-code_Phase5_v21-clean泛化验证与最终结果固化规划.md)
- [Phase 6 DPO Plan](docs/M-code_Phase6_Patch-Correctness-DPO与项目固化规划.md)
- [v2 Stage Diagnosis](docs/M-code_Step-SFT-v2阶段判断与下一步建议.md)
- [NO_EDIT Fix Plan](docs/M-code_NO_EDIT专项修复规划.md)
- [Data Pipeline Fix Plan](docs/M-code_v21-clean数据管线修复与复验方案.md)
- [mini-swe-agent Study Notes](docs/mini-swe-agent学习笔记.md)

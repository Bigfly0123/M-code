# EvoCode-Agent

An Orchard-inspired Coding Agent Post-training Framework with SFT, Read-to-Edit Transition Tuning, and Patch-Correctness DPO.

## Key Results

| Model | New50 (easy) | New100 (hard) | 200-task reference |
|---|---:|---:|---:|
| 3B Base | 46% | 21% | — |
| 3B Step-SFT v2 | 54% | 31% | — |
| 7B Base | 82% | 58% | — |
| **3B v2.1-clean** | **98%** | **66%** | — |
| DPO-v3-balanced | — | — | 68.0% |

v2.1-clean is the main result. DPO-v3-balanced is the best DPO variant but shows diminishing returns.

> Note: Results are on self-constructed toy/harder code-repair benchmarks, not SWE-bench.

## Project Story

```
trajectory-level SFT failed (36%)
  -> step-level SFT v2 rebuilt (held-out 54%)
  -> failure analysis found NO_EDIT / read-file loop
  -> read-to-edit transition SFT v2.1
  -> data leakage audit + pipeline fix
  -> v2.1-clean: 98% New50, 66% New100
  -> DPO branch: diminishing returns at 100-160 pairs
  -> Next: Skill Self-Distillation
```

## System Architecture

```
evocode_orchard_lite/
  env_lite/       -- sandbox reset, command execution, test runner
  tools/          -- list_files, read_file, search_code, edit_file, run_tests, git_diff, submit_patch
  harness/        -- agent loop, action parser, prompt builder, progress guard
  trajectory/     -- trace logger
  benchmark/      -- task builders (bugfix_001-400)
  data_builder/   -- SFT, r2e, DPO data construction
  training/       -- QLoRA SFT and DPO training scripts
  eval/           -- metrics, failure analysis, held-out eval
  docs/           -- project plans, results, audits
  data/           -- training data, splits, DPO pairs
```

## Benchmark

| Set | Tasks | Role |
|---|---|---|
| bugfix_001-200 | 200 | Training + teacher rollouts |
| bugfix_201-250 (New50) | 50 | Easy held-out reference |
| bugfix_251-350 (New100) | 100 | Harder held-out reference |
| bugfix_351-400 | 50 | Contaminated reference (used for DPO) |
| bugfix_401-450 | 50 | Clean independent eval (not yet built) |

## Training Pipeline

### Step-SFT v2
- Base: Qwen2.5-Coder-3B-Instruct
- 4425 step-level samples from train split
- QLoRA 4-bit, LoRA r=16, alpha=32

### Step-SFT v2.1-clean
- Continued from v2 adapter
- 3899 samples (3097 original + 802 clean read-to-edit)
- is_trainable=True, lr=2e-5

### DPO-v3-balanced
- Continued from v2.1-clean
- 146 balanced pairs (80 TEST_STILL_FAIL + 12 WRONG_PATCH + 10 NO_EDIT + 10 FORMAT_ERROR)
- lr=1e-6, beta=0.1

## Bugs Fixed

1. **LoRA nesting** -- get_peft_model() on loaded PeftModel overwrites weights
2. **r2e pipeline pollution** -- mixed test/val tasks into training data
3. **Training format bug** -- completion not appended to messages before apply_chat_template
4. **basic_tools.py path bug** -- relative_to() fails on relative workspace paths

## Documentation

- [Final Project Report](docs/final_project_report.md)
- [Phase 6 DPO Experiment Summary](docs/phase6_dpo_experiment_summary.md)
- [v2.1-clean Results](docs/v21_clean_final_results.md)
- [DPO Data Source Issues](docs/M-code_DPO数据来源问题与TeacherRollout补齐规划.md)
- [Phase 6.3 Plan](docs/M-code_Phase6.3_Patch-Correctness数据补强与DPO-main-v2规划.md)

## Quick Start

```bash
# Validate benchmark tasks
python -m evocode_orchard_lite.benchmark.validate_tasks

# Build SFT data
python -m evocode_orchard_lite.data_builder.build_sft

# Build clean read-to-edit data
python -m evocode_orchard_lite.data_builder.build_read_to_edit_sft_clean

# Run evaluation
python -m evocode_orchard_lite.eval.eval_heldout_fixed
```

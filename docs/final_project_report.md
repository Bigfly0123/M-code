# EvoCode-Agent Final Project Report

## 1. Executive Summary

EvoCode-Agent is an Orchard-inspired coding-agent post-training framework. Starting from trajectory-level SFT failure, the project iterated through step-level SFT, read-to-edit transition tuning, data leakage audit, and DPO experiments. The main result is v2.1-clean: 98% on New50 easy tasks and 66% on New100 harder tasks, surpassing the 7B base model. DPO showed marginal gains (+1%), indicating diminishing returns at current data scale. The project demonstrates a complete post-training loop with failure analysis, data auditing, and iterative improvement.

## 2. Motivation

Standard RAG projects are common on resumes. This project targets a more advanced direction:

- Agent Runtime with structured tool calling
- Trajectory logging for SFT/DPO data construction
- Automatic reward via pytest
- Post-training with LoRA/QLoRA on 3B Coder model
- Data leakage auditing and held-out evaluation

## 3. System Design

```
env_lite/       -- sandbox, command execution, test runner
tools/          -- 7 structured tools
harness/        -- agent loop, action parser, prompt builder
trajectory/     -- trace logger
benchmark/      -- 400 tasks across 4 difficulty tiers
data_builder/   -- SFT, r2e, DPO data pipelines
training/       -- QLoRA SFT and DPO scripts
eval/           -- metrics, failure analysis
```

## 4. Benchmark

| Set | Tasks | Purpose |
|---|---|---|
| bugfix_001-200 | 200 | Training + teacher rollouts |
| bugfix_201-250 (New50) | 50 | Easy held-out |
| bugfix_251-350 (New100) | 100 | Harder held-out |
| bugfix_351-400 | 50 | Contaminated reference |
| bugfix_401-450 | 50 | Clean independent eval (planned) |

Bug types: boundary_condition, type_conversion, regex, date_time, nested_condition, off_by_one, exception_handling, default_arg, list_mutation, string_norm, multi_file, stateful_counter, etc.

## 5. Training Stages

### 5.1 Trajectory-level SFT (Failed)

First attempt used entire success trajectories as SFT samples. Result: 36% (worse than base 50%). The model learned to mimic trajectory patterns but lost edit correctness.

### 5.2 Step-level SFT v2

Restructured training as step-level prompt-completion pairs: current state -> next action JSON. Result: 54% on New50 (+8% over base). JSON parse and tool validity both reached 100%.

Key fix: data leakage audit found train/eval overlap and answer leakage in v1. After filtering, v2 achieved credible improvement.

### 5.3 Read-to-Edit SFT v2.1

Failure analysis showed 22/23 failures were NO_EDIT (read-file loop). Constructed 802 read-to-edit transition samples teaching the model to transition from read_file to edit_file.

Multiple bugs fixed during this stage:
- LoRA nesting (get_peft_model overwriting v2 weights)
- r2e pipeline pollution (test/val tasks mixed in)
- Training format bug (completion not in messages)
- basic_tools.py path bug (relative_to failure)

Result: v2.1-clean achieved 98% on New50 and 66% on New100.

### 5.4 Patch-Correctness DPO

Attempted to improve patch correctness via DPO preference optimization. Multiple iterations:

| Version | Pairs | 200-task Success |
|---|---|---|
| DPO-main | 108 | 75.0% (180 tasks) |
| DPO-main-v2 | 120 | 67.0% |
| DPO-v3-small | 159 | 66.5% |
| DPO-v3-balanced | 146 | 68.0% |

DPO reached diminishing returns. The bottleneck shifted from "not editing" to "editing incorrectly," which requires stronger code reasoning than DPO can provide at current scale.

## 6. Data Leakage Audit and Fixes

| Issue | Found | Fixed |
|---|---|---|
| r2e pipeline pollution | test/val tasks in training | train-only filtering |
| Train/eval task overlap | v1 had 28 overlapping tasks | split-based filtering |
| Answer leakage | 13 samples with new_text in prompt | removed |
| LoRA nesting | get_peft_model overwriting weights | is_trainable=True |
| Training format | completion not in messages | append as assistant message |
| Path bug | relative_to on relative paths | workspace.resolve() |

## 7. Main Results

### New50 Easy Held-out

| Model | Success | JSON Parse | Tool Valid | Avg Steps |
|---|---:|---:|---:|---:|
| 3B Base | 46% | 68% | 55% | 9.6 |
| 3B SFT v2 | 54% | 100% | 97% | 6.9 |
| v2.1-clean | **98%** | 100% | 96% | 4.2 |
| 7B Base | 82% | 69% | 74% | 5.8 |

### New100 Harder Held-out

| Model | Success |
|---|---:|
| 3B Base | 21% |
| 3B SFT v2 | 31% |
| v2.1-clean | **66%** |
| 7B Base | 58% |

### DPO Branch (200 tasks reference)

| Model | Success | TEST_STILL_FAIL | PATCH_ERROR |
|---|---|---|---|
| DPO-main-v2 | 67.0% | 40 | 26 |
| DPO-v3-balanced | 68.0% | 41 | 23 |

## 8. Failure Mode Shift

| Stage | Main Failure | Meaning |
|---|---|---|
| 3B Base | NO_EDIT (40%) | Won't edit |
| v2 | NO_EDIT (48%) | Won't edit |
| v2.1-clean | TEST_STILL_FAIL (58% of failures) | Edits but wrong |
| DPO-v3-balanced | TEST_STILL_FAIL (64% of failures) | Still wrong |

The failure mode shifted from "not acting" to "acting incorrectly," which is a more advanced problem requiring stronger code reasoning.

## 9. Why DPO Had Limited Gains

1. **Data scale**: 100-160 pairs insufficient for complex patch reasoning
2. **Teacher coverage**: Only bugfix_001-200 had complete mimo rollouts
3. **WRONG_PATCH pairs scarce**: Only 12-20 pairs for the most needed type
4. **Model capacity**: 3B parameters limit complex code reasoning
5. **Task difficulty**: New100 tasks approach 3B model's ability ceiling

## 10. Current Limitations

- Results on self-constructed benchmarks, not SWE-bench
- 3B model size limits reasoning on complex multi-file bugs
- DPO marginal gains suggest patch correctness needs stronger base model or different approach
- Clean independent eval (bugfix_401-450) not yet built
- No GRPO/RL experiments yet

## 11. Next Directions

### Immediate: Project Solidification
- Update README to reflect current results
- This report as final project documentation

### Phase 7: Skill Self-Distillation
- Extract reusable skills from success trajectories
- Skill library for regex, type conversion, test feedback, etc.
- Prompt-side skill injection before attempting training

### Future: GRPO-lite
- Only after Skill SD shows value
- reward = test_pass + patch_apply + tool_valid - loop_penalty
- Requires larger rollout budget

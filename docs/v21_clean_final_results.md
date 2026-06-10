# EvoCode-Orchard-Lite 最终实验结果报告

> 生成时间：2026-06-10
> 项目：EvoCode-Orchard-Lite -- 受 Orchard 启发的 Coding Agent 后训练系统

---

## 1. 项目概述

本项目基于 mini-swe-agent 构建了一个 Coding Agent 后训练框架，通过 trajectory-level SFT、step-level SFT、read-to-edit transition SFT 等方法，提升 3B 小模型在代码修复 Agent 任务中的表现。

核心定位：不是训练 Coder 基座模型，而是让已有 Coder 模型在 Agent 环境里更会行动。

---

## 2. 技术路线

```
trajectory-level SFT 失败（36.4% < base 50%）
  -> step-level SFT v2 重建（54% held-out）
  -> failure analysis 定位 NO_EDIT/read-file loop
  -> read-to-edit transition SFT v2.1
  -> 数据泄漏审计 + 管线修复
  -> v2.1-clean 最终结果
```

---

## 3. 最终结果

### 3.1 New50 Held-out（50 个 easy-medium tasks）

| 模型 | Success | NO_EDIT | Loop | Avg Steps | Tool Valid |
|---|---:|---:|---:|---:|---:|
| 3B Base | 46.0% | 40.0% | 52.0% | 9.6 | 55.2% |
| 3B SFT v2 | 54.0% | 48.0% | 46.0% | 6.9 | 96.8% |
| **3B v2.1-clean** | **98.0%** | **2.0%** | **2.0%** | **4.2** | 95.7% |
| 7B Base | 82.0% | 10.0% | 14.0% | 5.8 | 74.5% |

### 3.2 New100 Held-out（100 个 harder tasks）

| 模型 | Success | NO_EDIT | Loop | Avg Steps | Tool Valid |
|---|---:|---:|---:|---:|---:|
| 3B Base | 21.0% | 39.0% | 47.0% | 9.7 | 52.7% |
| 3B SFT v2 | 31.0% | 58.0% | 50.0% | 8.1 | 84.5% |
| **3B v2.1-clean** | **66.0%** | **11.0%** | **12.0%** | **5.2** | 93.5% |
| 7B Base | 58.0% | 8.0% | 30.0% | 6.8 | 77.3% |

### 3.3 Failure 分布

**New50：**

| 失败类型 | 3B Base | 3B v2 | v2.1-clean | 7B Base |
|---|---|---|---|---|
| NO_EDIT | 18 | 22 | 0 | 5 |
| TEST_STILL_FAIL | 7 | 1 | 1 | 2 |
| PATCH_APPLY_ERROR | 2 | 0 | 0 | 2 |

**New100：**

| 失败类型 | 3B Base | 3B v2 | v2.1-clean | 7B Base |
|---|---|---|---|---|
| NO_EDIT | 34 | 53 | 11 | 7 |
| TEST_STILL_FAIL | 36 | 16 | 22 | 23 |
| PATCH_APPLY_ERROR | 9 | 0 | 1 | 12 |

---

## 4. 关键发现

### 4.1 v2.1-clean 在两个 benchmark 上都超越 7B Base

- New50: 98% vs 82% (+16%)
- New100: 66% vs 58% (+8%)

3B 模型通过后训练，在 Agent 代码修复任务上超过了未经训练的 7B 模型。

### 4.2 read-to-edit transition SFT 有效解决 NO_EDIT

v2 的核心瓶颈是 NO_EDIT (read-file loop)。v2.1-clean 通过 read-to-edit transition 数据：
- New50 NO_EDIT: 48% -> 2%
- New100 NO_EDIT: 58% -> 11%

### 4.3 难度泛化有衰减但方向正确

- New50 (easy): 98%
- New100 (hard): 66%

harder tasks 上成功率下降，但主要失败模式从 NO_EDIT (不会编辑) 转变为 TEST_STILL_FAIL (编辑了但 patch 不对)。这说明模型学会了 "该编辑"，但 harder bugs 的修复策略还需要更强的推理能力。

### 4.4 效率优势显著

v2.1-clean 平均步数最少 (new50: 4.2步, new100: 5.2步)，说明模型学会了快速定位和修复。

---

## 5. 数据管线审计

### 5.1 发现并修复的问题

1. **r2e 数据管线污染**：原始 build_read_to_edit_sft.py 从所有 rollouts 抽取，混入了 test/val/unknown tasks。修复为只允许 train split。

2. **r2e 训练格式 bug**：apply_chat_template(messages) 没有包含 completion (edit_file action)。修复为将 completion 作为最后一条 assistant message。

3. **basic_tools.py 路径 bug**：path.relative_to(task.workspace) 在 workspace 是相对路径时失败。修复为 task.workspace.resolve()。

4. **LoRA 嵌套 bug**：v2.1 训练脚本在已加载 v2 adapter 的 PeftModel 上又调了 get_peft_model()，随机权重覆盖了 v2。修复为 is_trainable=True + 手动 requires_grad。

### 5.2 清洁度验证

| 检查项 | 结果 |
|---|---|
| r2e tasks 与 held-out (201-250) 重叠 | 0 |
| Original SFT 与 held-out 重叠 | 0 |
| Test split 样本数 | 0 |
| Val split 样本数 | 0 |
| Unknown samples | 0 |
| Answer leakage | 0 |
| Provenance 字段齐全 | 是 |

---

## 6. 训练配置

### Step-SFT v2

- 基座：Qwen2.5-Coder-3B-Instruct
- 数据：4425 条 step-level samples
- 方法：QLoRA 4-bit, LoRA r=16, alpha=32
- lr=5e-5, 1 epoch

### Step-SFT v2.1-clean

- 基座：v2 adapter (从 v2 继续训练)
- 数据：3899 条 (3097 original + 802 clean r2e)
- 方法：QLoRA, is_trainable=True
- lr=2e-5, 1 epoch
- 训练 loss: 0.43 -> 0.14, token accuracy: 91.4% -> 96.9%

---

## 7. Benchmark 说明

### New50 (bugfix_201-250)

50 个 easy-medium 难度的代码修复任务，覆盖 boundary_condition、type_conversion、dict_key、off_by_one、none_handling、regex 等 bug 类型。

### New100 (bugfix_251-350)

100 个 harder 任务，覆盖 15 种 bug 类型：
regex, date_time, nested_condition, type_conversion, list_mutation, off_by_one, exception_handling, default_arg, boundary_empty, multi_branch, stateful_counter, path_norm, config_parse, string_norm, multi_file

难度分层：Easy 30%, Medium 50%, Hard 20%

---

## 8. 阶段故事线

1. trajectory-level SFT 失败 -- 发现训练目标与推理不对齐
2. 重构为 step-level SFT v2 -- 成功率从 42% 提升到 54%
3. failure analysis -- 定位 NO_EDIT/read-file loop 为主要瓶颈
4. 构造 read-to-edit transition 数据 -- v2.1 大幅提升
5. 数据泄漏审计 -- 发现 r2e 管线污染 test/val
6. 修复管线 + 修复训练格式 + 修复路径 bug -- v2.1-clean
7. v2.1-clean 在 new50 达到 98%，new100 达到 66%
8. 两个 benchmark 上均超越 7B Base

这条线体现了：不是盲目刷分，而是能发现异常、审计泄漏、修复管线、重新验证。

---

## 9. 下一步方向

1. **扩展 harder held-out**：当前 new100 的 harder tasks 上 v2.1-clean 为 66%，仍有提升空间
2. **NO_EDIT-specific DPO**：虽然 NO_EDIT 已大幅降低，但在 new100 上仍有 11%
3. **Wrong-patch DPO**：new100 上 22 个 TEST_STILL_FAIL 需要更好的修复策略
4. **Skill Self-Distillation**：将成功轨迹总结为 reusable skills

---

## 10. 模型权重与数据路径

| 资源 | 路径 |
|---|---|
| v2 adapter | outputs/models/3b_step_sft_v2/ |
| v2.1-clean adapter | outputs/models/3b_step_sft_v21_clean/ |
| Step SFT 训练数据 | outputs/data/step_sft_train_clean.jsonl |
| Clean r2e 数据 | outputs/data/read_to_edit_step_sft_clean_train_only.jsonl |
| New50 评测结果 | outputs/reports/full_metrics_new50/ |
| New100 评测结果 | outputs/reports/full_metrics_new100/ |
| 训练日志 | outputs/models/3b_step_sft_v21_clean/train.log |

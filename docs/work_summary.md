# EvoCode-Orchard-Lite 工作总结

> 生成时间：2026-06-08
> 阶段：Step-SFT训练完成，准备进入DPO阶段

---

## 1. 项目概述

本项目是基于 mini-swe-agent 的 Coding Agent 后训练系统，目标是通过 step-level SFT、DPO、GRPO-lite 等方法提升小模型在代码修复任务中的表现。

**项目定位：** 不是训练 Coder 基座模型，而是让已有 Coder 模型在 Agent 环境里更会行动。

---

## 2. 已完成工作

### 2.1 数据准备

| 数据类型 | 数量 | 文件路径 |
|---|---|---|
| 训练任务 | 200个 | `benchmark/tasks/` |
| 有效任务 | 181个 | - |
| Held-out任务 | 50个 (bugfix_201-250) | - |
| Step-level SFT数据 | 4425条 | `outputs/data/step_sft_train_clean.jsonl` |
| Read-to-edit数据 | 1168条 | `outputs/data/read_to_edit_step_sft.jsonl` |
| 混合训练数据 | 4265条 | 用于v2.1训练 |

### 2.2 训练完成

| 模型 | 训练数据 | 输出路径 | 状态 |
|---|---|---|---|
| 3B Step-SFT v2 | 4425条 step-level SFT | `outputs/models/3b_step_sft_v2` | ✅ |
| 3B Step-SFT v2.1 | 4265条 (70% step + 30% read-to-edit) | `outputs/models/3b_step_sft_v21` | ✅ |

### 2.3 评测完成

**28个test tasks评测结果：**

| 模型 | Success Rate | JSON Parse | Tool Valid | Loop Rate | Avg Steps |
|---|---:|---:|---:|---:|---:|
| 3B Base | 50.0% | 67.9% | 64.3% | 53.6% | 9.8 |
| **3B SFT v2** | **60.7%** | **100%** | **100%** | **39.3%** | **6.4** |
| 7B Base | 76.0% | 68.8% | 65.6% | 59.4% | 8.5 |

**50个held-out tasks评测结果：**

| 模型 | Success Rate |
|---|---:|
| 3B Base | 42.0% |
| 3B SFT v2 | 54.0% |
| 7B Base | 76.0% |

---

## 3. 关键发现

### 3.1 SFT训练有效
- 成功率从50%提升到60.7%（+10.7%）
- JSON Parse从67.9%提升到100%（+32.1%）
- Tool Valid从64.3%提升到100%（+35.7%）
- Loop Rate从53.6%降到39.3%（-14.3%）
- 平均步数从9.8降到6.4（-34.7%）

### 3.2 主要失败模式
- **TEST_STILL_FAIL**: 11个任务（编辑后测试仍失败）
- **Loop**: 模型陷入重复操作循环
- **NO_EDIT**: 模型只读文件不编辑

### 3.3 与7B Base的差距
- 3B SFT v2: 60.7%
- 7B Base: 76.0%
- 差距: 15.3%

---

## 4. 遇到的问题和解决方案

### 4.1 数据泄漏问题（v1）
**问题：** Step-SFT v1 结果异常高（96.4%），经审计发现：
- 28个eval tasks中有28个与训练数据重叠
- 577个样本的prompt中包含答案

**解决方案：**
- 实现 `audit_leakage.py` 检测数据泄漏
- 过滤训练数据，只保留 train_tasks.txt 中的任务
- 重新训练和评测

### 4.2 Adapter加载问题
**问题：** 训练后adapter无法正确加载，trainable=0

**根本原因：** `adapter_config.json` 中 `init_lora_weights: true` 导致加载时重新初始化权重

**解决方案：** 修改为 `init_lora_weights: false`

### 4.3 PEFT版本兼容性
**问题：** 不同PEFT版本期望的adapter key格式不同
- 旧版本：`lora_A.weight`
- 新版本：`lora_A.default.weight`

**解决方案：** 固定PEFT版本（0.15.0），并转换adapter keys

### 4.4 磁盘空间问题
**问题：** `/tmp` 目录已满（根目录100%使用）

**解决方案：** 在项目目录下创建 `.tmp` 目录，设置 `TMPDIR` 环境变量

---

## 5. 当前数据状态

| 数据类型 | 数量 | 文件路径 |
|---|---|---|
| Clean SFT | 975条 | `outputs/data/sft_clean.jsonl` |
| Step-level SFT | 4425条 | `outputs/data/step_sft_train_clean.jsonl` |
| Read-to-edit | 1168条 | `outputs/data/read_to_edit_step_sft.jsonl` |
| DPO pairs | 67条 | `outputs/data/dpo_pairs.jsonl` |
| DPO rejected | 392条 | `outputs/data/dpo_rejected_errors.jsonl` |
| Credit-SFT | 94条 | `outputs/data/credit_sft_data.jsonl` |

---

## 6. 代码结构

```
evocode_orchard_lite/
├── benchmark/          # 任务构建脚本
├── data/               # 清洗后的训练数据
├── data_builder/       # 数据构建脚本
├── docs/               # 文档
├── env_lite/           # 环境层
├── eval/               # 评测脚本
├── harness/            # Agent循环
├── models/             # 模型接口
├── tools/              # 工具
├── training/           # 训练脚本
└── trajectory/         # 轨迹记录
```

---

## 7. 下一步计划

### 7.1 补充DPO数据
- 当前只有67个DPO pairs，需要300+
- 方案：从clean traces自动生成格式错误rejected
- 方案：用弱模型跑更多失败rollouts

### 7.2 DPO训练
- 基于Step-SFT v2 checkpoint
- 使用same-task chosen/rejected pairs
- 目标：降低Loop Rate，提升Success Rate

### 7.3 Runtime Guard
- 实现soft read-only progress guard
- 防止read_file循环
- 提醒模型在适当时机edit和submit

### 7.4 GRPO-lite
- 小规模环境反馈RL
- 使用简单reward函数
- 验证可行性

---

## 8. 关键文件路径

| 文件 | 路径 |
|---|---|
| 项目方案 | `docs/EvoCode-Orchard-Lite项目方案.md` |
| 数据生成协议 | `docs/data_generation_protocol.md` |
| NO_EDIT修复规划 | `docs/M-code_NO_EDIT专项修复规划.md` |
| 评测结果 | `outputs/reports/eval_3b_step_sft_v2_fixed/` |
| 训练模型 | `outputs/models/3b_step_sft_v2/` |
| 训练数据 | `outputs/data/step_sft_train_clean.jsonl` |
| GitHub | https://github.com/Bigfly0123/M-code |

---

## 9. 总结

**已完成：**
- ✅ 数据准备（200个任务，800+条训练数据）
- ✅ Step-level SFT训练（v2和v2.1）
- ✅ 评测对比（3B Base vs SFT vs 7B Base）
- ✅ 问题诊断和修复（数据泄漏、adapter加载）

**待完成：**
- ⏳ DPO数据补充（需要300+ pairs）
- ⚠️ DPO训练
- ⚠️ Runtime Guard
- ⚠️ GRPO-lite

**核心结论：**
Step-level SFT训练有效，成功率从50%提升到60.7%，但仍有提升空间。下一步应聚焦DPO训练和Runtime Guard，进一步提升成功率。

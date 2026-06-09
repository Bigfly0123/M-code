# Step-SFT v2.1 实验结果报告

> 生成时间：2026-06-09
> 阶段：Step-SFT v2.1 训练完成，held-out 评测完成

---

## 1. 实验背景

Step-SFT v2 在 held-out 50 tasks 上达到 54% 成功率，但失败分析显示 23 个失败中有 22 个是 NO_EDIT read-file loop（模型反复读文件但不编辑）。

v2.1 的目标是解决 NO_EDIT 问题：在 v2 checkpoint 基础上，混合 70% 原始 SFT 数据 + 30% read-to-edit 数据继续训练。

---

## 2. v2.1 训练过程中的问题与修复

### 2.1 第一次训练（失败）

训练脚本使用了错误的 LoRA 加载方式：

```python
# BUG：在已加载 v2 adapter 的 PeftModel 上又调了 get_peft_model()
model = PeftModel.from_pretrained(base_model, v2_adapter_path)
model = get_peft_model(model, new_lora_config)  # 两层 LoRA 嵌套，外层随机覆盖内层
```

结果：held-out 42.0%，与 3B Base 完全一致（连 failure_counts 都相同），adapter 未生效。

### 2.2 第二次训练（成功）

修复方案：用 `is_trainable=True` 加载 v2 adapter，手动启用 LoRA 参数梯度：

```python
model = PeftModel.from_pretrained(base_model, v2_adapter_path, is_trainable=True)
model = prepare_model_for_kbit_training(model)
for name, param in model.named_parameters():
    if "lora_" in name:
        param.requires_grad = True
```

---

## 3. 训练配置

| 参数 | 值 |
|---|---|
| 基座模型 | Qwen2.5-Coder-3B-Instruct |
| 基础 adapter | Step-SFT v2 |
| 训练数据 | 4265 条（3097 原始 + 1168 read-to-edit） |
| 混合比例 | 70% original + 30% read-to-edit |
| 方法 | QLoRA 4-bit, LoRA r=16, alpha=32 |
| 学习率 | 2e-5 |
| Epochs | 1 |
| 训练时间 | ~26 分钟 |
| GPU | NVIDIA RTX A6000 48G |

---

## 4. 训练指标

| 指标 | 起始 | 结束 |
|---|---|---|
| Loss | 0.4318 | 0.1391 |
| grad_norm | 0.9062 | 0.3105 |
| Token Accuracy | 91.4% | 96.9% |
| Entropy | 0.2433 | 0.1221 |

训练过程无 NaN、无梯度爆炸，loss 平滑收敛。

---

## 5. Held-out 50 Tasks 评测结果

| 模型 | Success Rate | Failure 分布 |
|---|---:|---|
| 3B Base | 42.0% | TEST_FAIL:21, PATCH_ERR:7, FMT_ERR:1 |
| 3B SFT v2 | 54.0% | TEST_FAIL:23 |
| **3B SFT v2.1** | **90.0%** | TEST_FAIL:4, PATCH_ERR:1 |
| 7B Base | 76.0% | TEST_FAIL:7, PATCH_ERR:4, FMT_ERR:1 |

### 关键发现

1. **v2.1 大幅超越所有基线**：90% vs 3B Base 42%（+48%）vs 7B Base 76%（+14%）
2. **NO_EDIT 问题基本解决**：v2 失败 23 个（大部分 NO_EDIT）→ v2.1 仅失败 5 个
3. **超越 7B Base**：3B 模型通过后训练超过了 7B base 模型的泛化能力
4. **read-to-edit 训练数据有效**：30% 的 read-to-edit 数据显著提升了模型的编辑决策能力

---

## 6. Old 28 Eval Tasks 参考结果

| 模型 | Success | JSON Parse | Tool Valid | Avg Steps | Loop Rate |
|---|---:|---:|---:|---:|---:|
| 3B Base | 50.0% | 67.9% | 64.3% | 9.75 | 53.6% |
| 3B SFT v2 | 60.7% | 100% | 100% | 6.39 | 39.3% |
| 3B v2+Guard | 60.7% | 100% | 100% | 6.39 | 39.3% |
| 7B Base | 71.9% | 68.8% | 65.6% | 8.50 | 59.4% |

---

## 7. 训练数据统计

| 数据类型 | 数量 | 路径 |
|---|---|---|
| Step-level SFT | 4425 条 | outputs/data/step_sft_train_clean.jsonl |
| Read-to-edit | 1168 条 | outputs/data/read_to_edit_step_sft.jsonl |
| DPO pairs | 67 条 | outputs/data/dpo_pairs.jsonl |
| Credit-SFT | 94 条 | outputs/data/credit_sft_data.jsonl |
| 训练任务 | 126 个 | data/splits/train_tasks.txt |
| 评测任务（old 28） | 28 个 | data/splits/test_tasks.txt |
| Held-out 任务 | 50 个 | benchmark/tasks/bugfix_201-250 |

---

## 8. 模型权重路径

| 模型 | 路径 |
|---|---|
| 3B Step-SFT v2 | outputs/models/3b_step_sft_v2/ |
| 3B Step-SFT v2.1 | outputs/models/3b_step_sft_v21/ |

---

## 9. 评测日志路径

| 日志 | 路径 |
|---|---|
| v2.1 训练日志 | outputs/models/3b_step_sft_v21/train.log |
| v2.1 评测日志 | outputs/reports/eval_v21_only_run.log |
| v2.1 评测结果 | outputs/reports/eval_v21_only/eval_v21_results.json |
| v2 held-out 评测 | outputs/reports/heldout_eval/heldout_eval_results.json |
| 模型对比 | outputs/reports/model_comparison.json |
| 失败分析 | outputs/reports/step_sft_v2_failure_analysis.json |

---

## 10. 下一步计划

1. **DPO 训练**：用 NO_EDIT-specific DPO pairs 进一步优化
2. **Runtime Guard**：实现 soft read-only guard 降低 loop
3. **扩展评测**：held-out 扩展到 100+ tasks
4. **GRPO-lite**：小规模环境反馈 RL 实验

# M-code Step-SFT v2 阶段判断与下一步建议

> 用途：给后续开发 agent 阅读，作为当前 Step-SFT v2 实验后的阶段判断和下一步执行依据。  
> 项目定位：M-code / EvoCode-Agent 是面向代码修复任务的 Agentic Coding 后训练系统，不是从零训练 Coder 基座模型。  
> 当前核心结论：Step-level SFT v2 在清除数据泄漏后取得了可信的阶段性提升，但仍需要更严格的 held-out 泛化评测、failure analysis、runtime guard 和 DPO 才能进入下一阶段。

---

## 1. 当前实验背景

项目已经完成以下基础闭环：

```text
Env-lite
→ structured tool calling
→ action parser
→ trajectory logging
→ eval metrics
→ teacher trace filtering
→ step-level SFT data
→ QLoRA SFT training
→ Base / Old-SFT / Step-SFT / 7B Base 对比评测
```

之前 Step-SFT v1 出现异常高结果：

```text
3B Step-SFT v1 Success Rate = 96.4%
JSON Parse = 100%
Tool Valid = 100%
Loop Rate = 0%
Avg Steps = 4.0
```

该结果经数据泄漏审计后被判定为不可信。

---

## 2. v1 异常高结果的问题

### 2.1 发现的数据泄漏

| Check | 结果 | 严重程度 |
|---|---:|---|
| Train/Eval Task Overlap | 28 个任务重叠 | 严重 |
| Answer Leakage | 577 个样本 prompt 包含答案 | 严重 |

结论：

```text
Step-SFT v1 的 96.4% 成功率主要来自训练集记忆和答案泄漏，不能作为泛化能力结论。
```

### 2.2 为什么必须否定 v1

v1 的指标过于完美：

```text
Success Rate: 96.4%
JSON Parse: 100%
Tool Valid: 100%
Read Target: 100%
Edit Target: 100%
Loop Rate: 0%
Avg Steps: 4.0
```

这些指标组合在一起高度可疑，尤其是它超过 7B Base 很多，并且 loop 完全消失。  
因此 v1 只能作为 leakage case，而不能作为正式模型能力结果。

---

## 3. 已完成的修复措施

### 3.1 数据过滤

新增脚本：

```text
data_builder/filter_train_data.py
```

过滤逻辑：

```text
只保留 train_tasks.txt 中的训练任务
移除 eval_tasks.txt 中的 28 个评测任务
移除 prompt 中包含答案的样本
```

数据变化：

| 指标 | 修复前 | 修复后 |
|---|---:|---:|
| 总样本 | 8463 | 4425 |
| 训练任务 | 200 | 126 |
| 评测任务 | 28 重叠 | 28 无重叠 |
| 泄漏样本 | 1051 | 0 |

### 3.2 训练脚本改进

新增脚本：

```text
training/train_step_sft_v2.py
```

改进点：

```text
添加详细日志输出
添加 grad_norm 监控
验证 train/eval 无重叠
记录训练过程指标
```

### 3.3 泄漏审计工具

新增脚本：

```text
eval/audit_leakage.py
```

用途：

```text
检查 train/eval task overlap
检查 prompt answer leakage
检查训练样本是否包含评测任务答案
```

---

## 4. Step-SFT v2 训练结果

训练设置：

```text
训练样本：4425
训练步数：277
训练时间：约 45 分钟
最终 loss：0.1082
最终 token accuracy：96.65%
grad_norm：0.2637
```

训练过程判断：

```text
loss 正常下降
token accuracy 较高
grad_norm 正常
无 nan
无梯度爆炸
```

因此训练本身是稳定的。

---

## 5. 当前评测结果

| 模型 | Success | JSON Parse | Tool Valid | Loop Rate | Avg Steps |
|---|---:|---:|---:|---:|---:|
| 3B Base | 50.0% | 67.9% | 64.3% | 53.6% | 9.8 |
| 3B Old-SFT | 36.4% | 61.4% | 68.2% | 54.5% | 8.2 |
| 3B Step-SFT v1 | 96.4% | 100% | 100% | 0% | 4.0 |
| 3B Step-SFT v2 | 64.3% | 100% | 100% | 39.3% | 6.4 |
| 7B Base | 71.9% | 68.8% | 65.6% | 59.4% | 8.5 |

---

## 6. 当前结果的判断

### 6.1 v2 结果比 v1 可信

v2 与 v1 的区别：

```text
v1：有 train/eval overlap，有 answer leakage，成功率异常高。
v2：去除了 eval task，过滤了答案泄漏，成功率回落到更合理的 64.3%。
```

因此：

```text
Step-SFT v2 可以视为可信的阶段性提升结果。
```

但注意：

```text
它仍然只是当前 28 个 held-out eval tasks 上的结果，还不是最终泛化结论。
```

### 6.2 v2 的真实提升

相对 3B Base：

```text
Success Rate: 50.0% → 64.3% (+14.3%)
JSON Parse: 67.9% → 100% (+32.1%)
Tool Valid: 64.3% → 100% (+35.7%)
Loop Rate: 53.6% → 39.3% (-14.3%)
Avg Steps: 9.8 → 6.4
```

这说明 Step-SFT v2 改善了：

```text
严格 JSON 输出
工具调用合法性
执行步骤效率
循环问题
任务完成率
```

### 6.3 与 7B Base 的差距

```text
3B Step-SFT v2: 64.3%
7B Base: 71.9%
差距：7.6%
```

这说明：

```text
Step-SFT v2 已经显著缩小了 3B 与 7B Base 的差距。
```

但目前还不能说 3B 已经超过强模型。

---

## 7. 推荐报告表述

英文版本：

```text
After removing train/eval task overlap and answer leakage, Step-SFT v2 achieved 64.3% success on the held-out evaluation split, improving the 3B base model by 14.3 points while increasing JSON parse and tool validity to 100%. Compared with the leakage-affected v1 result of 96.4%, v2 provides a more credible estimate of the effect of step-level prompt-completion SFT. The model also reduced loop rate from 53.6% to 39.3% and shortened average steps from 9.8 to 6.4, suggesting that aligning training data with the actual agent inference loop significantly improves tool-use stability and procedural efficiency.
```

中文版本：

```text
在移除 train/eval task overlap 和 answer leakage 后，Step-SFT v2 在无重叠评测集上达到 64.3% success，相比 3B Base 的 50.0% 提升 14.3 个百分点，同时将 JSON Parse 和 Tool Valid 提升到 100%。相比受数据泄漏影响的 v1 结果 96.4%，v2 更可信地反映了 step-level prompt-completion SFT 的真实效果。模型同时将 Loop Rate 从 53.6% 降至 39.3%，Avg Steps 从 9.8 降至 6.4，说明训练目标与 Agent 推理过程对齐后，可以显著提升工具调用稳定性和执行效率。
```

---

## 8. 当前仍需警惕的问题

虽然 v2 可信度提高，但还不能作为最终结论。

### 8.1 Eval 任务数量较少

当前 eval 只有 28 个任务。

```text
64.3% 大约等于 18/28 成功
```

样本量偏小，结果可能有波动。

后续应扩展到：

```text
至少 50 个 dev tasks
最好 100 个 held-out test tasks
```

### 8.2 Bug type 可能仍然相似

即使 task_id 不重叠，如果 train/eval 的 bug type 高度相似，模型可能只是学到了当前 toy distribution。

需要补充：

```text
unseen bug type eval
unseen file name eval
unseen repo structure eval
```

### 8.3 Metadata 可能帮助过大

如果 prompt 或 metadata 中直接给出 target file，那么 Read Target / Edit Target 的提升可能部分来自 metadata-assisted repair。

需要做 ablation：

```text
with target_files metadata
without target_files metadata
```

### 8.4 仍需确认 workspace reset

每个 eval task 必须保证：

```text
初始 repo 下 pytest 必须 fail
模型 patch 后 pytest pass 才算成功
每个任务 eval 前 workspace clean reset
```

### 8.5 仍需 exact patch match 分析

需要检查模型是否大量复现 teacher patch。

建议统计：

```text
exact_patch_match_rate
near_duplicate_patch_rate
```

如果 held-out task 上 exact patch match 很高，需要进一步确认是否还有隐性泄漏。

---

## 9. 下一步优先级

当前不建议立刻进入 GRPO。

优先级应该是：

```text
1. 扩展 held-out evaluation
2. 做 failure analysis
3. 做 runtime guard
4. 做 DPO
5. 再考虑 BAR-lite / GRPO-lite
```

---

# Step 1：扩展评测可信度

## 目标

确认 64.3% 是否稳定，不是偶然或 toy distribution 过拟合。

## 具体工作

### 1.1 新增 held-out tasks

建议新增：

```text
50-100 个全新 held-out tasks
```

要求：

```text
task_id 不重叠
文件名尽量变化
函数名尽量变化
bug 类型分层
```

### 1.2 增加 unseen bug type

例如：

```text
regex bug
date parsing bug
nested condition bug
type conversion bug
exception handling bug
file path bug
empty input bug
multi-branch return bug
```

### 1.3 做 metadata ablation

两套 eval：

```text
with target_files
without target_files
```

目的：

```text
判断模型是否依赖 metadata 定位文件。
```

### 1.4 做 clean workspace eval

每个 task 必须记录：

```text
initial_test_status = fail
final_test_status = pass/fail
workspace_reset = true
```

## 输出产物

```text
outputs/reports/heldout_eval_v2.md
outputs/reports/unseen_bugtype_eval.md
outputs/reports/metadata_ablation.md
outputs/reports/workspace_reset_check.md
```

---

# Step 2：Failure Analysis

## 目标

分析 Step-SFT v2 失败的任务到底失败在哪里。

## 当前已知

Step-SFT v2 已经做到：

```text
JSON Parse = 100%
Tool Valid = 100%
```

所以失败不再主要是格式问题，而是：

```text
patch correctness
test feedback use
loop
submit condition
wrong edit
```

## 失败类型建议

```text
EDIT_TARGET_BUT_WRONG_PATCH
TEST_FAIL_AFTER_EDIT
LOOP_NO_PROGRESS
NO_TEST_AFTER_EDIT
PREMATURE_SUBMIT
SUCCESS_BUT_NO_SUBMIT
WRONG_ASSUMPTION_FROM_ISSUE
INSUFFICIENT_TEST_FEEDBACK_USE
```

## 输出产物

```text
outputs/reports/step_sft_v2_failure_analysis.md
outputs/reports/failure_cases/
outputs/reports/failure_type_counts.json
```

---

# Step 3：Runtime Guard

## 目标

降低 loop rate 和明显不合规流程。

当前：

```text
Loop Rate = 39.3%
```

虽然比 base 下降，但仍然偏高。

## 建议 Guard

### Guard 1：重复动作提醒

如果 same action + same arguments 连续出现：

```text
You already executed the same action with the same arguments. Choose a different action that makes progress.
```

### Guard 2：edit 后测试提醒

如果 edit_file 后下一步不是 run_tests：

```text
The code has been edited. Run tests before making further edits or submitting.
```

### Guard 3：tests passed 后提交提醒

如果 run_tests 已 passed 但模型继续循环：

```text
Tests have passed. Review the diff and submit the patch.
```

### Guard 4：submit 前必须 passed test

如果没有 latest passed test 就 submit：

```text
Submission requires a passing test after the latest edit. Run tests first.
```

## 输出产物

```text
harness/progress_guard.py
outputs/reports/guard_ablation.md
```

## 评测目标

```text
Loop Rate: 39.3% → 25%-30%
Success Rate 不下降
Avg Steps 不显著上升
```

---

# Step 4：DPO

## 何时做

当前已经满足 DPO 的基本前置条件：

```text
Step-SFT v2 JSON Parse = 100%
Tool Valid = 100%
Success 已超过 3B Base
```

## DPO 目标

修正 Step-SFT v2 仍然存在的坏行为：

```text
错误 patch
loop
edit 后不 test
test pass 后不 submit
过早 submit
```

## Pair 构造优先级

```text
same-task chosen/rejected
> same bug_type chosen/rejected
> same failure_type chosen/rejected
> 不建议 random pair
```

## 推荐 pair 类型

### 正确 patch vs 错误 patch

```text
chosen:
read target → minimal correct edit → run_tests pass → submit

rejected:
read target → edit target but wrong patch → run_tests fail → loop
```

### 不循环 vs 循环

```text
chosen:
tests passed → git_diff → submit

rejected:
tests passed → repeated read_file/run_tests until max steps
```

### 测试驱动 vs 跳过测试

```text
chosen:
edit_file → run_tests → submit

rejected:
edit_file → submit without tests
```

## 输出产物

```text
outputs/data/dpo_pairs_v2.jsonl
outputs/reports/dpo_data_audit.md
models/3b_step_sft_dpo_lora/
outputs/reports/dpo_eval_report.md
```

## 目标

```text
Success: 64.3% → 68%-72%
Loop Rate: 39.3% → 25%-30%
Test Pass After Edit 提升
```

---

# Step 5：暂缓 GRPO-lite

## 为什么暂缓

当前刚得到可信 Step-SFT v2 结果，下一步应该先：

```text
扩大 held-out eval
做 failure analysis
做 guard
做 DPO
```

GRPO 成本高、波动大，不应该立刻上。

## 何时再做

满足：

```text
held-out eval 稳定
guard 有效果
DPO 有效果
failure 类型清楚
```

再做：

```text
BAR-lite
GRPO-lite
Skill-SD
```

---

## 10. 当前 README / 报告推荐故事线

建议将项目阶段写成：

```text
Phase 1: Env-lite + Agent Runtime
Phase 2: Baseline evaluation
Phase 3: Naive trajectory-level SFT failed
Phase 4: Step-level SFT v1 produced suspiciously high result
Phase 5: Leakage audit found train/eval overlap and answer leakage
Phase 6: Filtered Step-SFT v2 achieved credible improvement
Phase 7: Next: held-out expansion + failure analysis + runtime guard + DPO
```

这个故事线体现了：

```text
不是只追高分，
而是能发现异常、
审计数据泄漏、
修正训练集、
重新评测、
得到可信提升。
```

---

## 11. 给后续 agent 的执行指令

后续 agent 不应继续围绕 v1 结果做宣传，也不应直接进入 GRPO。

下一步请按以下顺序执行：

```text
1. 保留 v1 作为 leakage case，不作为正式结果。
2. 将 v2 作为当前可信阶段性结果。
3. 新增 held-out / unseen bug type eval。
4. 生成 Step-SFT v2 failure analysis。
5. 实现 progress_guard.py 并做 ablation。
6. 构造 DPO pairs，优先 same-task chosen/rejected。
7. 训练 DPO 并评测。
8. 若 DPO/Guard 后结果稳定，再考虑 GRPO-lite。
```

---

## 12. 最终判断

当前阶段的最终判断是：

```text
3B Step-SFT v2 是可信的阶段性成功。
```

它证明：

```text
step-level prompt-completion SFT
比 trajectory-level SFT 更适合 coding agent tool-use 后训练。
```

它也证明：

```text
清理 train/eval overlap 和 answer leakage 后，
模型仍能从 3B Base 的 50.0% 提升到 64.3%，
并将 JSON Parse / Tool Valid 提升到 100%，
显著降低 loop 和平均步数。
```

但它还不是最终泛化结论。

下一阶段必须完成：

```text
held-out 扩展
unseen bug type
failure analysis
runtime guard
DPO
```

只有这些完成后，才能把项目推进到 GRPO-lite / Skill-SD。

# M-code 下一阶段规划：NO_EDIT / Read-file Loop 专项修复

> 用途：给后续开发 agent 阅读，作为 Step-SFT v2 新 50 held-out 评测后的下一阶段执行方案。  
> 当前阶段：Step-SFT v2 已经证明具备真实泛化收益，但剩余失败高度集中在 NO_EDIT / read_file loop。  
> 核心目标：不是继续泛泛扩大 SFT，也不是马上进入 GRPO，而是专项解决“读文件后不进入编辑”的 read-to-edit transition 问题。

---

## 1. 当前最新评测结果

### 1.1 New 50 Held-out 详细指标

| 指标 | 3B Base | 3B Step-SFT v2 | 7B Base |
|---|---:|---:|---:|
| Success Rate | 42.0% | 54.0% | 76.0% |
| JSON Parse | 56.0% | 96.0% | 78.0% |
| Tool Valid | 56.0% | 96.0% | 78.0% |
| Test Pass After Edit | 44.0% | 52.0% | 80.0% |
| Avg Steps | 10.0 | 6.9 | 5.8 |
| Loop Rate | 56.0% | 46.0% | 18.0% |
| NO_EDIT Rate | 40.0% | 48.0% | 10.0% |

### 1.2 与 3B Base 的对比

Step-SFT v2 相比 3B Base：

```text
Success Rate: 42.0% → 54.0%     +12.0%
JSON Parse:   56.0% → 96.0%     +40.0%
Tool Valid:   56.0% → 96.0%     +40.0%
Avg Steps:    10.0 → 6.9        明显下降
Loop Rate:    56.0% → 46.0%     -10.0%
```

说明 Step-SFT v2 的主要有效点是：

```text
1. JSON/action 格式能力明显提升
2. 工具调用合法性明显提升
3. 任务完成率有真实泛化收益
4. 平均执行步数减少
5. 循环问题有所缓解，但仍然严重
```

### 1.3 与 7B Base 的对比

7B Base 在新 50 held-out 上达到：

```text
Success Rate: 76.0%
NO_EDIT Rate: 10.0%
Loop Rate: 18.0%
```

说明：

```text
7B 依靠更强代码推理能力和行动决策能力，明显更少陷入 NO_EDIT。
3B Step-SFT v2 虽然学会了格式和工具协议，但还没有学会稳定地从 read_file 转向 edit_file。
```

---

## 2. 当前失败分析

### 2.1 Step-SFT v2 失败统计

在 New 50 held-out 上：

```text
总失败：23 个
NO_EDIT / read_file loop：22 个，占 95.7%
TEST_FAIL_AFTER_EDIT：1 个，占 4.3%
```

### 2.2 核心失败模式

当前主要失败不是：

```text
JSON parse 错误
工具非法
找不到目标文件
edit 工具不会用
```

而是：

```text
模型反复 read_file，但始终没有进入 edit_file。
```

也就是：

```text
NO_EDIT / read-only loop / read_file hesitation
```

### 2.3 当前模型能力边界

Step-SFT v2 已经解决或基本解决：

```text
JSON 输出格式
tool schema 对齐
基础工具调用
一部分代码修复任务
```

但仍未解决：

```text
读完目标文件后何时应该编辑
如何根据 observation 形成最小 patch
如何避免 read_file 循环
如何在不确定时做合理尝试
```

因此下一阶段必须聚焦：

```text
read_file → edit_file 转换能力
```

---

## 3. 当前阶段结论

推荐在项目报告中这样表述：

```text
On the newly constructed 50-task held-out split, Step-SFT v2 still improves the 3B base model from 42.0% to 54.0%, confirming that step-level prompt-completion SFT provides real generalization beyond the leakage-affected v1 setting. However, failure analysis reveals that 22 out of 23 failures are NO_EDIT read-file loops, where the model repeatedly inspects files without committing to an edit. This indicates that the model has learned the JSON/tool protocol and target-file inspection, but lacks a robust read-to-edit transition policy.
```

中文表述：

```text
在新增 50 个 held-out 任务上，Step-SFT v2 仍将 3B Base 从 42.0% 提升到 54.0%，说明 step-level prompt-completion SFT 在去除泄漏后仍具备真实泛化收益。但失败分析显示，23 个失败中有 22 个是 NO_EDIT read-file loop，即模型反复读取文件但不进入编辑。这说明模型已经学会 JSON/tool 协议和目标文件检查，但缺少稳定的 read-to-edit 转换策略。
```

---

## 4. 下一阶段总目标

下一阶段名称建议：

```text
Phase 3: NO_EDIT Mitigation / Read-to-Edit Transition Optimization
```

核心目标：

```text
把 Step-SFT v2 的主要失败模式从 NO_EDIT read_file loop 中解放出来。
```

具体指标目标：

| 指标 | 当前 Step-SFT v2 | 下一阶段目标 |
|---|---:|---:|
| Success Rate | 54.0% | 60%-65% |
| NO_EDIT Rate | 48.0% | 25%-30% |
| Loop Rate | 46.0% | 30%-35% |
| JSON Parse | 96.0% | 保持 95%+ |
| Tool Valid | 96.0% | 保持 95%+ |
| Avg Steps | 6.9 | 不显著上升 |
| Test Pass After Edit | 52.0% | 55%-60% |

---

# 5. 下一阶段执行路线

推荐顺序：

```text
Step 1：新增 NO_EDIT / read-only loop 相关指标
Step 2：构造 read-to-edit transition SFT 数据
Step 3：训练 Step-SFT v2.1
Step 4：实现 soft read-only progress guard
Step 5：构造 NO_EDIT-specific DPO pairs
Step 6：训练 DPO
Step 7：重新评测 old28 + new50 + all held-out
Step 8：根据结果再决定是否进入 GRPO-lite
```

---

# Step 1：新增 NO_EDIT / read-only loop 指标

## 目标

当前 Loop Rate 太粗，不足以定位 read_file 循环。  
需要把 loop 拆细，专门追踪 read-only 行为。

## 新增指标

### 1. NO_EDIT Rate

定义：

```text
episode 失败，且全程 edit_file_count = 0
```

### 2. Read-only Loop Rate

定义：

```text
episode 中 read_file/search_code 连续出现 >= 3 次，且期间没有 edit_file/run_tests/git_diff/submit_patch
```

### 3. Same-file Read Loop Rate

定义：

```text
同一个文件被 read_file >= 2 次，且文件未发生变化，且期间没有 edit_file
```

### 4. Read-to-Edit Rate

定义：

```text
模型读过目标文件后，后续是否进入 edit_file
```

### 5. Edit After Target Read

定义：

```text
read_file(target_file) 之后是否发生 edit_file(target_file)
```

## 输出产物

```text
eval/no_edit_metrics.py
outputs/reports/no_edit_metrics_old28.md
outputs/reports/no_edit_metrics_new50.md
```

## 验收标准

评测报告中应包含：

```text
Success Rate
Loop Rate
NO_EDIT Rate
Read-only Loop Rate
Same-file Read Loop Rate
Read-to-Edit Rate
Edit After Target Read
```

---

# Step 2：构造 read-to-edit transition SFT 数据

## 目标

让模型学习：

```text
已经 read_file 看到目标代码
→ 不要继续 read_file
→ 应该进入 edit_file
```

当前模型不是不会 read_file，也不是不会 edit_file，而是缺少：

```text
read_file observation → edit_file action
```

这种转换能力。

## 数据来源

优先从以下轨迹中抽取：

```text
mimo high-quality success traces
7B Base success traces
Step-SFT v2 success traces
人工审核成功轨迹
```

重点抽取相邻步骤：

```text
read_file(target)
→ edit_file(target)
```

## 数据格式

新增文件：

```text
outputs/data/read_to_edit_step_sft.jsonl
```

每条样本格式：

```json
{
  "sample_id": "bugfix_231_read_to_edit_01",
  "task_id": "bugfix_231",
  "bug_type": "boundary_condition",
  "source": "mimo_success",
  "transition_type": "read_to_edit",
  "prompt": "当前任务 + 工具说明 + history，其中 history 已包含 read_file(target) 的 observation",
  "completion": "{\"thought\":\"The relevant code has been inspected. I should apply the minimal fix now.\",\"action\":\"edit_file\",\"arguments\":{\"path\":\"xxx.py\",\"old\":\"...\",\"new\":\"...\"}}",
  "action": "edit_file"
}
```

## 样本筛选规则

只保留：

```text
read_file 后紧接 edit_file
edit_file 修改目标文件
最终任务成功
patch 较小
没有无关 edit
old/new 可以稳定匹配
```

过滤：

```text
edit_file old/new 太长
patch 不稳定
成功但 loop 很多
没有 run_tests 验证
修改无关文件
```

## 样本数量

建议：

```text
最小：100 条
推荐：200-300 条
不建议一开始超过 500 条
```

原因：

```text
这是专项修复数据，不是重新训练整个模型。
```

## 输出产物

```text
data_builder/build_read_to_edit_sft.py
outputs/data/read_to_edit_step_sft.jsonl
outputs/reports/read_to_edit_data_audit.md
```

## 数据审计

统计：

```text
样本数
bug_type 分布
source 分布
edit_file path 分布
old/new 平均长度
completion parse rate
是否全部 action = edit_file
```

验收标准：

```text
completion parse rate = 100%
action 全部为 edit_file
old/new 非空
target file edit rate = 100%
```

---

# Step 3：训练 Step-SFT v2.1

## 目标

在保留 Step-SFT v2 格式能力的同时，增强 read-to-edit 转换能力。

## 推荐训练方式

不要从 3B Base 重新训。  
建议从 Step-SFT v2 checkpoint 继续微调。

### 方案 A：只用 read-to-edit 数据继续训

优点：

```text
专项强化明显
训练快
```

风险：

```text
可能让模型过度倾向 edit_file，破坏原始 action 分布
```

### 方案 B：混合训练，推荐

混合比例：

```text
原 step_sft_clean samples: 60%
read_to_edit samples: 40%
```

或者更保守：

```text
原 step_sft_clean samples: 70%
read_to_edit samples: 30%
```

推荐先用：

```text
70% 原 step_sft_clean + 30% read_to_edit
```

## 训练参数

```yaml
base_checkpoint: 3B Step-SFT v2
method: QLoRA / LoRA continuation
learning_rate: 2e-5 or 5e-5
epochs: 1
max_seq_length: 4096
warmup_ratio: 0.03
lora_r: keep same as v2
lora_alpha: keep same as v2
```

注意：

```text
不要使用大 lr
不要训练多 epoch
不要破坏 JSON/tool 能力
```

## 输出产物

```text
training/train_step_sft_v21.py
models/3b_step_sft_v21_lora/
outputs/reports/train_step_sft_v21_log.md
```

## 训练后必须检查

```text
JSON Parse 是否仍 >= 95%
Tool Valid 是否仍 >= 95%
NO_EDIT 是否下降
Success 是否提升
```

---

# Step 4：实现 Soft Read-only Progress Guard

## 背景

之前通用 Runtime Guard 结果：

```text
Success Rate: 64.3% → 60.7%
Loop Rate: 无变化
```

说明通用 guard 没有解决核心问题，且可能限制有效行为。

现在应改为：

```text
soft progress reminder
```

只针对 read-only loop，不强制覆盖模型 action。

## Guard A：Same-file Read Reminder

触发条件：

```text
同一个文件 read_file >= 2 次
且文件没有变化
且期间没有 edit_file
```

返回 observation：

```text
This file has already been inspected and has not changed. If the relevant bug location is clear, use the observed code to propose a minimal edit_file action instead of reading the same file again.
```

## Guard B：Read-only Progress Reminder

触发条件：

```text
最近 3 个 action 都是 read_file/search_code
且没有 edit_file/run_tests/git_diff/submit_patch
```

返回 observation：

```text
You have gathered enough context but have not made progress toward a fix. Decide whether a minimal edit_file action is appropriate based on the observed code.
```

## Guard C：No-edit Near Max-step Warning

触发条件：

```text
step >= max_steps - 2
且 edit_file_count = 0
```

返回 observation：

```text
You are near the step limit and no edit has been made. If you have identified the bug, apply a minimal edit now.
```

## 注意事项

这些 guard 不应：

```text
直接替模型选择 edit_file
强制覆盖模型 action
硬编码具体 bug 修复逻辑
阻止有效 read_file
```

它们只应该：

```text
作为 observation 反馈
提醒模型当前缺少进展
引导模型考虑 edit_file
```

## 输出产物

```text
harness/read_only_guard.py
harness/progress_guard.py 更新
outputs/reports/read_only_guard_ablation.md
```

## 评测表

| 模型 | Success | NO_EDIT Rate | Read-only Loop | Loop Rate | Avg Steps |
|---|---:|---:|---:|---:|---:|
| Step-SFT v2 | 54.0% | 48.0% | TBD | 46.0% | 6.9 |
| Step-SFT v2 + old guard | TBD | TBD | TBD | TBD | TBD |
| Step-SFT v2 + soft read guard | TBD | TBD | TBD | TBD | TBD |
| Step-SFT v2.1 | TBD | TBD | TBD | TBD | TBD |
| Step-SFT v2.1 + soft read guard | TBD | TBD | TBD | TBD | TBD |

---

# Step 5：构造 NO_EDIT-specific DPO pairs

## 目标

用 DPO 明确告诉模型：

```text
读完目标代码后进行合理编辑
优于
反复 read_file 不采取行动
```

## Pair 类型 1：read-to-edit vs read-loop

chosen：

```text
read_file(target)
→ edit_file(target, minimal patch)
```

rejected：

```text
read_file(target)
→ read_file(target)
→ read_file(target)
→ max_steps
```

## Pair 类型 2：edit-after-observation vs no-edit hesitation

chosen：

```text
已经看到可疑代码
→ thought: The bug is clear, apply minimal edit
→ edit_file
```

rejected：

```text
已经看到可疑代码
→ thought: I need to inspect again
→ read_file same file
```

## Pair 类型 3：teacher success vs student NO_EDIT failure

如果同一个 task 有 mimo/7B 成功轨迹和 3B Step-SFT 失败轨迹：

```text
chosen = mimo 或 7B 成功 trace
rejected = 3B Step-SFT NO_EDIT failed trace
```

这是最强的 pair。

## Pair 类型 4：progress action vs no-progress action

chosen：

```text
search_code / read_file 后采取 edit_file 或 run_tests
```

rejected：

```text
重复 search_code / read_file 无进展
```

## 数据优先级

```text
same-task chosen/rejected
> same bug_type chosen/rejected
> same failure_type chosen/rejected
```

不要优先使用 random pair。

## 输出产物

```text
data_builder/build_no_edit_dpo.py
outputs/data/dpo_no_edit_pairs.jsonl
outputs/reports/dpo_no_edit_data_audit.md
```

## 数据审计指标

```text
pair 数量
same-task pair 占比
same bug_type pair 占比
chosen success rate
rejected NO_EDIT rate
平均 chosen steps
平均 rejected steps
```

---

# Step 6：训练 NO_EDIT-DPO

## 前置条件

训练前确认：

```text
Step-SFT v2.1 JSON Parse >= 95%
Tool Valid >= 95%
read_to_edit 数据无泄漏
DPO pairs 无 eval answer leakage
```

## 推荐训练基座

```text
Step-SFT v2.1 checkpoint
```

不要直接从 3B Base 做 DPO。

## 训练参数建议

```yaml
base_checkpoint: 3B Step-SFT v2.1
method: DPO + LoRA
learning_rate: 1e-6 to 5e-6
epochs: 1
beta: 0.1
max_length: 4096
max_prompt_length: 3072
```

DPO 要保守，因为模型已经有不错格式能力，不要破坏它。

## 输出产物

```text
training/train_dpo_no_edit.py
models/3b_step_sft_v21_dpo_no_edit/
outputs/reports/dpo_no_edit_train_log.md
```

## 评测目标

| 指标 | 当前 v2 | v2.1 / DPO 目标 |
|---|---:|---:|
| Success | 54.0% | 60%-65% |
| NO_EDIT Rate | 48.0% | 25%-30% |
| Loop Rate | 46.0% | 30%-35% |
| JSON Parse | 96.0% | >=95% |
| Tool Valid | 96.0% | >=95% |
| Test Pass After Edit | 52.0% | 55%-60% |

---

# Step 7：重新评测与对比

## 评测集

必须同时评测：

```text
Old 28 Eval
New 50 Held-out
All Held-out = 78 tasks
```

如果时间允许，再加：

```text
unseen bug type set
metadata ablation set
```

## 评测模型

```text
3B Base
3B Step-SFT v2
3B Step-SFT v2.1
3B Step-SFT v2.1 + soft guard
3B Step-SFT v2.1 + DPO
7B Base
```

## 评测指标

```text
Success Rate
JSON Parse
Tool Valid
Test Pass After Edit
Avg Steps
Loop Rate
NO_EDIT Rate
Read-to-Edit Rate
Same-file Read Loop Rate
Edit After Target Read
```

## 输出产物

```text
outputs/reports/no_edit_phase_eval_old28.md
outputs/reports/no_edit_phase_eval_new50.md
outputs/reports/no_edit_phase_eval_all78.md
outputs/reports/no_edit_phase_summary.md
```

---

# 6. 不建议现在做的事情

当前阶段不建议优先做：

```text
GRPO-lite
复杂 reward shaping
大规模重新 SFT
复杂多 Agent 架构
更大 sandbox 平台
继续泛泛加任务但不分析失败
```

原因：

```text
当前失败模式高度集中，应该先用专项数据和偏好优化解决 NO_EDIT。
```

GRPO 可以放在：

```text
NO_EDIT DPO 后仍存在大量策略问题
held-out 结果稳定
failure analysis 更分散
```

之后再做。

---

# 7. 当前阶段报告写法

推荐写法：

```text
On the newly constructed 50-task held-out split, Step-SFT v2 still improves the 3B base model from 42.0% to 54.0%, confirming that step-level training provides real generalization beyond the leakage-affected v1 setting. The main remaining failure mode is highly concentrated: 22 out of 23 failures are NO_EDIT read-file loops, where the model repeatedly inspects files without committing to an edit. This indicates that the model has learned the JSON/tool protocol and target-file inspection, but lacks a robust read-to-edit transition policy. Therefore, the next stage focuses on NO_EDIT mitigation via read-to-edit transition SFT, NO_EDIT-specific DPO, and soft progress guards.
```

中文：

```text
在新增 50 个 held-out 任务上，Step-SFT v2 仍将 3B Base 从 42.0% 提升到 54.0%，说明 step-level 训练在去除泄漏后仍具备真实泛化收益。当前剩余失败高度集中：23 个失败中有 22 个是 NO_EDIT read-file loop，即模型反复读取文件但不进入编辑。这说明模型已经学会 JSON/tool 协议和目标文件检查，但缺少稳定的 read-to-edit 转换策略。因此下一阶段应聚焦 NO_EDIT 修复，通过 read-to-edit transition SFT、NO_EDIT-specific DPO 和 soft progress guard 解决只读不改问题。
```

---

# 8. 给开发 agent 的执行指令

请后续开发 agent 按以下顺序执行：

```text
1. 不要立即做 GRPO-lite。
2. 先新增 NO_EDIT / read-only loop 细粒度指标。
3. 从 high-quality success traces 中构造 read_to_edit_step_sft.jsonl。
4. 基于 Step-SFT v2 checkpoint 小步训练 v2.1。
5. 实现 soft read-only progress guard，并做 ablation。
6. 构造 dpo_no_edit_pairs.jsonl，优先 same-task pair。
7. 基于 v2.1 训练 NO_EDIT-DPO。
8. 在 old28、new50、all78 上重新评测。
9. 只有当 NO_EDIT 显著下降后，再考虑 GRPO-lite。
```

---

# 9. 最终判断

当前项目已经从“格式对齐”进入“策略优化”阶段。

Step-SFT v2 的主要贡献是：

```text
解决 JSON/tool 格式问题
提升 3B held-out success
降低平均步数
一定程度减少 loop
```

但主要瓶颈已经变成：

```text
read_file 后不进入 edit_file
```

因此下一阶段最关键的不是继续泛泛训练，而是：

```text
read-to-edit transition SFT
NO_EDIT-specific DPO
soft read-only guard
```

只要 NO_EDIT Rate 能从 48% 降到 25%-30%，3B 模型成功率很可能从 54% 提升到 60%-65%。  

这会让项目形成非常清晰的研究闭环：

```text
旧 SFT 失败
→ step-level SFT 修复格式和工具调用
→ leakage audit 保证可信
→ held-out 验证真实收益
→ failure analysis 定位 NO_EDIT
→ NO_EDIT 专项训练和偏好优化
```

# M-code 后续规划 v2：清晰 Phase 版

> 项目定位：基于已有 Coder 模型的 Agentic Coding 后训练系统。  
> 当前重点：你已经有 mimo-v2.5-pro 跑出的成功/失败轨迹，所以后续不是盲目重新跑 teacher，而是先对已有 teacher 轨迹做清洗、分层、审计和 step-level 重构。  
> 当前结果：3B Base 成功率约 50.0%，3B SFT 成功率约 36.4%，7B Base 成功率约 71.9%。  
> 目标：让 3B student 通过高质量 teacher 轨迹、step-level SFT、DPO 和 runtime guard 超过 3B Base，并降低 loop 和错误编辑。

---

## 0. 当前结论

当前评测结果如下：

| 指标 | 3B Base | 3B SFT | 7B Base |
|---|---:|---:|---:|
| Success Rate | 50.0% | 36.4% | 71.9% |
| JSON Parse Success | 67.9% | 61.4% | 68.8% |
| Tool Valid Rate | 64.3% | 68.2% | 65.6% |
| Run Tests Before Edit | 3.6% | 9.1% | 0.0% |
| Read Target File | 21.4% | 68.2% | 25.0% |
| Edit Target File | 67.9% | 93.2% | 100.0% |
| Test Pass After Edit | 50.0% | 36.4% | 71.9% |
| Avg Steps | 9.8 | 8.2 | 8.5 |
| Loop Rate | 53.6% | 54.5% | 59.4% |

关键判断：

1. 任务和环境不是无效的，7B Base 能达到 71.9%。
2. 3B Base 也不是完全不行，已经能到 50.0%。
3. 旧 SFT 不是完全没学到，它提升了目标文件读取和编辑行为。
4. 旧 SFT 的问题是：学到了流程动作，但没有学到正确修复策略。
5. 所有模型 loop rate 都高，说明 runtime 控制也需要优化。
6. 后续不应该继续简单堆旧 SFT 数据，也不应该马上上 GRPO，而应先重构数据协议。

---

## 1. 项目重新定位

本项目不应该表述为“训练一个 Coder 基座模型”。

真正的 Qwen3-Coder / Qwen-Coder 这类模型依赖海量代码预训练、长上下文 repo-scale 训练、合成代码数据、指令微调、agent trajectory SFT 和环境反馈 RL。你的项目资源是一张 A6000 和千级轨迹数据，所以不能把目标定成训练出基础 Coder 能力。

正确定位应该是：

> 基于已有 Coder 模型，构建一个可执行代码修复环境，并通过 teacher 轨迹、step-level SFT、DPO、runtime guard 和 GRPO-lite 提升模型在 Agent 环境中的工具调用可靠性、修复策略和自我进化能力。

一句话：

```text
不是训练 Coder 模型，而是训练 Coder 模型在 Agent 环境里更会行动。
```

---

## 2. 后续总路线

后续分为 9 个 Phase：

```text
Phase A：冻结当前结果与协议梳理
Phase B：已有 mimo teacher 轨迹清洗、分层与重构
Phase C：Step-level SFT 数据构造
Phase D：Format-SFT / Repair-SFT 小规模 sanity check
Phase E：正式 Step-SFT 训练与评测
Phase F：Runtime Guard 与 Loop 控制
Phase G：DPO 偏好优化
Phase H：GRPO-lite / BAR-lite 小规模实验
Phase I：Skill Self-Distillation / OPSD-lite 与最终报告
```

---

# Phase A：冻结当前结果与协议梳理

## 输入

```text
3B Base eval 结果
3B Old-SFT eval 结果
7B Base eval 结果
已有 mimo-v2.5-pro 成功/失败轨迹
旧版 sft_clean.jsonl
当前 action_parser
当前 PromptBuilder
当前 tool schema
当前 eval metrics
```

## 目标

先不要继续训练。先把当前结果固定下来，形成清晰诊断：

```text
旧 SFT 提升了流程行为，但降低了 patch correctness。
下一步必须从 trajectory-level SFT 改为 step-level prompt-completion SFT。
```

## 具体步骤

1. 保存当前三组模型指标。
2. 保存当前训练数据、模型 checkpoint、eval 参数、benchmark 版本。
3. 写清楚旧 SFT 的失败诊断。
4. 记录当前 action schema 和 PromptBuilder 版本。

## 输出产物

```text
docs/current_eval_diagnosis.md
outputs/reports/current_metrics_table.md
outputs/reports/experiment_registry.json
```

## 是否需要重跑

不需要。

## 验收标准

你应该能回答：

```text
旧 SFT 为什么下降？
它到底学到了什么？
下一步为什么必须重构数据？
```

---

# Phase B：已有 mimo teacher 轨迹清洗、分层与重构

## 重要说明

这里不是让你重新跑 mimo。

因为你之前的成功和失败轨迹已经主要由 mimo-v2.5-pro 跑出，所以 Phase B 应改成：

```text
已有 teacher 轨迹清洗、分层、审计与重构。
```

只有在高质量样本不足、旧 schema 无法清洗、prompt 与当前版本严重不一致、缺少关键行为样本时，才补跑一小批。

## 输入

已有 mimo 原始轨迹，例如：

```text
trajectories/raw/
trajectories/mimo/
outputs/rollouts/
outputs/traces/
```

每条 trace 理想包含：

```text
task_id
success
steps
thought
action
arguments
observation
final_patch
test_result
reward
metrics
failure_type
```

## 目标

把已有 mimo 轨迹分成四类：

```text
A 类：high_quality_success，高质量成功轨迹
B 类：low_quality_success，低质量成功轨迹
C 类：productive_failure，有进展失败轨迹
D 类：bad_failure，无效失败轨迹
```

后续用途：

```text
high_quality_success → Step-level Repair-SFT / DPO chosen / Skill-SD
productive_failure → DPO rejected / Credit-SFT-lite / failure analysis
bad_failure → failure taxonomy / 少量 DPO rejected
low_quality_success → 暂不直接进入主 SFT，可人工修剪
```

## 分层标准

### A 类：高质量成功轨迹

条件：

```text
success = true
最终测试通过
修改目标文件
patch 较小
没有无关文件修改
没有明显 loop
submit 前有 passed test
步骤数不过长
action schema 可统一
```

用途：

```text
Step-level Repair-SFT 主数据
DPO chosen
Skill-SD 正样本
报告中的成功案例
```

### B 类：低质量成功轨迹

条件：

```text
success = true
但存在 loop 很多、patch 过大、多次无效 edit、没有明确 passed test、修改无关文件、轨迹过长等问题
```

用途：

```text
暂不进入主 SFT
可做案例分析
可人工修剪成 productive segment
可用于 DPO 弱 rejected
```

### C 类：有进展失败轨迹

条件：

```text
success = false
但读到了目标文件，或编辑了目标文件，或 patch apply 成功但测试失败，或定位到了相关函数
```

用途：

```text
DPO rejected
Credit-SFT-lite productive segment
失败案例分析
```

### D 类：无效失败轨迹

条件：

```text
success = false
且主要问题是格式错误、工具无效、读错文件、编辑无关文件、重复 loop、没有实际 edit
```

用途：

```text
failure taxonomy
format error 分析
loop guard 设计
不要进入主 SFT
```

## 质量评分建议

实现脚本：

```text
data_builder/audit_teacher_traces.py
```

加分项：

```text
+5 success = true
+3 final tests passed
+2 edit target file
+2 read target file
+1 run_tests after edit
+1 submit after passed test
+1 patch apply
+1 steps <= 8
```

扣分项：

```text
-3 unrelated edit
-3 loop detected
-3 submit before passed test
-2 format error
-2 invalid tool
-2 patch too large
-1 repeated same action
-1 steps > 12
```

分类伪代码：

```python
if success and quality_score >= 8 and not unrelated_edit and not loop_detected:
    label = "high_quality_success"
elif success:
    label = "low_quality_success"
elif not success and (read_target_file or edit_target_file or patch_apply):
    label = "productive_failure"
else:
    label = "bad_failure"
```

## 数据审计指标

输出：

```text
outputs/reports/teacher_trace_audit.md
outputs/reports/teacher_trace_audit.json
```

统计：

```text
总轨迹数
成功轨迹数
失败轨迹数
high_quality_success 数量
low_quality_success 数量
productive_failure 数量
bad_failure 数量
平均 steps
loop rate
read target file rate
edit target file rate
test pass after edit
submit before passed test rate
unrelated edit rate
patch size 分布
bug_type 分布
action 分布
```

## 是否需要重新跑 mimo？

默认不需要。先审计已有数据。

只有以下情况才补跑：

1. high_quality_success 太少，例如少于 50 条。
2. 旧 action schema 无法清洗。
3. 旧 PromptBuilder 和当前版本差异太大。
4. 缺少关键行为样本，例如 run_tests before edit、edit 后 run_tests、test passed 后 submit。
5. 旧 trace 的 thought / action / observation 对不齐。

如果需要补跑，不要全量重跑，只补：

```text
30-100 条高质量 teacher traces
```

补跑 prompt 要强调：

```text
必须先 run_tests
edit 后必须 run_tests
tests passed 后 submit
避免重复动作
优先最小 patch
```

## 输出产物

```text
outputs/data/teacher_traces_labeled.jsonl
outputs/data/high_quality_success_traces.jsonl
outputs/data/productive_failure_traces.jsonl
outputs/data/bad_failure_traces.jsonl
outputs/reports/teacher_trace_audit.md
outputs/reports/teacher_trace_audit.json
```

## 验收标准

```text
有明确数据分层
知道 high_quality_success 有多少
知道 productive_failure 有多少
知道是否需要补跑 mimo
有 teacher_trace_audit.md
```

---

# Phase C：Step-level SFT 数据构造

## 输入

```text
high_quality_success_traces.jsonl
productive_failure_traces.jsonl
当前 PromptBuilder
当前 action schema
当前 action_parser
```

## 目标

把高质量成功轨迹拆成 step-level prompt-completion 样本：

```text
当前任务 + 工具说明 + 历史 action/observation
→ 下一步 JSON action
```

## 数据格式

输出文件：

```text
outputs/data/step_sft_clean.jsonl
```

样本格式：

```json
{
  "sample_id": "bugfix_001_step_03",
  "task_id": "bugfix_001",
  "step": 3,
  "source": "mimo_high_quality_success",
  "bug_type": "boundary_condition",
  "prompt": "PromptBuilder 生成的完整 prompt",
  "completion": "{"thought":"Apply the minimal boundary-condition fix.","action":"edit_file","arguments":{"path":"auth.py","old":"return token_time < now","new":"return token_time <= now"}}",
  "action": "edit_file",
  "trace_label": "high_quality_success"
}
```

## completion 要求

每个 completion 必须：

```text
是单个 JSON object
不包含 ```json
不包含 markdown
不包含额外解释
thought 非空
action 合法
arguments 是 dict
符合统一 schema
能被 action_parser 解析
```

## 具体步骤

1. 读取 high_quality_success trace。
2. 遍历每条 trace 的 steps。
3. 每一步都用当前 PromptBuilder 重建 prompt。
4. 把当前 step 的 assistant action 转成 completion。
5. 统一 action schema。
6. 补全空 thought。
7. 用 action_parser 检验 completion。
8. 保存 step_sft_clean.jsonl。
9. 生成数据审计报告。

## 输出产物

```text
data_builder/build_step_sft.py
outputs/data/step_sft_clean.jsonl
outputs/reports/step_sft_data_audit.md
```

## 是否需要重跑

不需要。使用 Phase B 清洗后的已有 teacher 数据。

## 验收标准

```text
completion parse rate = 100%
thought 空值比例 = 0%
action schema 统一
PromptBuilder 与 eval 一致
```

---

# Phase D：Format-SFT / Repair-SFT 小规模 sanity check

## 输入

```text
step_sft_clean.jsonl
```

## 目标

先验证训练格式有效，不要直接全量训练。

## 两类 sanity check

### Format sanity check

取 100-200 条样本，覆盖所有 action。

目标：

```text
训练后在训练样本上 JSON Parse > 95%
Tool Valid > 95%
Arguments Valid > 95%
```

### Repair sanity check

取 50-100 条高质量修复样本。

目标：

```text
模型能在训练任务上复现关键 action
尤其是 edit_file 的 old/new 是否合理
```

## 训练参数建议

```yaml
model: Qwen2.5-Coder-3B-Instruct
method: QLoRA
lr: 5e-5 or 1e-4
epochs: 1-3 for sanity only
lora_r: 8 or 16
max_seq_length: 4096
```

## 输出产物

```text
models/3b_format_sanity_lora/
outputs/reports/format_sanity_report.md
outputs/reports/repair_sanity_report.md
```

## 验收标准

```text
训练集 JSON Parse > 95%
训练集 Tool Valid > 95%
```

未达到前，不进入正式 Step-SFT。

---

# Phase E：正式 Step-SFT 训练与评测

## 输入

```text
step_sft_clean.jsonl
```

## 数据混合比例

推荐：

```text
Format/tool samples: 30%
Repair strategy samples: 70%
```

如果 parse 仍差：

```text
Format/tool samples: 50%
Repair strategy samples: 50%
```

如果 parse 稳定：

```text
Format/tool samples: 20%
Repair strategy samples: 80%
```

## 训练参数建议

```yaml
model: Qwen2.5-Coder-3B-Instruct
method: QLoRA
load_in_4bit: true
max_seq_length: 4096
lora_r: 8 or 16
lora_alpha: 16 or 32
lora_dropout: 0.05
learning_rate: 5e-5 or 1e-4
epochs: 1
warmup_ratio: 0.03
bf16: true
```

## 评测对象

```text
3B Base
3B Old-SFT
3B Step-SFT
7B Base
```

## 评测指标

```text
Success Rate
JSON Parse Success
Tool Valid Rate
Run Tests Before Edit
Read Target File
Edit Target File
Test Pass After Edit
Avg Steps
Loop Rate
Premature Submit Rate
```

## 验收目标

最低目标：

```text
3B Step-SFT >= 3B Old-SFT
JSON Parse >= 80%
Tool Valid >= 80%
```

合格目标：

```text
3B Step-SFT > 3B Base 50%
Test Pass After Edit > 50%
```

优秀目标：

```text
3B Step-SFT 55%-60%
Loop Rate < 45%
JSON Parse > 85%
```

---

# Phase F：Runtime Guard 与 Loop 控制

## 为什么做

当前所有模型 loop rate 都在 53%-59%。  
这说明 loop 不只是模型问题，也是 runtime 控制问题。

## 原则

Guard 不替模型修 bug，只防止无效循环和明显不合规流程。

## 四个轻量 guard

### Guard 1：重复动作提醒

如果 same action + same arguments 连续出现，返回：

```text
You already executed the same action with the same arguments. Choose a different action that makes progress.
```

### Guard 2：edit 后测试提醒

如果最近执行了 edit_file，下一步不是 run_tests，提示：

```text
The code has been edited. Run tests before making further edits or submitting.
```

### Guard 3：tests passed 后提交提醒

如果 run_tests 已 passed，模型继续循环，提示：

```text
Tests have passed. Review the diff and submit the patch.
```

### Guard 4：submit 前必须有 passed test

如果没有 latest passed test 就 submit，返回：

```text
Submission requires a passing test after the latest edit. Run tests first.
```

## 输出产物

```text
harness/progress_guard.py
docs/runtime_guard_design.md
outputs/reports/guard_ablation.md
```

## 验收目标

```text
Loop Rate 下降 10%-20%
Avg Steps 不显著上升
Success Rate 不下降
Premature Submit Rate 下降
```

---

# Phase G：DPO 偏好优化

## 输入

```text
high_quality_success_traces.jsonl
productive_failure_traces.jsonl
bad_failure_traces.jsonl
Step-SFT 模型
```

## 目标

用 DPO 修正坏行为：

```text
错误编辑
跳过测试
过早提交
循环
过度修改
测试通过后不提交
```

## DPO pair 优先级

```text
same-task chosen/rejected
> same bug_type chosen/rejected
> same failure_type chosen/rejected
> 不建议 random pair
```

## Pair 类型

### 正确 patch vs 错误 patch

```text
chosen:
read target → minimal correct edit → run_tests pass → submit

rejected:
read target → edit target but wrong patch → run_tests fail → loop
```

### 测试驱动 vs 不测试

```text
chosen:
run_tests → read_file → edit_file → run_tests → submit

rejected:
read_file → edit_file → submit without tests
```

### 不循环 vs 循环

```text
chosen:
tests passed → git_diff → submit

rejected:
tests passed → repeated run_tests/read_file until max steps
```

## 输出产物

```text
outputs/data/dpo_pairs_v2.jsonl
outputs/reports/dpo_data_audit.md
training/train_dpo.py
models/3b_step_sft_dpo_lora/
outputs/reports/dpo_eval_report.md
```

## 何时开始

满足：

```text
Step-SFT JSON Parse >= 80%
Step-SFT Tool Valid >= 80%
Step-SFT 不低于 Old-SFT
```

再做 DPO。

## 验收目标

```text
Loop Rate 下降
Test Pass After Edit 上升
Success Rate 上升
Premature Submit 下降
```

---

# Phase H：GRPO-lite / BAR-lite 小规模实验

## 何时做

DPO 和 guard 做完后再做。  
不要把项目成败押在 GRPO 上。

## BAR-lite

每个 task 采样 4 条 rollout：

```text
全成功 → too_easy
全失败 → too_hard
有成功有失败 → informative
```

优先用 informative groups。

## Reward

```python
reward = 0.0

if tests_passed:
    reward += 1.0
if patch_apply:
    reward += 0.2
if tool_valid:
    reward += 0.1
if format_error:
    reward -= 0.3
if loop_detected:
    reward -= 0.2
if premature_submit:
    reward -= 0.2
```

## 输出

```text
data_builder/build_rollout_groups.py
training/train_grpo_lite.py
outputs/reports/grpo_smoke_test.md
outputs/reports/grpo_lite_eval.md
```

## 验收目标

```text
跑通 rollout → reward → update → eval
小规模任务上 success 或 loop 有改善
```

---

# Phase I：Skill Self-Distillation / OPSD-lite

## 目标

把成功轨迹总结为 reusable skill，再蒸馏给 student。

## 流程

```text
high_quality_success traces
→ summarize skill
→ skill memory
→ teacher-with-skill samples
→ student-without-skill step SFT
```

## Skill 示例

```text
Skill: Boundary Condition Fix

When equality-boundary tests fail, inspect comparison operators such as <, <=, >, >=.
Prefer a minimal one-line patch and rerun the failing test after editing.
```

## 输出

```text
outputs/data/skills.jsonl
outputs/data/skill_sd_step_sft.jsonl
training/train_skill_sd.py
outputs/reports/skill_sd_eval.md
```

## 何时做

这是高级加分项。  
必须在 Step-SFT / DPO / Guard 有初步效果后再做。

---

# 两周执行计划

## Day 1：冻结当前结果

```text
docs/current_eval_diagnosis.md
outputs/reports/current_metrics_table.md
```

## Day 2：Teacher trace 审计脚本

```text
data_builder/audit_teacher_traces.py
outputs/reports/teacher_trace_audit.md
```

## Day 3：Teacher trace 分层

```text
high_quality_success_traces.jsonl
productive_failure_traces.jsonl
bad_failure_traces.jsonl
```

## Day 4：统一 action schema

```text
docs/action_schema_v2.md
harness/action_schema.py
```

## Day 5：Step-level SFT builder

```text
data_builder/build_step_sft.py
outputs/data/step_sft_clean.jsonl
```

## Day 6：Step-SFT 数据审计

```text
outputs/reports/step_sft_data_audit.md
```

## Day 7：Format sanity SFT

```text
models/3b_format_sanity_lora/
outputs/reports/format_sanity_report.md
```

## Day 8：正式 Step-SFT

```text
models/3b_step_sft_lora/
```

## Day 9：Step-SFT 评测

```text
outputs/reports/step_sft_eval_report.md
```

## Day 10：Runtime Guard

```text
harness/progress_guard.py
outputs/reports/guard_ablation.md
```

## Day 11：DPO pair 构造

```text
outputs/data/dpo_pairs_v2.jsonl
outputs/reports/dpo_data_audit.md
```

## Day 12：DPO 训练

```text
models/3b_step_sft_dpo_lora/
```

## Day 13：DPO 评测

```text
outputs/reports/dpo_eval_report.md
```

## Day 14：阶段报告

```text
docs/phase2_report.md
README 更新
docs/resume_bullets.md
```

---

# 三周扩展计划

第三周做：

```text
BAR-lite
GRPO-lite
Skill-SD
最终报告
```

## Day 15-16：BAR-lite rollout groups

```text
outputs/data/informative_rollout_groups.jsonl
```

## Day 17-18：GRPO-lite smoke test

```text
outputs/reports/grpo_smoke_test.md
```

## Day 19：GRPO-lite eval

```text
outputs/reports/grpo_lite_eval.md
```

## Day 20：Skill-SD 数据

```text
outputs/data/skills.jsonl
outputs/data/skill_sd_step_sft.jsonl
```

## Day 21：最终报告

```text
docs/final_project_report.md
docs/interview_qa.md
```

---

# 最终阶段目标

## 最低目标

```text
Step-SFT 不低于 Old-SFT
JSON Parse >= 80%
Tool Valid >= 80%
```

## 合格目标

```text
Step-SFT Success >= 3B Base 50%
Test Pass After Edit >= 50%
Loop Rate <= 45%
```

## 优秀目标

```text
Step-SFT + DPO Success 55%-60%
JSON Parse >= 85%
Tool Valid >= 85%
Loop Rate < 40%
Test Pass After Edit > 55%
```

## 不现实目标

短期不要追：

```text
3B 超过 7B Base
3B 超过 mimo
GRPO 大幅提升
训练出 Qwen3-Coder 级别代码能力
```

---

# 简历表达更新

```text
M-code / EvoCode-Agent：面向代码修复任务的 Agentic Coding 后训练系统

- 构建本地 Env-lite 代码修复环境，支持 sandbox reset、结构化工具调用、pytest 测试反馈、patch diff、reward 计算与完整 trajectory logging。
- 设计多维 Agent 评测指标，覆盖 success rate、JSON parse、tool valid、read/edit target file、test pass after edit、loop rate 等，发现初始 SFT 虽提升目标文件读写行为，但导致 patch correctness 下降。
- 对已有 mimo-v2.5-pro teacher 轨迹进行清洗、质量分层和审计，筛选 high-quality success traces 作为 Step-level SFT 主数据，并将 productive failures 用于 DPO rejected 构造。
- 将训练数据从 trajectory-level transcript 重构为 step-level prompt-completion 格式，并统一 action schema，使训练目标与真实 Agent 推理过程对齐。
- 构造 same-task chosen/rejected 偏好对，用 DPO 抑制错误编辑、跳过测试、循环和过早提交等坏行为。
- 实现轻量 runtime guard 与 BAR-lite / GRPO-lite 方案，探索基于环境反馈的 Agentic Coding 强化学习闭环。
```

---

# 最终结论

Phase B 不应该理解为“重新跑 teacher”。

在你已有 mimo-v2.5-pro 成功/失败轨迹的情况下，Phase B 应该是：

```text
已有 teacher 轨迹清洗
→ 质量评分
→ 分层
→ 审计
→ high-quality success 筛选
→ productive failure 提取
→ Step-SFT / DPO / Skill-SD 数据源构建
```

只有当已有数据出现以下问题时，才需要补跑一小批 mimo：

```text
高质量成功轨迹不足
action schema 无法清洗
prompt 与当前版本严重不一致
缺少关键行为样本
```

后续最重要的不是继续盲目训练，而是：

```text
先把已有 mimo 轨迹变成高质量 teacher training data；
再做 step-level prompt-completion SFT；
再用 DPO 和 runtime guard 修正错误编辑和循环。
```

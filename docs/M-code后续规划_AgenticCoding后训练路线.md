# M-code / EvoCode-Agent 后续规划文档：从“训练 Coder 模型”转向“Agentic Coding 后训练系统”

> 项目仓库：M-code  
> 当前阶段：Agent Runtime / Env-lite / Benchmark / Trace / SFT 已跑通，进入训练诊断与路线重规划阶段。  
> 核心目标：不是从零训练一个 Coder 基座模型，而是在已有 Coder 模型基础上，构建面向代码修复任务的 Agent 后训练、自我进化和可评测闭环。  
> 当前推荐定位：**Coding Agent Post-training / Agentic Coding Distillation / Environment-grounded Tool-use Optimization**

---

## 0. 为什么需要重新规划？

之前项目的初始想法是：

```text
CT + SFT + RL + Agent 化 + OPSD / 自我进化
```

这个方向本身没有问题，但在实际实验后，需要重新校准目标。

当前实验结果显示：

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

这些结果说明：

1. **任务和框架是可行的。** 7B Base 达到 71.9%，说明 benchmark、tools、Env-lite、prompt 和 parser 基本能工作。
2. **3B Base 不是完全没有能力。** 3B Base 已有 50.0% success rate，说明任务不是只有 API 大模型才能做。
3. **当前 SFT 没有提升最终成功率。** 3B SFT 从 50.0% 降到 36.4%，说明当前 SFT 数据和训练方式存在问题。
4. **SFT 并不是完全没学到东西。** 它显著提高了 Read Target File 和 Edit Target File，说明它学到了流程动作。
5. **SFT 的核心问题是“学会了做动作，但没有学会改对”。** Test Pass After Edit 从 50.0% 降到 36.4%，说明 patch correctness 下降。
6. **所有模型 Loop Rate 都很高。** 53%-59% 的 loop rate 说明 Agent 控制、停止条件、重复动作处理仍需要优化。

因此，后续不能继续简单堆 SFT 数据，也不能马上上 DPO / GRPO。需要先重构训练目标和数据协议。

---

## 1. 项目重新定位

### 1.1 不要再把项目说成“训练 Coder 模型”

真正的 Qwen3-Coder / Qwen3-Coder-Next 这类模型，依赖：

```text
海量代码预训练
长上下文 repo-scale 训练
高质量代码数据清洗
合成任务数据
指令微调
agent trajectory SFT
environment-grounded RL
模型蒸馏
```

你的单卡 A6000 + 1000 条左右 SFT 数据，不可能训练出真正的 Coder 基座能力。

所以项目不能定位为：

```text
我训练了一个代码大模型。
```

### 1.2 正确定位

本项目应该定位为：

```text
基于已有 Coder 模型的 Agentic Coding 后训练系统。
```

更具体：

```text
给定一个已有 Coder 模型，构建代码修复 Agent 环境，收集工具调用轨迹，使用 teacher 成功轨迹、step-level SFT、DPO、GRPO-lite 和 Skill Distillation，提高模型在固定代码修复环境中的工具调用可靠性、修复行为和自我进化能力。
```

### 1.3 项目英文定位

```text
M-code: An Environment-grounded Coding Agent Post-training Framework with Step-level SFT, Preference Optimization and Skill Distillation
```

或者：

```text
EvoCode-Agent: A Self-evolving Coding Agent Post-training System for Tool-use and Code Repair
```

---

## 2. 当前实验的真实结论

### 2.1 不是任务不可解

7B Base 71.9%，mimo-v2.5-pro 之前也有较高成功率，说明：

```text
benchmark 可解
agent loop 可运行
tools 基本有效
parser 修复后能工作
```

因此不能说项目方向失败。

### 2.2 不是 3B 完全无能力

3B Base 50.0%，说明：

```text
3B 能完成一部分 toy code repair task
3B 可以输出部分可解析 action
3B 有一定基础代码修复能力
```

所以“3B 完全不行”不是准确结论。

### 2.3 当前 SFT 是“流程增强、修复退化”

SFT 后：

```text
Read Target File: 21.4% → 68.2%
Edit Target File: 67.9% → 93.2%
Tool Valid Rate: 64.3% → 68.2%
Run Tests Before Edit: 3.6% → 9.1%
```

说明 SFT 学到了：

```text
更会读目标文件
更会编辑目标文件
更像一个工具调用 Agent
```

但是：

```text
Success Rate: 50.0% → 36.4%
Test Pass After Edit: 50.0% → 36.4%
JSON Parse Success: 67.9% → 61.4%
```

说明 SFT 没学到：

```text
如何做正确 patch
如何从测试反馈中修正
如何稳定输出 parse-safe JSON
如何避免模板化错误
```

### 2.4 当前 SFT 的核心问题

当前问题不是单纯 LoRA 参数，也不是数据量太少，而是：

```text
训练目标和真实 Agent 行为目标不一致。
```

具体包括：

1. trajectory-level 数据没有拆成 step-level action samples；
2. 训练 prompt 和 eval prompt 可能不完全一致；
3. action schema 可能不统一；
4. thought 质量不足或为空；
5. 训练数据可能过于模板化；
6. 成功轨迹质量不足，3B 自己的低质量轨迹占比过高；
7. 没有把 7B/mimo 的高质量修复策略蒸馏给 3B；
8. 没有针对错误编辑、循环、跳过测试做偏好优化。

---

## 3. 后续总体路线

后续路线应该从：

```text
继续堆 SFT 数据
```

改为：

```text
Teacher Distillation + Step-level SFT + DPO + Loop Control + GRPO-lite
```

总体流程：

```text
Phase A: 数据协议重构
Phase B: Teacher 轨迹采集
Phase C: Step-level SFT
Phase D: 行为评测与失败分析
Phase E: DPO 偏好优化
Phase F: Loop / Submit / Test Guard
Phase G: GRPO-lite 小规模实验
Phase H: Skill Self-Distillation / OPSD-lite
Phase I: 最终报告和简历包装
```

---

## 4. Phase A：数据协议重构

### 4.1 目标

把旧的 `sft_clean.jsonl` 从“整条轨迹 transcript”改造成：

```text
当前 Agent 状态 → 下一步 JSON action
```

也就是 step-level prompt-completion 数据。

### 4.2 为什么必须做 step-level？

Agent 在真实运行时，每一步面对的是：

```text
当前任务
+ 工具说明
+ 历史 action / observation
```

然后输出：

```text
下一步 JSON action
```

如果训练时直接喂整条 trajectory，模型会同时学习：

```text
system prompt
user issue
assistant action
tool output
pytest output
submit message
```

训练目标太杂，不利于学“下一步动作”。

### 4.3 新数据格式

建议新文件：

```text
data/step_sft_clean.jsonl
```

每条样本格式：

```json
{
  "task_id": "bugfix_001",
  "step": 0,
  "source": "teacher_7b_success",
  "bug_type": "boundary_condition",
  "prompt": "与 eval 完全一致的 PromptBuilder 输出，包含工具说明、任务、history",
  "completion": "{\"thought\":\"Run the failing tests first to observe the failure.\",\"action\":\"run_tests\",\"arguments\":{}}",
  "action": "run_tests",
  "success_trace": true
}
```

### 4.4 核心要求

1. prompt 必须和 eval 使用同一个 PromptBuilder。
2. completion 必须是单个 JSON object。
3. completion 不能用 markdown code block。
4. action schema 必须统一。
5. thought 不能为空。
6. 每条 completion 必须能被 action_parser 解析。
7. completion-only loss，尽量不要训练 prompt 部分。
8. 每条数据保留 source，方便做数据审计。

### 4.5 工具 schema 统一

建议第一版固定如下：

```json
{"action": "list_files", "arguments": {}}
{"action": "run_tests", "arguments": {}}
{"action": "git_diff", "arguments": {}}
{"action": "submit_patch", "arguments": {}}
{"action": "read_file", "arguments": {"path": "xxx.py"}}
{"action": "search_code", "arguments": {"query": "keyword"}}
{"action": "edit_file", "arguments": {"path": "xxx.py", "old": "...", "new": "..."}}
```

尤其要避免：

```json
{"action": "run_tests", "arguments": {"command": "..."}}
{"action": "run_tests", "arguments": {"path": "..."}}
```

如果 test command 已在 metadata 中，就不要让模型自己传 command。

---

## 5. Phase B：Teacher 轨迹采集

### 5.1 为什么需要 teacher？

当前 3B SFT 的问题是：

```text
学会流程动作，但没有学会正确修复。
```

所以后续不能主要让 3B 从自己的轨迹里学。应该让强模型做 teacher：

```text
mimo-v2.5-pro
Qwen2.5-Coder-7B Base
后续可选 Qwen3-Coder
```

### 5.2 Teacher 的角色

| 模型 | 角色 |
|---|---|
| 7B Base | strong baseline / teacher |
| mimo-v2.5-pro | stronger teacher |
| 3B Base | student baseline |
| 3B SFT | student model |
| 3B DPO | refined student |

### 5.3 数据质量排序

推荐优先级：

```text
mimo 成功轨迹
> 7B Base 成功轨迹
> 人工审核成功轨迹
> 3B Base 成功轨迹
> 修复后的失败轨迹
> 旧 scripted trace
```

### 5.4 Teacher trace 采集标准

每条 teacher trace 必须满足：

```text
最终测试通过
修改目标文件
patch 最小化
没有无关文件修改
有 run_tests 验证
submit 前测试通过
没有明显 loop
```

### 5.5 Teacher trace 过滤规则

过滤掉：

```text
成功但修改过大
成功但没有 run_tests
成功但多次循环
成功但 edit_file old/new 不稳定
成功但 observation 与 action 不对应
```

### 5.6 输出文件

```text
trajectories/teacher/mimo_success/
trajectories/teacher/7b_success/
outputs/data/teacher_success_traces.jsonl
outputs/data/teacher_step_sft.jsonl
```

---

## 6. Phase C：Step-level SFT

### 6.1 训练目标

第一阶段不要直接追 task success，先分两类目标：

#### 目标 1：Format / Tool Stability

指标：

```text
JSON Parse Success
Tool Valid Rate
Arguments Valid Rate
```

目标值：

```text
JSON Parse Success: 85%+
Tool Valid Rate: 85%+
```

#### 目标 2：Repair Strategy

指标：

```text
Success Rate
Test Pass After Edit
Edit Target File
Run Tests After Edit
```

目标值：

```text
3B Step-SFT Success > 3B Base
Test Pass After Edit > 3B Base
```

### 6.2 数据混合比例

推荐第一轮：

```text
Format / schema samples: 30%
Teacher repair samples: 70%
```

如果 JSON parse 仍然差：

```text
Format / schema samples: 50%
Teacher repair samples: 50%
```

如果 JSON parse 已经稳定：

```text
Format / schema samples: 20%
Teacher repair samples: 80%
```

### 6.3 训练参数建议

第一轮保守训练：

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
gradient_accumulation_steps: 8
bf16: true
```

不要一开始：

```text
大 lr
多 epoch
所有旧数据混合
```

### 6.4 Sanity Check

必须先做小样本 sanity check：

```text
100 条 step-level samples
训练 1-3 epoch
在训练样本上测试 prompt → completion
```

目标：

```text
训练集 JSON Parse > 95%
训练集 Tool Valid > 95%
```

如果做不到，不要扩大全量训练。

### 6.5 评测表

```markdown
| Model | Success | JSON Parse | Tool Valid | Read Target | Edit Target | Test Pass After Edit | Loop |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3B Base | 50.0 | 67.9 | 64.3 | 21.4 | 67.9 | 50.0 | 53.6 |
| 3B Old-SFT | 36.4 | 61.4 | 68.2 | 68.2 | 93.2 | 36.4 | 54.5 |
| 3B Step-SFT | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| 7B Base | 71.9 | 68.8 | 65.6 | 25.0 | 100.0 | 71.9 | 59.4 |
```

---

## 7. Phase D：失败分析

每次训练后必须做 failure analysis，不要只看 success。

### 7.1 关键失败类型

```text
FORMAT_ERROR
INVALID_TOOL
INVALID_ARGUMENTS
WRONG_FILE_EDIT
EDIT_TARGET_BUT_WRONG_PATCH
NO_TEST_AFTER_EDIT
PREMATURE_SUBMIT
LOOP_SAME_ACTION
LOOP_NO_PROGRESS
TEST_FAIL_AFTER_EDIT
SUCCESS_BUT_NO_SUBMIT
```

### 7.2 当前最重要的失败类型

结合当前结果，最重要的是：

```text
EDIT_TARGET_BUT_WRONG_PATCH
LOOP_NO_PROGRESS
NO_TEST_AFTER_EDIT
PREMATURE_SUBMIT
FORMAT_ERROR
```

### 7.3 分析输出

建议生成：

```text
outputs/reports/failure_shift_base_vs_sft.md
outputs/reports/failure_cases/
outputs/reports/per_bug_type_metrics.csv
```

### 7.4 每个失败案例记录

```json
{
  "task_id": "bugfix_010",
  "model": "3b_step_sft",
  "failure_type": "EDIT_TARGET_BUT_WRONG_PATCH",
  "expected_behavior": "...",
  "model_patch": "...",
  "test_output": "...",
  "diagnosis": "Model edited the correct file but changed the wrong condition."
}
```

---

## 8. Phase E：DPO 偏好优化

### 8.1 为什么 DPO 适合当前阶段？

当前 SFT 已经让模型更会读/改目标文件，但 patch 质量下降。  
这说明模型需要学习“好行为优于坏行为”，而不是继续模仿所有轨迹。

DPO 适合修：

```text
错误编辑
跳过测试
过早提交
循环
过度修改
测试通过后不提交
```

### 8.2 DPO 数据构造原则

优先级：

```text
same task chosen/rejected
> same bug_type chosen/rejected
> similar failure_type chosen/rejected
> 不建议 random chosen/rejected
```

### 8.3 偏好对类型

#### Pair 1：正确 patch vs 错误 patch

```text
chosen:
read target file → minimal correct edit → run_tests pass → submit

rejected:
read target file → edit target file but wrong patch → run_tests fail → loop
```

#### Pair 2：测试驱动 vs 不测试

```text
chosen:
run_tests → read_file → edit_file → run_tests → submit

rejected:
read_file → edit_file → submit without tests
```

#### Pair 3：不循环 vs 循环

```text
chosen:
tests passed → git_diff → submit

rejected:
tests passed → repeated read_file/run_tests until max_steps
```

#### Pair 4：最小编辑 vs 过度编辑

```text
chosen:
one-line fix

rejected:
large unrelated changes
```

#### Pair 5：失败后修正 vs 原地重复

```text
chosen:
run_tests fail → inspect error → adjust patch → run_tests pass

rejected:
run_tests fail → repeat same edit / same test
```

### 8.4 DPO 目标指标

```text
Loop Rate 下降
Premature Submit 下降
Test Pass After Edit 上升
Success Rate 上升
```

### 8.5 DPO 前置条件

只有 Step-SFT 达到以下条件后，再做 DPO：

```text
JSON Parse Success >= 80%
Tool Valid Rate >= 80%
Success Rate >= 3B Old-SFT
```

如果 Step-SFT 还不稳定，不要急着 DPO。

---

## 9. Phase F：Agent 控制与 Loop Guard

### 9.1 为什么需要 Guard？

所有模型 Loop Rate 都很高：

```text
3B Base: 53.6%
3B SFT: 54.5%
7B Base: 59.4%
```

这说明 loop 不是某个模型的问题，而是 Agent 控制层也需要处理。

### 9.2 Guard 不是抢模型决策权

Guard 的作用不是硬编码答案，而是防止无效循环和不合法流程。

它属于：

```text
runtime safety / progress control
```

不是：

```text
Python 替模型做修复决策
```

### 9.3 推荐四个轻量 Guard

#### Guard 1：重复动作提醒

如果连续出现：

```text
same action + same arguments
```

系统返回：

```text
You already executed the same action with the same arguments. Choose a different action that makes progress.
```

#### Guard 2：edit 后测试提醒

如果已经 `edit_file`，但模型继续读文件或编辑，提示：

```text
The code has been edited. Run tests before making further edits or submitting.
```

#### Guard 3：测试通过后提交提醒

如果 `run_tests` passed，模型还继续循环，提示：

```text
Tests have passed. You should review the diff and submit the patch.
```

#### Guard 4：submit 前必须测试通过

如果没有 passed test 就 submit：

```text
Submission requires a passing test after the latest edit. Run tests first.
```

### 9.4 Guard 的评测指标

加 guard 前后对比：

```text
Loop Rate
Success Rate
Avg Steps
Premature Submit Rate
Success But No Submit Rate
```

### 9.5 注意

Guard 不要太多。  
第一版只加这四个。  
不要写针对具体 bug 的规则。

---

## 10. Phase G：GRPO-lite / Environment-grounded RL

### 10.1 什么时候做 GRPO-lite？

满足以下条件后再做：

```text
Step-SFT 比 3B Base 不差
JSON Parse >= 85%
Tool Valid >= 85%
Loop Rate 已通过 guard 有所下降
```

否则 GRPO 很容易浪费时间。

### 10.2 GRPO-lite 的目标

不是追求 SOTA，而是证明：

```text
模型可以在可执行环境中 rollout
根据 reward 更新
并在小规模任务上改善行为
```

### 10.3 Reward 设计

第一版 reward：

```python
reward = 0.0

if result.tests_passed:
    reward += 1.0

if result.patch_apply:
    reward += 0.2

if result.tool_valid:
    reward += 0.1

if result.format_error:
    reward -= 0.3

if result.loop_detected:
    reward -= 0.2

if result.premature_submit:
    reward -= 0.2
```

不要过度复杂。

### 10.4 BAR-lite 采样策略

每个 task 采样 4 条 rollout：

```text
全成功 → too_easy
全失败 → too_hard
有成功有失败 → informative
```

只优先用 informative groups 做 DPO / GRPO。

### 10.5 GRPO-lite 评测目标

```text
Success Rate 小幅提升
Loop Rate 下降
Test Pass After Edit 上升
Format Error 不恶化
```

---

## 11. Phase H：Skill Self-Distillation / OPSD-lite

### 11.1 目标

把成功轨迹总结成可复用经验，然后蒸馏给 student。

### 11.2 流程

```text
teacher success traces
→ summarize skill
→ skill memory
→ teacher-with-skill trajectory
→ student-without-skill SFT
```

### 11.3 Skill 示例

```text
Skill: Boundary Condition Fix

When tests fail on equality boundary cases, inspect comparison operators such as <, <=, >, >=.
Prefer a minimal one-line change and rerun the failing test after editing.
```

### 11.4 数据格式

```json
{
  "skill_id": "boundary_condition_fix",
  "bug_type": "boundary_condition",
  "skill": "When equality boundary tests fail, inspect comparison operators such as <, <=, >, >=.",
  "positive_trace": "teacher success trace",
  "student_prompt": "task + tools + history without explicit skill",
  "student_completion": "next JSON action"
}
```

### 11.5 何时做？

这是高级加分项。  
建议放在 Step-SFT 和 DPO 有效果之后。

---

## 12. 未来 2 周执行计划

### Day 1：冻结当前实验结果

输出：

```text
docs/current_eval_diagnosis.md
outputs/reports/current_metrics_table.md
```

内容包括：

```text
3B Base vs 3B Old-SFT vs 7B Base
核心结论：SFT 学到流程，但修复退化
```

### Day 2：重构 action schema

输出：

```text
docs/action_schema_v2.md
harness/action_schema.py
```

统一：

```text
run_tests {}
submit_patch {}
git_diff {}
list_files {}
read_file {"path": ...}
search_code {"query": ...}
edit_file {"path": ..., "old": ..., "new": ...}
```

### Day 3：实现 step-level builder

输出：

```text
data_builder/build_step_sft.py
outputs/data/step_sft_clean.jsonl
```

要求：

```text
每条 completion 可被 parser 解析
prompt 与 eval PromptBuilder 一致
```

### Day 4：teacher trace 采集

输出：

```text
trajectories/teacher/7b_success/
trajectories/teacher/mimo_success/
```

至少：

```text
50-100 条高质量成功轨迹
```

### Day 5：数据审计

输出：

```text
outputs/reports/step_sft_data_audit.md
```

统计：

```text
action 分布
bug_type 分布
source 分布
completion parse rate
thought 空值比例
run_tests 比例
edit_file 比例
```

### Day 6：100 条 sanity SFT

输出：

```text
models/3b_format_sanity_lora/
outputs/reports/sanity_eval.md
```

目标：

```text
训练集 JSON Parse > 95%
训练集 Tool Valid > 95%
```

### Day 7：Step-SFT 训练

输出：

```text
models/3b_step_sft_lora/
```

训练数据：

```text
300-1000 条 step-level samples
```

### Day 8：Step-SFT 评测

输出：

```text
outputs/reports/base_vs_old_sft_vs_step_sft.md
```

判断：

```text
是否超过 3B Base
是否修复 JSON parse
是否提升 Test Pass After Edit
```

### Day 9：实现 loop guard

输出：

```text
harness/progress_guard.py
docs/runtime_guard_design.md
```

只做四个 guard：

```text
repeat action
edit-after-test reminder
tests-passed-submit reminder
submit requires passed test
```

### Day 10：Guard 前后评测

输出：

```text
outputs/reports/guard_ablation.md
```

对比：

```text
3B Base without guard
3B Base with guard
3B Step-SFT without guard
3B Step-SFT with guard
7B Base with guard
```

### Day 11：构造 DPO 数据

输出：

```text
outputs/data/dpo_pairs_v2.jsonl
outputs/reports/dpo_data_audit.md
```

优先 same-task pairs。

### Day 12：DPO 训练

输出：

```text
models/3b_step_sft_dpo_lora/
```

### Day 13：DPO 评测

输出：

```text
outputs/reports/dpo_eval_report.md
```

重点看：

```text
loop rate
test pass after edit
success rate
premature submit
```

### Day 14：整理阶段报告

输出：

```text
docs/phase2_report.md
docs/next_phase_grpo_plan.md
README 更新
```

---

## 13. 未来 3 周执行计划

第三周做进阶项。

### Day 15：BAR-lite rollout group

输出：

```text
data_builder/build_rollout_groups.py
outputs/data/informative_rollout_groups.jsonl
```

### Day 16：GRPO-lite smoke test

输出：

```text
training/train_grpo_lite.py
outputs/reports/grpo_smoke_test.md
```

### Day 17-18：小规模 GRPO-lite

输出：

```text
models/3b_grpo_lite_lora/
```

只用：

```text
30-50 个 easy tasks
每个 4 rollout
```

### Day 19：GRPO-lite 评测

输出：

```text
outputs/reports/grpo_lite_eval.md
```

### Day 20：Skill-SD 数据构造

输出：

```text
outputs/data/skills.jsonl
outputs/data/skill_sd_step_sft.jsonl
```

### Day 21：最终报告

输出：

```text
docs/final_project_report.md
docs/resume_bullets.md
docs/interview_qa.md
```

---

## 14. 阶段目标

### 最低目标

```text
Step-SFT 不低于 3B Base
JSON Parse > 80%
Tool Valid > 80%
Read Target File 保持高水平
Edit Target File 保持高水平
```

### 合格目标

```text
3B Step-SFT Success > 50%
Test Pass After Edit > 50%
Loop Rate 降到 40%-45%
```

### 优秀目标

```text
3B Step-SFT + DPO Success 55%-60%
Loop Rate < 40%
JSON Parse > 85%
Tool Valid > 85%
Test Pass After Edit > 55%
```

### 不现实目标

短期不要追：

```text
3B 超过 7B Base
3B 超过 mimo
GRPO 大幅提升
训练出 Qwen3-Coder 级代码能力
```

---

## 15. 项目报告应该怎么讲

### 15.1 项目定位

```text
本项目不尝试从零训练 Coder 基座模型，而是关注 Agentic Coding 后训练阶段。我们构建了一个可执行的代码修复环境，支持工具调用、测试反馈、轨迹记录和自动评测，并研究如何通过 teacher distillation、step-level SFT、DPO 和 environment reward 提升小模型在代码修复 Agent 场景中的行为可靠性。
```

### 15.2 当前发现

```text
初始 SFT 并未提升最终成功率。进一步指标分析发现，SFT 显著提高了目标文件读取率和编辑率，但降低了测试通过率，说明模型主要学习到了流程性动作，而没有学习到高质量修复策略。该发现促使我们将训练数据从 trajectory-level transcript 重构为 step-level prompt-completion，并引入 7B/mimo teacher 成功轨迹作为修复策略蒸馏数据。
```

### 15.3 技术亮点

```text
1. Env-lite executable code repair environment
2. Structured tool-call agent harness
3. Full trajectory logging
4. Fine-grained behavior metrics
5. Step-level SFT data construction
6. Teacher-student repair trajectory distillation
7. DPO for bad behavior suppression
8. Runtime loop guard
9. GRPO-lite / environment-grounded reward
10. Skill Self-Distillation / OPSD-lite
```

---

## 16. 简历写法更新

### 中文版

```text
M-code / EvoCode-Agent：面向代码修复任务的 Agentic Coding 后训练系统

- 构建本地 Env-lite 代码修复环境，支持 sandbox reset、结构化工具调用、pytest 测试反馈、patch diff、reward 计算与完整 trajectory logging。
- 设计多维 Agent 评测指标，覆盖 success rate、JSON parse、tool valid、read/edit target file、test pass after edit、loop rate 等，发现初始 SFT 虽提升目标文件读写行为，但导致 patch correctness 下降。
- 将训练数据从 trajectory-level transcript 重构为 step-level prompt-completion 格式，并统一 action schema，使训练目标与真实 Agent 推理过程对齐。
- 使用 Qwen2.5-Coder-7B / mimo-v2.5-pro 成功轨迹作为 teacher 数据，蒸馏 3B student 的代码修复策略，区分 format/tool SFT 与 repair strategy SFT。
- 构造 same-task chosen/rejected 偏好对，用 DPO 抑制错误编辑、跳过测试、循环和过早提交等坏行为。
- 实现轻量 runtime guard 与 BAR-lite / GRPO-lite 方案，探索基于环境反馈的 Agentic Coding 强化学习闭环。
```

### 英文版

```text
M-code / EvoCode-Agent: Agentic Coding Post-training System for Code Repair

- Built a local Env-lite code repair environment with sandbox reset, structured tool calls, pytest-based feedback, patch diff, reward computation and full trajectory logging.
- Designed fine-grained evaluation metrics including success rate, JSON parse rate, tool validity, target-file read/edit rate, test-pass-after-edit and loop rate, revealing that naive SFT improved procedural behaviors but degraded patch correctness.
- Reconstructed trajectory-level transcripts into step-level prompt-completion data and unified the action schema to align training objectives with the actual agent inference loop.
- Used Qwen2.5-Coder-7B and mimo-v2.5-pro successful trajectories as teacher data to distill repair strategies into a 3B student model.
- Built same-task DPO preference pairs to suppress wrong edits, skipped tests, repetitive loops and premature submissions.
- Implemented lightweight runtime guards and designed BAR-lite / GRPO-lite experiments for environment-grounded agentic coding optimization.
```

---

## 17. 最终结论

后续项目不要继续围绕：

```text
怎么把 1000 条 SFT 再训几轮
```

而应该围绕：

```text
如何让已有 Coder 模型在 Agent 环境中更可靠地行动
```

接下来最关键的三件事：

```text
1. 重建 step-level prompt-completion 数据
2. 用 7B/mimo teacher 成功轨迹蒸馏 3B
3. 用 DPO + loop guard 修正错误编辑和循环行为
```

这才是当前项目最合理、最有希望的路线。

最终项目目标不是训练出一个 Qwen3-Coder，而是证明：

```text
在固定代码修复 Agent 环境中，
通过环境轨迹、teacher 蒸馏、step-level SFT、DPO 和 runtime guard，
可以让小模型在工具调用、测试驱动修复和任务完成率上获得可测量提升。
```

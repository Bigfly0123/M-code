# EvoCode-Orchard-Lite 项目方案：受 Orchard 启发的 Coding Agent 后训练与自我进化系统

> 目标：在 2-3 周内做出一个能写进简历、能面试讲清楚、能真实跑通的 AI Agent 后训练项目。  
> 方向：AI Agent 开发 / 大模型应用工程 / Agentic RL / Coding Agent。  
> 资源假设：单卡 A6000 48G。  
> 核心策略：不做普通 RAG，不盲目复现大论文，不直接魔改大框架；做一个轻量但完整的 Orchard-lite Coding Agent 后训练闭环。

---

## 0. 为什么要重写这一版文档？

之前的方案已经明确了：

```text
Coding Agent Runtime
→ 代码修复任务集
→ 轨迹记录
→ SFT
→ DPO
→ 小规模 GRPO
→ OPSD-lite / Skill Self-Distillation
```

但还不够到位的地方有几个：

1. 没有把“环境层 Env”提高到足够重要的位置。
2. 没有明确说明为什么 Orchard 对这个项目有启发。
3. 没有说明为什么不能直接复刻 Orchard。
4. 没有加入 Credit-assignment SFT-lite。
5. 没有加入 Balanced Adaptive Rollout-lite。
6. 没有进一步区分“必成部分”和“挑战部分”。
7. 没有明确说明 mini-swe-agent / SWE-agent / Orchard 三者在项目中的角色。

这版文档的目标是把项目定位升级成：

> **EvoCode-Orchard-Lite：受 Orchard 启发的轻量级 Coding Agent 后训练与自我进化系统。**

---

## 1. 项目一句话定位

本项目不是普通代码助手，也不是普通 RAG 项目，而是：

> **实现一个本地轻量版 Orchard-style Agent Environment，围绕代码修复任务构建 Agent Runtime、Sandbox、Trajectory、Reward、SFT/DPO/GRPO 数据闭环，并通过 Credit-SFT-lite、BAR-lite 和 Skill Self-Distillation 实现 Agent 自我进化。**

更简单地说：

```text
让一个 Coding Agent 在代码修复环境里反复执行任务；
记录它的成功和失败轨迹；
把轨迹转成 SFT / DPO / RL 数据；
用 LoRA / QLoRA 训练小模型；
再通过 Skill 总结和自蒸馏形成自我进化闭环。
```

---

## 2. 为什么这个项目有价值？

现在 RAG 简历项目已经很多，普通项目通常是：

```text
上传文档 → 向量检索 → LLM 回答
```

这类项目的问题是：

- 场景太泛
- 工程深度不足
- 没有训练
- 没有复杂环境交互
- 没有真实 reward
- 没有 agent trajectory
- 没有模型能力提升闭环

而本项目的核心差异是：

```text
Agent 与环境交互
+ 多步工具调用
+ 自动测试 reward
+ 轨迹数据构造
+ 后训练
+ 自我进化
+ 评测对比
```

这更贴近岗位里常见的：

- AI Agent 开发
- Tool Use
- Coding Agent
- Agent Runtime
- Agent Infra
- LLM 后训练
- SFT / DPO / RL
- Agentic RL
- Self-Evolving Agent

---

## 3. Orchard 给我们的核心启发

Orchard 是微软研究院、哥伦比亚大学、UIUC 团队联合提出的 open-source agentic modeling framework。

它不是普通 Agent 编排框架，而是强调：

> **可复用的环境层 Env 是 Agent 训练、rollout、评测和自我进化的基础设施。**

Orchard 的核心思想可以总结成：

```text
Environment-first
Trajectory-centric
Harness-agnostic
Training-recipe-friendly
Evaluation-reusable
```

也就是：

1. 先有可控环境。
2. Agent 在环境里执行任务。
3. 保存完整轨迹。
4. 轨迹可以用于 SFT、RL、Eval。
5. 同一个环境层不绑定某一个 Agent 框架。
6. 同一批轨迹可以被不同 trainer / model / harness 复用。

这对我们非常关键。

之前我们容易把重点放在：

```text
我要写一个 Agent Loop。
```

但 Orchard 的启发是：

```text
你真正要先设计的是 Agent 的环境层和轨迹层。
```

因为没有环境层，就没有可靠 reward。  
没有轨迹层，就没有 SFT / DPO / RL 数据。  
没有评测层，就不知道模型是否变强。

---

## 4. 为什么不能直接复刻 Orchard？

Orchard 很高级，但不适合作为 2-3 周个人项目直接复刻。

原因：

1. Orchard Env 是 Kubernetes-native 的环境服务。
2. 它涉及 sandbox lifecycle、command execution、file I/O、network policy、REST API 等。
3. Orchard-SWE 规模是研究团队级别，包含大量 SWE 轨迹。
4. 它面向的是 scalable agentic modeling，不是个人快速项目。
5. 直接复刻会把时间耗在 K8s、分布式环境、部署和工程复杂度上。
6. 你现在最需要的是做出可展示闭环，而不是搭一个大基础设施。

所以我们的策略不是：

```text
复现 Orchard
```

而是：

```text
做一个 Orchard-inspired Local Env-lite。
```

---

## 5. 什么是 Orchard-lite？

Orchard-lite 是本项目的本地轻量版环境层。

它不做 Kubernetes，不做分布式，不做复杂网络策略。

它只做个人项目必要的核心能力：

```text
1. sandbox 初始化
2. repo 文件读写
3. 命令执行
4. pytest 测试
5. patch / diff
6. reward 计算
7. trace logging
8. 环境 reset
9. 任务批量评测
```

### Orchard Env vs 本项目 Env-lite

| 维度 | Orchard Env | EvoCode Env-lite |
|---|---|---|
| 部署 | Kubernetes-native | 本地 Docker / subprocess |
| 目标 | 大规模 agentic modeling | 个人可控项目闭环 |
| 环境生命周期 | Pod / sandbox lifecycle | 本地 task workspace reset |
| 文件操作 | REST API / sandbox file I/O | Python file I/O |
| 命令执行 | Env service command execution | subprocess / Docker exec |
| 网络策略 | Network policy | 第一版不做 |
| 轨迹规模 | 大规模 rollouts | 30-300 个小任务 |
| 训练 | SFT + RL recipes | SFT 必做，DPO/GRPO 进阶 |
| 周期 | 团队级 | 2-3 周 |

---

## 6. 项目最终架构

```text
EvoCode-Orchard-Lite
│
├── Env-lite
│   ├── sandbox reset
│   ├── command execution
│   ├── file I/O
│   ├── test execution
│   ├── patch apply / diff
│   └── reward calculation
│
├── Agent Harness
│   ├── mini-swe-agent style loop
│   ├── prompt builder
│   ├── action parser
│   ├── tool registry
│   └── step controller
│
├── Trajectory Layer
│   ├── raw trace
│   ├── success trace
│   ├── failed trace
│   ├── productive segment
│   └── rollout group
│
├── Data Builder
│   ├── SFT data
│   ├── Credit-SFT-lite data
│   ├── DPO preference pair
│   ├── GRPO rollout data
│   └── Skill-SD data
│
├── Training Pipeline
│   ├── LoRA / QLoRA SFT
│   ├── DPO
│   ├── GRPO-lite
│   └── Skill Self-Distillation
│
└── Eval Suite
    ├── task success rate
    ├── test pass rate
    ├── tool valid rate
    ├── format error rate
    ├── patch apply rate
    ├── avg steps
    └── failure taxonomy
```

---

## 7. 项目名称建议

中文：

```text
EvoCode-Orchard-Lite：受 Orchard 启发的 Coding Agent 后训练与自我进化系统
```

英文：

```text
EvoCode-Orchard-Lite: An Orchard-inspired Coding Agent Post-training Framework with SFT, RL and Skill Self-Distillation
```

简历中也可以简化为：

```text
EvoCode-Agent: Self-Evolving Coding Agent with Environment-grounded SFT/RL
```

---

## 8. 项目技术关键词

你后续简历和面试可以围绕这些词展开：

```text
Coding Agent
Agent Runtime
Agent Harness
Environment Layer
Sandbox
Tool Use
Trajectory Logging
SFT
DPO
GRPO
Credit-assignment SFT
Balanced Adaptive Rollout
Reward Function
Agentic RL
Skill Memory
OPSD-lite
Self-Distillation
LoRA / QLoRA
Evaluation
Failure Analysis
```

---

## 9. 固定场景：代码修复任务

### 为什么选代码修复？

因为代码修复天然适合 Agent 后训练：

```text
有任务输入：issue / failing test
有工具调用：read_file / edit_file / run_tests
有环境反馈：pytest output
有自动 reward：test pass / fail
有轨迹数据：multi-turn interaction
有明确评测：success rate
```

### 不建议第一版做真实 SWE-bench

SWE-bench 难度高，依赖复杂，容易拖垮 2-3 周计划。

第一版建议做：

```text
Toy CodeRepair Benchmark
```

任务类型：

```text
1. 边界条件错误
2. 参数顺序错误
3. 类型转换错误
4. dict key 错误
5. list index off-by-one
6. None 判断错误
7. regex 错误
8. 日期比较错误
9. 返回格式错误
10. 简单算法错误
```

---

## 10. 推荐目录结构

```text
evocode-orchard-lite/
├── README.md
├── requirements.txt
├── configs/
│   ├── agent.yaml
│   ├── model.yaml
│   ├── train_sft.yaml
│   ├── train_dpo.yaml
│   └── train_grpo.yaml
│
├── env_lite/
│   ├── code_repair_env.py
│   ├── sandbox.py
│   ├── command_executor.py
│   ├── file_manager.py
│   ├── test_runner.py
│   ├── reward.py
│   └── reset.py
│
├── harness/
│   ├── agent_loop.py
│   ├── prompt_builder.py
│   ├── action_parser.py
│   ├── tool_registry.py
│   └── controller.py
│
├── tools/
│   ├── list_files.py
│   ├── read_file.py
│   ├── search_code.py
│   ├── edit_file.py
│   ├── run_tests.py
│   ├── git_diff.py
│   └── submit_patch.py
│
├── benchmark/
│   ├── tasks/
│   │   ├── bugfix_001/
│   │   │   ├── repo/
│   │   │   ├── tests/
│   │   │   ├── issue.md
│   │   │   └── metadata.json
│   │   └── bugfix_002/
│   └── build_tasks.py
│
├── trajectories/
│   ├── raw/
│   ├── success/
│   ├── failed/
│   ├── productive_segments/
│   └── rollout_groups/
│
├── data_builder/
│   ├── build_sft.py
│   ├── build_credit_sft.py
│   ├── build_dpo.py
│   ├── build_grpo.py
│   ├── build_skills.py
│   └── filter_traces.py
│
├── training/
│   ├── train_sft.py
│   ├── train_dpo.py
│   ├── train_grpo.py
│   └── train_skill_sd.py
│
├── eval/
│   ├── run_eval.py
│   ├── metrics.py
│   ├── failure_analysis.py
│   └── report_generator.py
│
├── outputs/
│   ├── models/
│   ├── reports/
│   └── figures/
│
└── dashboard/
    └── app.py
```

---

## 11. Step-by-step：2-3 周怎么做？

## Phase 0：学习参考项目

时间：1-2 天。

学习目标：

```text
mini-swe-agent：理解最小 agent loop
SWE-agent：理解正式 coding agent 的任务、工具、trajectory、eval
Orchard：理解 Env-first、trajectory、SFT/RL recipe
```

不要一上来直接写训练。

---

## Phase 1：Env-lite + Toy Benchmark

时间：2-3 天。

目标：

```text
先做环境，不做训练。
```

完成内容：

1. 建项目目录。
2. 建 10-30 个 toy code repair tasks。
3. 每个 task 能 pytest fail。
4. 人工修复后 pytest pass。
5. 实现 sandbox reset。
6. 实现 command executor。
7. 实现 test runner。
8. 实现 reward function。

### 任务格式

```text
benchmark/tasks/bugfix_001/
├── repo/
├── tests/
├── issue.md
└── metadata.json
```

### metadata.json 示例

```json
{
  "task_id": "bugfix_001",
  "bug_type": "boundary_condition",
  "language": "python",
  "test_command": "pytest tests/test_auth.py",
  "target_files": ["auth.py"],
  "difficulty": "easy"
}
```

---

## Phase 2：Agent Harness

时间：2-3 天。

目标：

```text
实现 mini-swe-agent 风格的最小 agent loop。
```

第一版工具：

```text
list_files
read_file
search_code
edit_file
run_tests
git_diff
submit_patch
```

Agent loop：

```text
task prompt
→ LLM output
→ action parser
→ tool execution
→ observation
→ history update
→ next step
→ final submit
```

### Action 格式

建议一开始用结构化 JSON：

```json
{
  "thought": "I should run the failing test first.",
  "action": "run_tests",
  "arguments": {
    "cmd": "pytest tests/test_auth.py"
  }
}
```

原因：

1. 后面容易做 SFT。
2. 容易统计 format error。
3. 容易执行工具。
4. 容易构造 DPO / GRPO 数据。

---

## Phase 3：Trajectory Logging

时间：1-2 天。

目标：

```text
所有任务运行过程都必须保存完整轨迹。
```

Trace 示例：

```json
{
  "task_id": "bugfix_001",
  "model": "qwen2.5-coder-7b-instruct",
  "success": true,
  "reward": 1.0,
  "steps": [
    {
      "step": 1,
      "thought": "I should run the failing test first.",
      "action": {
        "name": "run_tests",
        "arguments": {
          "cmd": "pytest tests/test_auth.py"
        }
      },
      "observation": "test_token_expired failed..."
    }
  ],
  "final_patch": "...",
  "test_result": "passed",
  "metrics": {
    "num_steps": 5,
    "tool_valid": true,
    "patch_apply": true,
    "format_errors": 0
  }
}
```

这一步非常重要。  
没有 trace，后面没有 SFT、DPO、RL、自我进化。

---

## Phase 4：Baseline Evaluation

时间：1 天。

目标：

```text
先评测 base model，不要急着训练。
```

评测指标：

```text
Task Success Rate
Test Pass Rate
Tool Call Valid Rate
Patch Apply Rate
Format Error Rate
Avg Steps
Loop Rate
Run-test-before-submit Rate
Unrelated Edit Rate
```

失败分类：

```text
FORMAT_ERROR
NO_TEST_BEFORE_SUBMIT
WRONG_FILE_EDIT
OVER_EDIT
LOOP
GIVE_UP
HALLUCINATED_FILE
PATCH_APPLY_ERROR
TEST_STILL_FAIL
```

---

## Phase 5：SFT 数据构造

时间：2-3 天。

数据来源：

```text
1. 手写高质量轨迹
2. 强模型生成轨迹
3. base model 成功轨迹
4. 失败轨迹中的 productive segment
```

这里要加入 Orchard 的启发：

> 不只成功轨迹有用，失败轨迹中有正向进展的片段也有用。

这就是：

```text
Credit-assignment SFT-lite
```

---

## 12. Credit-assignment SFT-lite

### 12.1 为什么需要它？

普通 SFT 只用成功轨迹：

```text
success trajectory → SFT
```

但现实中，Agent 大部分轨迹可能失败。

如果只用成功轨迹，数据太少。

Orchard-SWE 的启发是：

> 即使最终任务失败，轨迹中也可能有一些 productive steps，例如正确运行测试、正确定位文件、正确读目标函数。

所以我们做简化版：

```text
failed trajectory
→ segment scoring
→ keep productive segments
→ SFT
```

### 12.2 什么是 productive segment？

例如：

```text
Step 1: run_tests ✅
Step 2: read_file(auth.py) ✅
Step 3: identify target function ✅
Step 4: edit wrong condition ❌
Step 5: submit failed ❌
```

虽然最终失败，但前 3 步是有价值的。

可以保留为：

```text
run_tests
→ read_file
→ inspect target function
```

### 12.3 简化评分规则

```python
def score_step(step):
    score = 0
    if step.action == "run_tests":
        score += 1
    if step.action == "read_file" and step.file in target_files:
        score += 1
    if step.action == "search_code" and step.keyword in issue_keywords:
        score += 1
    if step.action == "edit_file" and step.file not in target_files:
        score -= 1
    if step.format_error:
        score -= 1
    return score
```

保留：

```text
连续正分片段
```

过滤：

```text
格式错误
乱改文件
重复无效动作
编造文件
```

### 12.4 简历表达

可以写：

```text
参考 Orchard-SWE 的 credit-assignment SFT 思路，从失败轨迹中抽取具有正向进展的 productive segments，缓解仅依赖成功轨迹导致的数据稀缺问题。
```

---

## 13. DPO 数据构造

DPO 用来让模型偏向好行为。

格式：

```json
{
  "prompt": "Fix bugfix_001.",
  "chosen": "run tests → inspect target file → minimal edit → rerun tests → submit",
  "rejected": "guess directly → edit unrelated file → submit without tests"
}
```

数据来源：

```text
chosen:
- 成功轨迹
- 高质量 productive segment
- 人工修正轨迹

rejected:
- 失败轨迹
- format error 轨迹
- no-test-submit 轨迹
- wrong-file-edit 轨迹
```

DPO 重点改善：

```text
少乱改
少跳过测试
少格式错误
少无效循环
更倾向测试驱动修复
```

---

## 14. GRPO-lite / RL

GRPO 是挑战层，不是项目生死线。

### 14.1 最小 RL 闭环

```text
task
→ model samples multiple rollouts
→ execute in Env-lite
→ compute reward
→ update policy
→ evaluate
```

### 14.2 第一版 reward

```python
def reward_fn(result):
    if result.format_error:
        return -0.3
    if result.tests_passed:
        return 1.0
    if result.patch_apply:
        return 0.2
    if result.tool_valid:
        return 0.1
    return 0.0
```

### 14.3 不要一开始复杂 reward

不要立刻加入太多规则，否则容易 reward hacking。

第一版优先：

```text
test pass
patch apply
tool valid
format error
```

---

## 15. BAR-lite：Balanced Adaptive Rollout 简化版

Orchard 的 Balanced Adaptive Rollout 解决的是：

```text
一个任务如果所有 rollout 都成功，没学习信号；
一个任务如果所有 rollout 都失败，也没学习信号；
最好选择同时有成功和失败的任务组。
```

我们做简化版：

### 15.1 每个任务采样 4 条 rollout

```text
rollout_1
rollout_2
rollout_3
rollout_4
```

### 15.2 分组策略

```text
如果 4 条全成功：
    标记 too_easy，降低训练权重

如果 4 条全失败：
    标记 too_hard，进入 failure analysis 或 DPO rejected pool

如果 1-3 条成功：
    标记 informative，进入 DPO / GRPO 训练池
```

### 15.3 BAR-lite 的意义

它让你不是盲目采样，而是有选择地保留有学习价值的任务。

简历表达：

```text
实现 BAR-lite rollout selection，根据同一任务多条 rollout 的成功/失败分布筛选 informative task group，用于 DPO/GRPO 训练，减少全成功或全失败样本带来的低效训练。
```

---

## 16. Skill Self-Distillation / OPSD-lite

完整 OPSD 不适合 2-3 周个人项目。

我们做：

```text
OPSD-inspired Skill Self-Distillation
```

流程：

```text
成功轨迹
→ 总结 skill
→ 存入 skill memory
→ 相似任务检索 skill
→ teacher-with-skill 生成高质量轨迹
→ student-without-skill 学习轨迹
```

### Skill 示例

```text
Skill: Boundary Condition Repair

When tests fail on equality boundary cases, inspect comparison operators such as <, <=, >, >=.
Make minimal edits and always rerun the failing test before submitting.
```

### 训练样本

Teacher 输入：

```text
task + issue + failing test + retrieved skill + repo context
```

Teacher 输出：

```text
high-quality trajectory
```

Student 输入：

```text
task + issue + failing test + repo context
```

Student 输出：

```text
same high-quality trajectory
```

简历表达：

```text
借鉴 OPSD / Skill Distillation 思路，将成功轨迹总结为 reusable skills，并构造 teacher-with-skill 到 student-without-skill 的自蒸馏数据，使模型逐步内化调试经验。
```

---

## 17. 训练策略：一张 A6000 48G 怎么做？

### 17.1 模型选择

优先：

```text
Qwen2.5-Coder-3B-Instruct
Qwen2.5-Coder-7B-Instruct
DeepSeek-Coder-6.7B-Instruct
```

进阶：

```text
Qwen3-4B / 8B
Qwen3-Coder 小模型
```

不建议第一版：

```text
14B+
32B+
70B
```

### 17.2 训练方式

```text
LoRA / QLoRA
bf16
4bit NF4
gradient checkpointing
short context 2048 / 4096
small batch + gradient accumulation
```

### 17.3 阶段顺序

```text
Base Eval
→ SFT
→ SFT Eval
→ DPO
→ DPO Eval
→ GRPO-lite
→ GRPO Eval
→ Skill-SD
→ Final Eval
```

不要跳过 eval。

---

## 18. 2 周计划

### Day 1：学习 mini-swe-agent + 建任务样例

输出：

```text
mini-swe-agent 阅读笔记
10 个 toy bug task
```

### Day 2：Env-lite

输出：

```text
sandbox.py
command_executor.py
test_runner.py
reward.py
```

### Day 3：Agent Harness

输出：

```text
agent_loop.py
tool_registry.py
action_parser.py
prompt_builder.py
```

### Day 4：Trace Logger + 单任务跑通

输出：

```text
trace_logger.py
能跑 bugfix_001
保存完整 trace
```

### Day 5：扩展 Benchmark

输出：

```text
30-50 个 toy bug task
```

### Day 6：Baseline Eval

输出：

```text
baseline_report.md
failure_taxonomy.json
```

### Day 7：SFT 数据

输出：

```text
sft_data.jsonl
credit_sft_data.jsonl
```

### Day 8：SFT 训练

输出：

```text
LoRA adapter
training log
```

### Day 9：SFT Eval

输出：

```text
base_vs_sft_report.md
```

### Day 10：DPO 数据

输出：

```text
dpo_pairs.jsonl
```

### Day 11：DPO 训练

输出：

```text
DPO adapter
```

### Day 12：DPO Eval

输出：

```text
base_sft_dpo_report.md
```

### Day 13：Skill-SD 原型

输出：

```text
skills.jsonl
skill_sd_data.jsonl
```

### Day 14：整理展示

输出：

```text
README.md
project_report.md
architecture.md
resume_bullets.md
```

---

## 19. 3 周计划：加入 GRPO-lite / BAR-lite

### Day 15：Rollout Group Builder

输出：

```text
rollout_groups.jsonl
```

### Day 16：BAR-lite

输出：

```text
informative_groups.jsonl
too_easy_groups.jsonl
too_hard_groups.jsonl
```

### Day 17：GRPO smoke test

输出：

```text
5 个任务能跑通 rollout + reward + update
```

### Day 18：小规模 GRPO

输出：

```text
30-50 个 easy tasks 上的 GRPO checkpoint
```

### Day 19：GRPO Eval

输出：

```text
sft_dpo_grpo_comparison.md
```

### Day 20：Skill-SD 训练

输出：

```text
skill_sd_adapter
```

### Day 21：最终报告

输出：

```text
final_report.md
demo_script.md
interview_qa.md
```

---

## 20. 最低成功线、中等成功线、高级成功线

### 最低成功线

必须完成：

```text
Env-lite
Agent Harness
Toy CodeRepair Benchmark
Trace Logger
Baseline Eval
SFT Data
LoRA SFT
Base vs SFT Report
```

这已经能写简历。

### 中等成功线

再加：

```text
Credit-SFT-lite
DPO Data
DPO Training
Base vs SFT vs DPO Report
```

这是比较完整的大项目。

### 高级成功线

再加：

```text
BAR-lite
GRPO-lite
Skill Self-Distillation
Final Ablation Report
```

这是高阶项目。

---

## 21. 最终评测表模板

```markdown
| Model | Task Success | Test Pass | Tool Valid | Format Error | Patch Apply | Avg Steps | Loop Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base | - | - | - | - | - | - | - |
| SFT | - | - | - | - | - | - | - |
| SFT + Credit-SFT | - | - | - | - | - | - | - |
| SFT + DPO | - | - | - | - | - | - | - |
| SFT + DPO + GRPO-lite | - | - | - | - | - | - | - |
| Skill-SD | - | - | - | - | - | - | - |
```

不要提前编结果，真实跑出来是多少写多少。

---

## 22. 面试讲解版本

### 22.1 30 秒版本

```text
我做了一个受 Orchard 启发的轻量级 Coding Agent 后训练系统。项目把 Agent 训练拆成 Env-lite、Agent Harness、Trajectory、Data Builder、Training 和 Eval 六层。Agent 能在本地代码修复环境中调用 read_file、edit_file、run_tests 等工具完成 bug 修复，并把每一步交互记录为轨迹。我基于成功轨迹和失败轨迹中的 productive segments 构造 SFT 数据，再用成功/失败轨迹构造 DPO 偏好数据，并尝试用 BAR-lite 筛选有信息量的 rollout 做小规模 GRPO。最后加入 Skill Self-Distillation，把成功调试经验总结为可复用 skill，再蒸馏回模型。
```

### 22.2 详细版本

```text
这个项目的核心不是写一个简单代码助手，而是搭建 Agent 后训练闭环。受 Orchard 的 environment-first 思路启发，我先实现了一个本地 Env-lite，负责 sandbox reset、文件读写、命令执行、pytest 测试、diff 和 reward 计算。然后实现 mini-swe-agent 风格的 Agent Harness，让模型通过结构化 action 调用工具完成代码修复任务。

每次运行都会保存完整 trajectory，包括 thought、action、observation、patch、测试结果和 reward。基于这些轨迹，我构造了三类训练数据：第一类是成功轨迹 SFT；第二类是参考 Orchard-SWE 的 credit-assignment SFT-lite，从失败轨迹中抽取正向片段；第三类是 chosen/rejected DPO pair，用来减少模型乱改文件、不跑测试、工具格式错误等坏行为。

在进阶部分，我实现 BAR-lite，对同一任务采样多条 rollout，筛选有成功也有失败的 informative groups，用于 DPO/GRPO。最后借鉴 OPSD/Skill Distillation，将成功轨迹总结成 reusable skills，并构造 teacher-with-skill 到 student-without-skill 的自蒸馏数据，形成 Agent 自我进化闭环。
```

---

## 23. 简历写法

### 中文版

```text
EvoCode-Orchard-Lite：受 Orchard 启发的 Coding Agent 后训练与自我进化系统

- 设计并实现本地 Env-lite 环境层，支持代码仓库 sandbox reset、文件读写、命令执行、pytest 测试、patch diff 与 reward 计算，解耦 Agent Harness、训练数据构造和评测流程。
- 实现 mini-swe-agent 风格的 Coding Agent Harness，支持 list_files、read_file、search_code、edit_file、run_tests、git_diff 等工具调用，并记录完整 thought-action-observation trajectory。
- 构建 Toy CodeRepair Benchmark，覆盖边界条件、参数错误、类型转换、返回格式错误等常见 bug 类型，并以 test pass、patch apply、tool valid、format error 等指标自动评测。
- 参考 Orchard-SWE 的 credit-assignment SFT 思路，从失败轨迹中抽取 productive segments，结合成功轨迹构造 SFT 数据，并使用 LoRA / QLoRA 对 Qwen-Coder 系列模型进行后训练。
- 构造 chosen/rejected 轨迹对进行 DPO 训练，降低模型乱改文件、跳过测试、工具调用格式错误和无效循环等行为。
- 实现 BAR-lite rollout selection 和小规模 GRPO 实验，根据同一任务多条 rollout 的成功/失败分布筛选 informative groups，用环境 reward 优化 Agent 行为。
- 借鉴 OPSD / Skill Distillation，将成功修复轨迹总结为 reusable skills，并构造 teacher-with-skill 到 student-without-skill 的自蒸馏数据，形成 Agent 自我进化闭环。
```

### 英文版

```text
EvoCode-Orchard-Lite: Orchard-inspired Coding Agent Post-training and Self-evolution Framework

- Built a lightweight local Env-lite layer for code-repair agents, supporting sandbox reset, file I/O, command execution, pytest-based evaluation, patch diff and reward computation.
- Implemented a mini-swe-agent-style coding agent harness with structured tool calls, including list_files, read_file, search_code, edit_file, run_tests and git_diff, while logging full thought-action-observation trajectories.
- Constructed a Toy CodeRepair Benchmark covering boundary-condition bugs, argument mismatch, type errors and return-format bugs, with automatic metrics such as test pass rate, patch applicability and tool-call validity.
- Implemented Orchard-inspired credit-assignment SFT-lite by extracting productive segments from failed trajectories and combining them with successful rollouts for LoRA / QLoRA SFT.
- Built DPO preference pairs from successful and failed trajectories to reduce invalid tool calls, unrelated edits, skipped tests and repetitive loops.
- Designed BAR-lite rollout selection and small-scale GRPO experiments using environment-grounded rewards from test results, patch validity and tool-call correctness.
- Developed an OPSD-inspired Skill Self-Distillation loop that summarizes successful debugging trajectories into reusable skills and distills teacher-with-skill behavior into a student model.
```

---

## 24. 参考资料

### Orchard

- GitHub: https://github.com/microsoft/Orchard
- Paper: https://arxiv.org/abs/2605.15040
- HTML: https://arxiv.org/html/2605.15040v1

### mini-swe-agent

- GitHub: https://github.com/SWE-agent/mini-swe-agent
- Docs: https://mini-swe-agent.com/

### SWE-agent

- Docs: https://swe-agent.com/latest/
- GitHub: https://github.com/SWE-agent/SWE-agent

### Training tools

- TRL: https://huggingface.co/docs/trl/en/index
- PEFT: https://huggingface.co/docs/peft/en/index
- QLoRA: https://arxiv.org/abs/2305.14314

---

## 25. 最终结论

你不应该做一个普通 RAG，也不应该盲目复刻完整 Orchard。

最适合你的项目是：

```text
受 Orchard 启发，
学习 mini-swe-agent / SWE-agent，
自己实现 Env-lite + Agent Harness + Trajectory + Training + Eval 的轻量闭环。
```

2 周最低目标：

```text
Env-lite + Agent Harness + Benchmark + Trace + SFT + Eval
```

3 周高级目标：

```text
Credit-SFT-lite + DPO + BAR-lite + GRPO-lite + Skill-SD
```

这个项目的优势是：

1. 比普通 RAG 更高级。
2. 比纯算法复现更可落地。
3. 能体现 Agent 工程能力。
4. 能体现后训练理解。
5. 能讲清楚失败、评测和迭代。
6. 和 AI Agent 开发 / 大模型应用开发岗位高度相关。

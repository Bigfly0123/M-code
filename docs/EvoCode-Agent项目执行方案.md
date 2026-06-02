# EvoCode-Agent 项目执行方案：面向代码修复任务的 CT / SFT / RL / OPSD-lite 自进化 Agent 后训练系统

> 目标读者：准备做 AI Agent / 大模型应用开发 / Agentic RL 方向项目的个人开发者  
> 适用资源：单卡 A6000 48G，2-3 周内做出可展示版本  
> 推荐定位：70% Agent 工程化 + 30% 后训练算法实验  
> 项目关键词：Coding Agent、Tool Use、Agent Runtime、Trace、SFT、DPO、GRPO、OPSD-lite、Self-Evolving Agent

---

## 0. 一句话总结

这个项目不是再做一个普通 RAG，也不是直接复现大模型算法论文，而是做一个：

> **面向代码修复任务的轻量级 Coding Agent Runtime，并基于 Agent 成功/失败轨迹构造 SFT、DPO、GRPO 和 Skill Self-Distillation 数据，使模型在工具调用、调试流程和代码修复任务上逐步变强。**

更直白地说：

```text
先让 Agent 能跑任务、调用工具、修改代码、运行测试、记录轨迹；
再用这些轨迹做 SFT / DPO / 小规模 GRPO；
最后用成功经验总结 skill，做 OPSD-lite / 自我进化。
```

---

## 1. 为什么选择“代码修复 Agent”作为固定场景？

CT + SFT + RL + Agent 化这类项目必须固定场景。

不要做成：

```text
我训练了一个万能 Agent，什么都能做。
```

这基本不可控，也不好评估。

正确做法是：

```text
我选择一个明确任务环境，让模型通过工具调用完成任务，并且每个任务都有自动 reward。
```

代码修复是非常适合的场景，因为它满足几个关键条件：

| 条件 | 代码修复 Agent 是否满足 | 说明 |
|---|---|---|
| 多步任务 | 满足 | 需要读文件、跑测试、定位 bug、修改代码、再验证 |
| 工具调用 | 满足 | read_file、search_code、edit_file、run_tests、git_diff |
| 自动评测 | 满足 | pytest 是否通过就是天然 reward |
| 数据可构造 | 满足 | 可以自己造 toy repo 和 bug |
| 面试价值 | 高 | 对标 Claude Code、SWE-agent、OpenHands、Devin 类方向 |
| 单卡可做 | 可以 | 用 3B/7B 模型 LoRA / QLoRA 即可 |

---

## 2. 项目定位

### 2.1 对外定位

项目名称建议：

```text
EvoCode-Agent：面向代码修复任务的自进化 Agent 后训练系统
```

英文简历名称可以是：

```text
EvoCode-Agent: A Self-Evolving Coding Agent with SFT, Preference Optimization and RL-based Tool Use
```

### 2.2 项目不是做什么

这个项目不是：

- 不是普通 ChatBot
- 不是普通 RAG
- 不是只接 API 的 Agent Demo
- 不是纯论文复现
- 不是大规模预训练
- 不是一定要训练出 SOTA 的 RL 模型

### 2.3 项目真正做什么

这个项目做的是：

1. 自研轻量级 Coding Agent Runtime
2. 构造可自动评测的代码修复任务集
3. 记录 Agent 工具调用轨迹
4. 构造 SFT 训练数据
5. 构造 DPO chosen / rejected 轨迹
6. 小规模尝试 GRPO / RL
7. 借鉴 OPSD / Skill Distillation 思路做自我进化
8. 通过评测指标证明每个阶段的变化

---

## 3. 2-3 周内的现实目标

### 3.1 必成版目标

2-3 周内必须优先完成：

```text
Agent Runtime
+ Toy Code Repair Benchmark
+ Trace Logger
+ Baseline Evaluation
+ SFT Data Builder
+ LoRA SFT
+ Base vs SFT Evaluation Report
```

这已经足够作为一个完整项目的核心版本。

### 3.2 进阶版目标

如果时间允许，再做：

```text
DPO Preference Data
+ DPO Training
+ Base vs SFT vs DPO Evaluation
```

### 3.3 挑战版目标

最后再考虑：

```text
Small-scale GRPO
+ Skill Memory
+ OPSD-lite / Skill Self-Distillation
```

### 3.4 不要把项目成败押在 GRPO 上

训练出效果最稳的是 SFT。

训练效果稳定性大致如下：

| 阶段 | 出效果概率 | 主要效果 |
|---|---:|---|
| SFT | 高 | 工具调用格式更稳定、流程更规范 |
| DPO | 中高 | 减少坏行为，例如乱改文件、不跑测试 |
| GRPO | 中低 | 可能提升成功率，但不稳定 |
| OPSD-lite | 中 | 可以作为 skill memory + 蒸馏闭环展示 |

---

## 4. 你应该借鉴哪些项目？

### 4.1 mini-swe-agent

参考价值：极简 Agent Loop。

适合学习：

- 最小 Coding Agent 怎么跑
- 如何让模型通过 shell / command 完成任务
- 如何把 observation 回传给模型
- 如何保持项目轻量

官方仓库：  
https://github.com/SWE-agent/mini-swe-agent

### 4.2 SWE-agent

参考价值：标准代码修复 Agent。

适合学习：

- GitHub issue 到 patch 的流程
- 工具接口设计
- trajectory 记录
- benchmark / eval 思路
- 配置化 Agent 运行方式

官方文档：  
https://swe-agent.com/latest/

官方组织：  
https://github.com/SWE-agent

### 4.3 OpenHands

参考价值：完整软件开发 Agent 平台。

适合学习：

- sandbox
- workspace
- 文件编辑工具
- 长任务管理
- 多工具协作
- 工程化架构

官网：  
https://www.openhands.dev/

GitHub：  
https://github.com/OpenHands/OpenHands

注意：OpenHands 太大，不建议直接复刻。你应该只借鉴架构思想。

### 4.4 Hugging Face TRL

参考价值：训练工具。

适合用于：

- SFTTrainer
- DPOTrainer
- GRPOTrainer
- reward function
- post-training pipeline

官方文档：  
https://huggingface.co/docs/trl/en/index

SFT 文档：  
https://huggingface.co/docs/trl/en/sft_trainer

DPO 文档：  
https://huggingface.co/docs/trl/en/dpo_trainer

GRPO 文档：  
https://huggingface.co/docs/trl/en/grpo_trainer

### 4.5 PEFT / LoRA / QLoRA

单卡 A6000 48G 不建议全参训练。

推荐使用：

- LoRA
- QLoRA
- bf16
- gradient checkpointing
- 短上下文起步

PEFT 文档：  
https://huggingface.co/docs/peft/en/index

LoRA 文档：  
https://huggingface.co/docs/peft/package_reference/lora

QLoRA 论文：  
https://arxiv.org/abs/2305.14314

---

## 5. 推荐模型选择

### 5.1 第一阶段推荐模型

优先选择：

```text
Qwen2.5-Coder-3B-Instruct
Qwen2.5-Coder-7B-Instruct
DeepSeek-Coder-6.7B-Instruct
Qwen2.5-7B-Instruct
```

### 5.2 为什么不要一开始上 14B / 32B？

原因：

1. 训练慢
2. debug 慢
3. RL rollout 慢
4. 显存压力更大
5. 2-3 周内迭代成本太高

建议路线：

```text
第一版：3B 或 7B
稳定后：7B
挑战版：14B QLoRA
不要一开始碰 32B+
```

### 5.3 A6000 48G 建议配置

| 项目 | 建议 |
|---|---|
| 训练方式 | LoRA / QLoRA |
| 精度 | bf16 或 4bit NF4 |
| context length | 2048 / 4096 起步 |
| batch size | 小 batch + gradient accumulation |
| optimizer | paged_adamw_8bit / adamw_torch |
| 训练阶段 | 先 SFT，再 DPO，最后 GRPO |
| 是否 vLLM | 第一版可以不用；GRPO 慢时再考虑 |

---

## 6. 总体架构

### 6.1 系统流程

```text
Bug Task
  ↓
Agent Runtime
  ↓
Tool Calling Loop
  ↓
Repository Sandbox
  ↓
Run Tests / Get Reward
  ↓
Trace Logger
  ↓
Trajectory Dataset
  ↓
SFT / DPO / GRPO / Skill-SD
  ↓
New Agent Policy
  ↓
Evaluation
```

### 6.2 Agent Loop

最小 Agent Loop：

```text
1. 读取任务描述
2. 观察 repo 信息
3. 选择工具
4. 执行工具
5. 获取 observation
6. 根据 observation 再决策
7. 修改代码
8. 运行测试
9. 成功则 submit
10. 失败则继续调试或停止
```

### 6.3 工具列表

第一版只需要以下工具：

| 工具 | 功能 |
|---|---|
| list_files | 查看项目文件结构 |
| read_file | 读取文件内容 |
| search_code | 搜索关键词 |
| edit_file | 修改文件 |
| run_tests | 运行 pytest |
| git_diff | 查看修改 diff |
| submit_patch | 提交最终 patch |

不要一开始加太多工具。工具越多，训练和评测越难。

---

## 7. 推荐项目目录结构

```text
evocode-agent/
├── README.md
├── requirements.txt
├── configs/
│   ├── agent.yaml
│   ├── model.yaml
│   └── train.yaml
│
├── runtime/
│   ├── agent_loop.py
│   ├── tool_registry.py
│   ├── prompt_builder.py
│   ├── action_parser.py
│   ├── sandbox.py
│   └── trace_logger.py
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
├── envs/
│   ├── code_repair_env.py
│   ├── task_loader.py
│   ├── reward.py
│   └── reset_repo.py
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
├── data_builder/
│   ├── build_sft.py
│   ├── build_dpo.py
│   ├── build_grpo_rollouts.py
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
├── traces/
│   ├── raw/
│   ├── success/
│   └── failed/
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

## 8. 数据格式设计

### 8.1 任务格式

每个任务一个目录：

```text
benchmark/tasks/bugfix_001/
├── repo/
├── tests/
├── issue.md
└── metadata.json
```

`issue.md` 示例：

```markdown
# Bug Report

The function `is_expired(token_time, now)` returns False when token_time equals now, but it should be treated as expired.

Run:

```bash
pytest tests/test_auth.py
```

Expected:

All tests should pass.
```

`metadata.json` 示例：

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

### 8.2 Trace 格式

每次 Agent 运行后保存完整轨迹：

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
    },
    {
      "step": 2,
      "thought": "The error is related to token expiration. I need to inspect auth.py.",
      "action": {
        "name": "read_file",
        "arguments": {
          "path": "auth.py"
        }
      },
      "observation": "def is_expired(token_time, now): return token_time < now"
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

### 8.3 SFT 数据格式

可以转成 ShareGPT / ChatML 风格：

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a coding agent. You can use tools to inspect and edit a repository."
    },
    {
      "role": "user",
      "content": "Fix the bug described in issue.md. You may use tools."
    },
    {
      "role": "assistant",
      "content": "Thought: I should run the failing test first.\nAction: run_tests({\"cmd\": \"pytest tests/test_auth.py\"})"
    },
    {
      "role": "tool",
      "content": "test_token_expired failed..."
    },
    {
      "role": "assistant",
      "content": "Thought: The bug is likely in auth.py.\nAction: read_file({\"path\": \"auth.py\"})"
    }
  ]
}
```

### 8.4 DPO 数据格式

```json
{
  "prompt": "Fix bugfix_001. You can use tools.",
  "chosen": "Thought: Run tests first...\nAction: run_tests(...)\nObservation: ...\nAction: read_file(...)\nAction: edit_file(...)\nAction: run_tests(...)\nFinal: fixed.",
  "rejected": "Thought: I know the issue.\nAction: edit_file(random_file.py)\nFinal: fixed."
}
```

### 8.5 GRPO Rollout 数据

GRPO 不一定需要提前固定完整数据集，但你需要保存每次 rollout：

```json
{
  "task_id": "bugfix_001",
  "rollouts": [
    {
      "completion": "...",
      "reward": 1.0,
      "success": true
    },
    {
      "completion": "...",
      "reward": 0.0,
      "success": false
    },
    {
      "completion": "...",
      "reward": -0.2,
      "success": false
    }
  ]
}
```

---

## 9. Reward 设计

### 9.1 第一版 reward

不要复杂。第一版只做 outcome reward：

```python
def compute_reward(result):
    if result.tool_format_error:
        return -0.3
    if result.timeout_or_max_steps:
        return -0.2
    if result.patch_apply_error:
        return -0.1
    if result.tests_passed:
        return 1.0
    return 0.0
```

### 9.2 第二版 reward

加入过程奖励：

```python
reward = 0.0

if tests_passed:
    reward += 1.0

if patch_apply:
    reward += 0.2

if tool_call_valid:
    reward += 0.1

if ran_tests_before_submit:
    reward += 0.1

if edited_unrelated_files:
    reward -= 0.2

if repeated_same_action:
    reward -= 0.1

if format_error:
    reward -= 0.3

if max_steps_exceeded:
    reward -= 0.2
```

### 9.3 不要过度 reward shaping

一开始不要设计太多细节，否则模型可能学会钻空子。

例如：

- 为了拿 run_tests 奖励，反复运行测试
- 为了少步骤，跳过必要检查
- 为了 patch apply，做无意义小修改

所以第一版建议：

```text
测试通过 > patch 可应用 > 工具格式合法 > 步数控制
```

---

## 10. 评测指标

必须做指标，否则项目很难讲清楚。

### 10.1 核心指标

| 指标 | 含义 |
|---|---|
| Task Success Rate | 任务完成率 |
| Test Pass Rate | 测试通过率 |
| Tool Call Valid Rate | 工具调用合法率 |
| Patch Apply Rate | patch 可应用率 |
| Format Error Rate | JSON / action 格式错误率 |
| Avg Steps | 平均步数 |
| Avg Tool Calls | 平均工具调用次数 |
| Loop Rate | 重复无效操作比例 |
| Run-test-before-submit Rate | 提交前是否运行测试 |
| Unrelated Edit Rate | 修改无关文件比例 |

### 10.2 推荐评测表

最终报告至少要有：

| Model | Task Success | Tool Valid | Format Error | Avg Steps | Test Pass |
|---|---:|---:|---:|---:|---:|
| Base | - | - | - | - | - |
| SFT | - | - | - | - | - |
| SFT + DPO | - | - | - | - | - |
| SFT + GRPO | - | - | - | - | - |
| SFT + GRPO + Skill-SD | - | - | - | - | - |

不要提前编数字。真实跑出来是多少就写多少。

---

## 11. 从 0 到 Start：具体执行步骤

## Step 1：初始化项目

```bash
mkdir evocode-agent
cd evocode-agent

mkdir runtime tools envs benchmark data_builder training eval traces outputs configs dashboard
touch README.md requirements.txt
```

`requirements.txt` 第一版：

```text
torch
transformers
datasets
accelerate
peft
trl
bitsandbytes
pytest
pyyaml
rich
typer
pydantic
gitpython
streamlit
pandas
matplotlib
```

---

## Step 2：先做 Toy Benchmark

不要先写 Agent。先做 10 个最简单 bug。

示例 bug 类型：

```text
1. 边界条件错误：< 应该改成 <=
2. 参数顺序错误：add(a,b) 调用反了
3. dict key 拼写错误
4. list index off-by-one
5. 类型转换错误：str/int
6. 日期比较错误
7. regex pattern 错误
8. None 判断错误
9. 默认参数错误
10. 返回格式错误
```

每个任务都要有：

```text
repo/
tests/
issue.md
metadata.json
```

完成标准：

```bash
pytest benchmark/tasks/bugfix_001/repo/tests
```

能稳定失败，修复后能稳定通过。

---

## Step 3：实现工具

先实现最小工具。

### list_files

输入：repo_path  
输出：文件树

### read_file

输入：path  
输出：文件内容

### search_code

输入：keyword  
输出：命中文件和行号

### edit_file

第一版不要做复杂 patch，可以先做：

```json
{
  "path": "auth.py",
  "old": "return token_time < now",
  "new": "return token_time <= now"
}
```

### run_tests

输入：cmd  
输出：stdout、stderr、returncode

### git_diff

输出当前修改 diff。

### submit_patch

最终提交。

---

## Step 4：实现 Agent Loop

第一版可以用 API 模型作为 planner，不要急着本地模型。

伪代码：

```python
for step in range(max_steps):
    prompt = build_prompt(task, history, tools)
    response = llm.generate(prompt)
    action = parse_action(response)

    if action.name == "submit_patch":
        break

    observation = tool_registry.execute(action)
    trace_logger.append(step, response, action, observation)

result = run_tests()
reward = compute_reward(result)
save_trace()
```

### 第一版 action 格式

建议用 JSON：

```json
{
  "thought": "I need to run the failing test first.",
  "action": "run_tests",
  "arguments": {
    "cmd": "pytest tests/test_auth.py"
  }
}
```

这样后面容易做 SFT。

---

## Step 5：跑 Baseline

用同一个任务集，跑 base model。

记录结果：

```text
任务 1：失败，原因：没有运行测试，直接乱改
任务 2：失败，原因：工具 JSON 格式错误
任务 3：成功
...
```

生成 `outputs/reports/baseline_report.md`。

### Baseline 目标

不是为了高成功率，而是为了发现失败模式。

常见失败模式：

| 失败类型 | 说明 |
|---|---|
| FORMAT_ERROR | 工具调用格式错误 |
| NO_TEST_BEFORE_SUBMIT | 没跑测试就提交 |
| WRONG_FILE_EDIT | 修改错误文件 |
| OVER_EDIT | 改动过大 |
| LOOP | 重复读同一个文件或重复跑测试 |
| GIVE_UP | 过早放弃 |
| HALLUCINATED_FILE | 编造不存在文件 |
| PATCH_APPLY_ERROR | patch 无法应用 |

---

## Step 6：构造 SFT 数据

### 数据来源

优先顺序：

1. 自己写 20-30 条高质量轨迹
2. 用强模型生成 100-300 条轨迹
3. 从 baseline 成功轨迹中筛选
4. 对失败轨迹人工修正

### SFT 目标

SFT 不要求直接提升所有任务成功率。

第一目标是：

```text
让模型学会标准工具调用格式和标准调试流程。
```

标准流程：

```text
读 issue
→ 运行失败测试
→ 根据报错定位文件
→ 阅读目标文件
→ 小范围修改
→ 再运行测试
→ 查看 diff
→ submit
```

### SFT 数据质量标准

保留：

- 工具调用合法
- 步骤清晰
- observation 对得上
- 修改范围小
- 最后测试通过

过滤：

- 编造文件
- observation 和 action 对不上
- 乱改多个文件
- 没测试
- 失败但伪装成功

---

## Step 7：LoRA SFT

建议第一版配置：

```yaml
model_name: Qwen/Qwen2.5-Coder-7B-Instruct
method: lora
load_in_4bit: true
max_seq_length: 4096
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
batch_size: 1
gradient_accumulation_steps: 8
learning_rate: 2e-4
num_train_epochs: 2
bf16: true
gradient_checkpointing: true
```

训练完成后评测：

```text
Base vs SFT
```

重点看：

- Tool Call Valid Rate 是否提升
- Format Error Rate 是否下降
- Run-test-before-submit Rate 是否提升
- Avg invalid steps 是否下降

如果 task success 没明显涨，也不要慌。SFT 先改善行为格式就算有效。

---

## Step 8：构造 DPO 数据

DPO 数据来自：

```text
chosen = 成功轨迹 / 高质量轨迹
rejected = 失败轨迹 / 低质量轨迹
```

同一任务最好有对比：

```text
chosen：先跑测试 → 定位 → 小改 → 再测 → 成功
rejected：直接猜 → 改错文件 → 不测 → 失败
```

DPO 重点优化：

- 少乱改文件
- 少跳过测试
- 少重复无效动作
- 少格式错误
- 更偏向测试驱动修复

建议数据量：

```text
第一版：100-300 对
进阶版：500-1000 对
```

---

## Step 9：DPO 训练

建议第一版只在 SFT 模型基础上做 DPO。

```text
Base → SFT → DPO
```

不要直接：

```text
Base → DPO
```

评测表：

```text
Base vs SFT vs DPO
```

如果 DPO 只提升了坏行为减少，也算成功。

---

## Step 10：GRPO / RL 小规模实验

这一阶段是挑战层。

不要上来就做全量。

第一版只选：

```text
50 个 easy 任务
每个任务采样 2-4 条 rollout
max_steps 控制在 8-12
reward 简单
```

GRPO 的目标不是必须大涨，而是证明你跑通：

```text
online rollout
→ execute tools
→ compute reward
→ update policy
→ evaluate
```

### GRPO 最小 reward

```python
def reward_fn(completion, task_result):
    if task_result.format_error:
        return -0.3
    if task_result.tests_passed:
        return 1.0
    if task_result.patch_apply:
        return 0.2
    return 0.0
```

### 注意事项

GRPO 可能不稳定。

如果出现以下情况，不代表项目失败：

- reward 大部分是 0
- 成功率波动
- 模型只学会格式，修复能力提升不明显
- rollout 很慢

你可以在报告里写清楚：

```text
由于长时代码修复任务 reward 稀疏，纯 outcome reward 的 GRPO 提升有限，因此后续引入 process reward 和 skill self-distillation。
```

这样反而显得你真的做过实验。

---

## Step 11：OPSD-lite / Skill Self-Distillation

不要一开始复现论文级 OPSD。

做工程版即可：

```text
成功轨迹
→ 总结 skill
→ 存入 skill memory
→ 相似任务检索 skill
→ teacher-with-skill 生成高质量轨迹
→ student-without-skill 学习该轨迹
```

### Skill 示例

```text
Skill: Boundary Condition Repair

When a test fails on equality boundary cases, first inspect comparison operators such as <, <=, >, >=.
Prefer minimal edits and always run the specific failing test before submitting.
```

### Skill 数据格式

```json
{
  "skill_id": "boundary_condition_repair",
  "source_task": "bugfix_001",
  "skill": "When equality boundary tests fail, inspect comparison operators such as <, <=, >, >=.",
  "failure_pattern": "The model changed unrelated validation logic instead of checking the comparison operator.",
  "recommended_actions": [
    "run failing test",
    "read target file",
    "inspect comparison operator",
    "make minimal edit",
    "run test again"
  ]
}
```

### OPSD-lite 训练样本

Teacher 输入：

```text
task + issue + failing test + retrieved skill + repository context
```

Teacher 输出：

```text
high-quality trajectory
```

Student 输入：

```text
task + issue + failing test + repository context
```

Student 输出：

```text
same high-quality trajectory
```

这就是：

```text
privileged teacher → normal student
```

你可以把它称为：

```text
Skill-based Self-Distillation inspired by OPSD
```

不要过度宣称“完整复现 OPSD”。

---

# 12. 2 周执行计划

如果只有 2 周，按这个做。

## Week 1：工程闭环

### Day 1

目标：项目初始化 + 10 个 toy bug。

完成：

- 建 repo
- 建目录
- 写 10 个 bugfix task
- 每个 task 能 pytest fail
- 人工修复后 pytest pass

### Day 2

目标：工具系统。

完成：

- list_files
- read_file
- search_code
- edit_file
- run_tests
- git_diff
- submit_patch

### Day 3

目标：Agent Loop。

完成：

- tool registry
- prompt builder
- action parser
- trace logger
- 能跑单个任务

### Day 4

目标：批量评测。

完成：

- run_eval.py
- reward.py
- metrics.py
- 跑 10 个任务
- 输出 baseline report

### Day 5

目标：扩展任务集。

完成：

- 任务扩到 30-50 个
- failure taxonomy
- trace 保存规范化

### Day 6

目标：SFT 数据构造。

完成：

- build_sft.py
- 20 条手写高质量轨迹
- 50-100 条强模型生成轨迹
- 数据过滤脚本

### Day 7

目标：SFT 训练准备。

完成：

- train_sft.py
- LoRA 配置
- 小数据 smoke test
- 能成功跑一个 epoch

---

## Week 2：训练和报告

### Day 8

目标：正式 SFT。

完成：

- Qwen2.5-Coder-3B/7B LoRA SFT
- 保存 adapter
- 记录训练日志

### Day 9

目标：Base vs SFT 评测。

完成：

- 跑全任务集
- 统计指标
- 对比工具调用合法率、格式错误率、测试通过率

### Day 10

目标：DPO 数据。

完成：

- build_dpo.py
- chosen/rejected pairs 100-300 对
- 失败轨迹分类

### Day 11

目标：DPO 训练。

完成：

- train_dpo.py
- SFT checkpoint → DPO
- 小规模训练

### Day 12

目标：Base vs SFT vs DPO 评测。

完成：

- 三模型对比
- failure analysis
- 可视化表格

### Day 13

目标：Skill Memory / OPSD-lite 原型。

完成：

- build_skills.py
- 成功轨迹总结 skill
- skill 检索
- teacher-with-skill 样本构造

### Day 14

目标：整理项目展示。

完成：

- README
- 技术报告
- 架构图
- 指标表
- 失败案例分析
- 简历项目描述

2 周版不强求 GRPO。可以把 GRPO 写成进行中或扩展实验。

---

# 13. 3 周执行计划

如果有 3 周，第 3 周做 GRPO 和更完整 OPSD-lite。

## Week 3：RL 和自我进化

### Day 15

目标：GRPO 环境准备。

完成：

- build_grpo_rollouts.py
- 选择 30-50 个 easy task
- 限制 max_steps
- 简单 reward

### Day 16

目标：GRPO smoke test。

完成：

- 2-5 个任务跑通 rollout
- reward 能正确返回
- trainer 能 update

### Day 17

目标：小规模 GRPO。

完成：

- 30-50 个任务
- 每个任务 2-4 条 rollout
- 训练一个小 checkpoint

### Day 18

目标：GRPO 评测。

完成：

- SFT vs SFT+DPO vs SFT+GRPO
- 分析 reward 稀疏问题
- 记录失败案例

### Day 19

目标：Skill Self-Distillation。

完成：

- skill-conditioned teacher 样本
- student-without-skill 样本
- train_skill_sd.py

### Day 20

目标：最终评测。

完成：

- Base
- SFT
- SFT+DPO
- SFT+GRPO
- SFT+Skill-SD

至少跑 30-50 个任务。

### Day 21

目标：最终报告和简历包装。

完成：

- 项目 README
- 技术文档
- 训练报告
- demo 视频脚本
- 简历 bullet
- 面试讲解稿

---

## 14. 最小可交付版本验收标准

只要满足下面条件，项目就可以写进简历：

```text
1. 有一个可运行的 Coding Agent Runtime
2. 有 30-50 个可自动评测的代码修复任务
3. 有完整 trace logger
4. 有 baseline 评测
5. 有 SFT 数据构造流程
6. 有 LoRA SFT 模型
7. 有 Base vs SFT 对比报告
8. 有失败案例分析
9. 有清晰 README 和架构图
```

中等完成度：

```text
在上面基础上加入 DPO 数据和 DPO 训练。
```

高级完成度：

```text
加入 GRPO 小实验和 OPSD-lite / Skill Self-Distillation。
```

---

## 15. 风险与兜底方案

| 风险 | 表现 | 兜底方案 |
|---|---|---|
| 任务太难 | base 和 SFT 都做不出来 | 降低任务难度，先做 toy bug |
| SFT 没提升成功率 | task success 不涨 | 看 tool valid、format error、流程规范是否提升 |
| DPO 无明显效果 | 指标波动 | 增加 chosen/rejected 质量，减少噪声 |
| GRPO 太慢 | rollout 时间过长 | 只做 30-50 个 easy task，小模型，小 max_steps |
| reward 稀疏 | 大部分 reward 为 0 | 加 process reward，例如 patch_apply、tool_valid |
| 模型乱改文件 | unrelated edit 高 | DPO 加 rejected 样本，reward 惩罚 |
| 工具调用格式错 | JSON parse 失败 | SFT 加格式样本，action parser 做容错 |
| A6000 显存不够 | OOM | 用 3B、4bit QLoRA、短上下文、gradient checkpointing |
| 2 周时间不够 | 做不完 RL | 保证 SFT + Eval 完成，RL 写成扩展实验 |

---

## 16. 面试讲解逻辑

### 16.1 30 秒版本

```text
我做了一个面向代码修复任务的自进化 Coding Agent。系统包含轻量 Agent Runtime、工具调用、repo sandbox、测试反馈、轨迹记录和自动评测。我先构造了一个小型代码修复 benchmark，用 base model 跑出成功/失败轨迹，再基于这些轨迹构造 SFT 和 DPO 数据，优化模型的工具调用格式、调试流程和测试驱动修复行为。进阶部分尝试用 GRPO 进行小规模在线优化，并借鉴 OPSD / Skill Distillation，把成功轨迹总结为 reusable skills，再蒸馏回模型。
```

### 16.2 详细版本

```text
项目的核心不是接一个 LLM API，而是完整搭建了 Agent 后训练闭环。

第一层是 Agent Runtime：模型可以通过 list_files、read_file、search_code、edit_file、run_tests、git_diff 等工具与代码仓库交互。每一步工具调用都会被记录成 trajectory，并且系统会根据 pytest 是否通过、patch 是否可应用、工具调用是否合法等指标自动打分。

第二层是训练数据闭环：我把成功轨迹转成 SFT 数据，让模型学习标准的测试驱动调试流程；把成功和失败轨迹构造成 DPO preference pair，让模型减少乱改文件、不跑测试、格式错误等坏行为。

第三层是 Agentic RL / 自我进化实验：我在小规模 easy task 上尝试 GRPO，用测试通过率和工具合法性作为 reward。同时借鉴 OPSD / Skill-SD 思路，把成功轨迹总结成 reusable skill，构造 teacher-with-skill 到 student-without-skill 的自蒸馏数据，让模型逐步内化修复经验。
```

---

## 17. 简历写法

### 中文简历版本

```text
EvoCode-Agent：面向代码修复任务的自进化 Agent 后训练系统

- 设计并实现轻量级 Coding Agent Runtime，支持 read_file、search_code、edit_file、run_tests、git_diff 等工具调用，并通过 sandbox 执行代码修复任务。
- 构建小型 CodeRepair Benchmark，覆盖边界条件、类型转换、参数错误、返回格式错误等常见 bug 类型，并以 pytest 结果、patch 可应用性和工具调用合法性作为自动评测指标。
- 基于 Agent 成功/失败轨迹构造 SFT 与 DPO 数据，使用 LoRA / QLoRA 对 Qwen2.5-Coder 进行后训练，优化模型工具调用格式、测试驱动调试流程和无效操作比例。
- 尝试小规模 GRPO Agentic RL，以测试通过率、patch apply、tool valid 等信号构造 reward，并分析长时任务 reward 稀疏与 rollout 成本问题。
- 借鉴 OPSD / Skill Distillation 思路，将成功修复轨迹抽象为 reusable skills，构建 teacher-with-skill 到 student-without-skill 的自蒸馏数据，用于 Agent 自我进化闭环。
```

### 英文简历版本

```text
EvoCode-Agent: Self-Evolving Coding Agent with SFT, Preference Optimization and RL-based Tool Use

- Built a lightweight coding agent runtime with tool calling, repository sandbox, test execution, patch generation, trajectory logging and automatic evaluation.
- Constructed a toy CodeRepair benchmark covering boundary-condition bugs, type errors, argument mismatch, return-format errors and simple algorithmic bugs, using pytest results and patch validity as reward signals.
- Converted successful and failed agent trajectories into SFT and DPO datasets, and fine-tuned Qwen2.5-Coder with LoRA / QLoRA to improve tool-call validity, test-driven debugging behavior and invalid-action rate.
- Implemented a small-scale GRPO experiment with reward signals from test pass rate, patch applicability and tool-call validity, and analyzed sparse reward issues in long-horizon coding tasks.
- Designed an OPSD-inspired Skill Self-Distillation loop that summarizes successful trajectories into reusable skills and distills teacher-with-skill behavior into a student model without explicit skill prompts.
```

---

## 18. README 推荐结构

```markdown
# EvoCode-Agent

## Overview

## Motivation

## System Architecture

## Agent Runtime

## Tools

## CodeRepair Benchmark

## Training Pipeline
- SFT
- DPO
- GRPO
- Skill Self-Distillation

## Evaluation

## Results

## Failure Analysis

## How to Run

## Roadmap
```

---

## 19. 最终展示材料

项目结束时建议准备：

```text
1. GitHub README
2. 技术报告 report.md
3. 架构图 architecture.png
4. 训练流程图 training_pipeline.png
5. 指标对比表 results.csv
6. 失败案例分析 failure_analysis.md
7. 3-5 分钟 demo 视频
8. 简历 bullet
9. 面试讲解稿
```

---

## 20. 关键提醒

### 20.1 不要一开始就做 RL

顺序一定是：

```text
Agent 环境 → 任务集 → Baseline → SFT → DPO → GRPO → OPSD-lite
```

### 20.2 不要一开始用真实大型 repo

先 toy task。

SWE-bench 可以后面作为扩展，不要作为第一阶段目标。

### 20.3 不要只看 task success

SFT 早期可能不明显提升成功率，但只要下面指标改善，也算有效：

```text
tool call valid rate
format error rate
run-test-before-submit rate
avg invalid steps
unrelated edit rate
```

### 20.4 不要夸大 OPSD

建议写：

```text
OPSD-inspired Skill Self-Distillation
```

不要写：

```text
完整复现 OPSD 并大幅提升模型能力
```

### 20.5 项目核心价值是闭环

最终你要讲清楚：

```text
任务环境
→ Agent 运行
→ 轨迹收集
→ 数据构造
→ 后训练
→ 评测
→ 失败归因
→ skill 总结
→ 再训练
```

这个闭环就是项目高级感的来源。

---

## 21. 最终结论

2-3 周内，最现实且最有价值的目标不是做一个“完美的 CT + SFT + RL + OPSD 全量系统”，而是做出一个：

```text
可运行的 Coding Agent
+ 可自动评测的代码修复任务集
+ 可复现的轨迹数据
+ SFT / DPO 后训练闭环
+ 小规模 GRPO / OPSD-lite 扩展实验
```

你的最低成功线应该是：

```text
Agent Runtime + Benchmark + Trace + SFT + Eval
```

你的高级加分线是：

```text
DPO + GRPO + Skill Self-Distillation
```

如果执行得好，这个项目可以同时覆盖：

- AI Agent 开发
- 大模型应用工程
- Tool Use
- Agent Runtime
- LLM 后训练
- SFT / DPO / RL
- Agent 自我进化

这比普通 RAG 项目更有区分度，也更适合你当前想冲的岗位方向。

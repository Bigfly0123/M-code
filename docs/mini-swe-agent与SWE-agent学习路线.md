# mini-swe-agent 与 SWE-agent 学习路线：如何从零读懂并迁移到 EvoCode-Orchard-Lite 项目

> 目标：不是“看一遍源码”，而是通过 mini-swe-agent 和 SWE-agent 学会 Coding Agent 的核心框架、任务组织、工具调用、轨迹记录和评测思路，并迁移到自己的 EvoCode-Orchard-Lite 项目中。  
> 时间建议：2-4 天完成第一轮学习。  
> 学习原则：先跑通，再读代码；先读 mini，再读 SWE-agent；先理解 loop，再理解工程化；不要一上来魔改大项目。

---

## 0. 为什么要学习这两个项目？

我们的项目目标是：

```text
EvoCode-Orchard-Lite:
Env-lite + Coding Agent Harness + Trajectory + SFT/DPO/GRPO + Skill-SD
```

其中 Agent Harness 部分可以从 mini-swe-agent 和 SWE-agent 学。

两者关系：

| 项目 | 你应该怎么用 |
|---|---|
| mini-swe-agent | 学最小 coding agent loop，适合第一天读懂和复刻 |
| SWE-agent | 学正式 coding agent 的工程组织、工具接口、trajectory、benchmark/eval |
| OpenHands | 暂时只看架构，不建议第一阶段深入 |
| Orchard | 学 Env-first、trajectory、SFT/RL recipe，不直接复刻 |

---

## 1. 先说结论：不要直接 fork 大项目魔改

你不是要做：

```text
fork SWE-agent
改几个配置
接一个模型
跑几个 demo
```

这样简历含金量不够，而且面试时容易被问倒。

更好的路线是：

```text
1. 跑通 mini-swe-agent
2. 读懂它的最小 loop
3. 自己复刻一个结构化 tool loop
4. 再读 SWE-agent 学工程设计
5. 把学到的东西迁移到自己的 evocode-orchard-lite
```

也就是：

```text
学习开源框架，但不依赖开源框架；
借鉴设计，但核心闭环自己实现。
```

---

## 2. 学习总路线

建议顺序：

```text
Day 1:
mini-swe-agent 跑通 + 核心 loop 阅读 + 画流程图

Day 2:
自己复刻 mini loop + 加结构化工具 + 加 trace logger

Day 3:
阅读 SWE-agent 文档和核心模块 + 总结工程设计

Day 4:
把 SWE-agent 的任务组织、trajectory、eval 思路迁移到 EvoCode-Orchard-Lite
```

---

## 3. mini-swe-agent 学习目标

mini-swe-agent 的价值是：

```text
用最少代码展示一个 coding agent 的本质。
```

你要从它学到：

1. Agent loop 是什么。
2. LLM 输出如何变成 action。
3. action 如何在环境中执行。
4. observation 如何反馈给 LLM。
5. 多轮历史如何维护。
6. 什么时候停止。
7. 如何控制 max step。
8. 为什么极简 loop 也能完成代码任务。
9. 它的缺点是什么。
10. 我们要如何改造成后训练友好的版本。

---

## 4. mini-swe-agent 第一轮：先跑通

### 4.1 克隆项目

```bash
git clone https://github.com/SWE-agent/mini-swe-agent.git
cd mini-swe-agent
```

### 4.2 安装依赖

按照官方 README / docs 安装即可。

通常你需要准备：

```text
Python 环境
模型 API key 或本地模型配置
LiteLLM 配置
```

mini-swe-agent 重点是简单，不要一开始改源码。

### 4.3 跑一个最小任务

目标不是解决真实 GitHub issue，而是看懂它怎么执行。

你可以先用一个很小的本地 repo，让它完成简单任务，例如：

```text
修复一个 failing pytest
```

观察：

```text
它如何读文件？
它如何运行命令？
它如何修改代码？
它如何看到测试失败？
它如何决定下一步？
它如何停止？
```

---

## 5. mini-swe-agent 第二轮：带着问题读源码

你读源码时不要从头看到尾，而是带着问题读。

### 问题 1：Agent loop 在哪里？

你要找到类似这样的逻辑：

```python
while step < max_steps:
    prompt = build_prompt(...)
    response = llm(...)
    action = parse(response)
    observation = execute(action)
    history.append(...)
```

你要理解：

```text
一轮循环由哪些部分组成？
哪些是 LLM 决定的？
哪些是系统执行的？
哪些会进入下一轮上下文？
```

### 问题 2：Prompt 是怎么构造的？

重点看：

```text
system prompt
task prompt
history
tool / bash instructions
observation
stop instruction
```

你要记录：

```text
它如何告诉模型可以做什么？
它如何约束模型输出？
它如何把历史塞回上下文？
```

### 问题 3：它用的是自由 bash 还是结构化工具？

mini-swe-agent 通常偏向极简 bash agent。  
这很灵活，但对训练不一定友好。

你要思考：

```text
自由 bash 的优点：
- 灵活
- 工具设计简单
- 模型可以直接执行命令

自由 bash 的缺点：
- 轨迹不结构化
- 工具调用难统计
- SFT/DPO 数据较难规范
- reward attribution 较难
```

所以我们自己的项目建议改成结构化工具：

```json
{
  "thought": "...",
  "action": "run_tests",
  "arguments": {"cmd": "pytest tests/test_x.py"}
}
```

### 问题 4：Observation 怎么回传？

你要看：

```text
命令输出 stdout/stderr 是否完整返回？
是否截断？
是否有长度限制？
错误命令如何处理？
```

迁移到自己项目时要设计：

```text
observation truncation
error message normalization
test output extraction
relevant lines selection
```

### 问题 5：如何停止？

停止条件一般包括：

```text
模型提交最终答案
达到 max_steps
命令超时
任务成功
发生不可恢复错误
```

我们自己的项目需要明确：

```text
submit_patch
max_steps
timeout
test passed
format error too many times
```

### 问题 6：有没有 trace？

mini-swe-agent 可能没有我们需要的完整训练轨迹格式。

你要判断：

```text
是否保存每一步 response？
是否保存 action？
是否保存 observation？
是否保存最终 patch？
是否保存测试结果？
是否保存 reward？
```

如果没有，就要在自己的项目中补：

```text
trace_logger.py
```

---

## 6. mini-swe-agent 第三轮：自己复刻最小版本

不要直接复制源码。  
你应该自己写一个简化版：

```text
harness/agent_loop.py
harness/prompt_builder.py
harness/action_parser.py
harness/tool_registry.py
env_lite/command_executor.py
trajectory/trace_logger.py
```

### 6.1 最小 agent_loop.py 伪代码

```python
class AgentLoop:
    def __init__(self, model, tool_registry, prompt_builder, trace_logger, max_steps=10):
        self.model = model
        self.tool_registry = tool_registry
        self.prompt_builder = prompt_builder
        self.trace_logger = trace_logger
        self.max_steps = max_steps

    def run(self, task):
        history = []
        for step in range(self.max_steps):
            prompt = self.prompt_builder.build(task, history)
            response = self.model.generate(prompt)
            action = parse_action(response)

            if action.name == "submit_patch":
                self.trace_logger.log_final(response)
                break

            observation = self.tool_registry.execute(action)
            history.append({
                "response": response,
                "action": action,
                "observation": observation
            })
            self.trace_logger.log_step(step, response, action, observation)

        result = evaluate_task(task)
        self.trace_logger.log_result(result)
        return result
```

### 6.2 你复刻时必须加的东西

mini-swe-agent 的目标是极简。  
你的目标是后训练，所以你必须加：

```text
1. structured action
2. trace logger
3. reward
4. task metadata
5. failure type
6. SFT data conversion
7. eval metrics
```

---

## 7. mini-swe-agent 学完后的产出

你应该产出一个学习笔记：

```markdown
# mini-swe-agent 学习笔记

## 它解决什么问题？

## 核心 loop 是什么？

## Prompt 如何构造？

## Action 如何执行？

## Observation 如何回传？

## 它为什么极简却有效？

## 它不适合直接用于后训练的地方？

## 我们项目要保留什么？

## 我们项目要改造什么？
```

你还应该画一个流程图：

```text
Task
→ Prompt
→ LLM
→ Action
→ Execution
→ Observation
→ History
→ Next Step
→ Submit
```

---

## 8. SWE-agent 学习目标

SWE-agent 比 mini-swe-agent 更完整。

你不需要第一阶段读完所有代码。  
你重点学：

```text
1. Agent-Computer Interface
2. repository task 定义
3. environment / sandbox 思路
4. tools / commands
5. trajectory
6. evaluation
7. config
8. benchmark
```

SWE-agent 官方文档也提示，目前更多推荐 mini-swe-agent，因为 mini-swe-agent 更简单、开发重心更高。但 SWE-agent 仍然非常适合学习正式工程结构。

---

## 9. SWE-agent 第一轮：先读文档，不急着读源码

你先看官方文档中的这些内容：

```text
Getting Started
Usage
Configuration
Agent / Environment
Tools
Trajectories
SWE-bench evaluation
FAQ
```

你的目标不是记命令，而是回答：

```text
SWE-agent 如何把 GitHub issue 变成一个 agent task？
SWE-agent 如何让模型和 repo 交互？
SWE-agent 的 environment 是什么？
它的 tools 是怎么暴露给模型的？
它怎么保存 trajectory？
它怎么评估任务是否完成？
```

---

## 10. SWE-agent 第二轮：理解 Agent-Computer Interface

SWE-agent 最值得学的是 ACI，Agent-Computer Interface。

简单说：

```text
不是直接让模型乱用电脑，
而是设计一组适合模型理解和执行的命令/接口，
让模型能高效定位、编辑、测试代码。
```

你要重点思考：

```text
为什么工具接口设计会影响 Agent 能力？
为什么命令输出要对模型友好？
为什么搜索、查看、编辑、测试这些动作要被规范？
为什么不能把整个 repo 一次性塞给模型？
```

迁移到我们项目：

```text
tools/list_files.py
tools/read_file.py
tools/search_code.py
tools/edit_file.py
tools/run_tests.py
tools/git_diff.py
```

你自己的工具不是越多越好，而是要：

```text
简单
稳定
可解析
可记录
可评测
适合训练
```

---

## 11. SWE-agent 第三轮：学习任务组织

SWE-agent 面向真实 GitHub issue / SWE-bench。  
我们的第一版不做那么难，但要学它的任务组织方式。

一个代码修复任务需要：

```text
repo
issue / problem statement
test command
expected behavior
environment setup
evaluation script
```

迁移到我们项目：

```text
benchmark/tasks/bugfix_001/
├── repo/
├── tests/
├── issue.md
└── metadata.json
```

metadata 必须包含：

```json
{
  "task_id": "bugfix_001",
  "bug_type": "boundary_condition",
  "test_command": "pytest tests/test_auth.py",
  "target_files": ["auth.py"],
  "difficulty": "easy"
}
```

---

## 12. SWE-agent 第四轮：学习 trajectory

你要重点看 SWE-agent 如何保存运行过程。

你需要理解：

```text
trajectory 是什么？
每一步包含哪些字段？
是否保存模型输出？
是否保存命令？
是否保存 observation？
是否保存 patch？
是否保存结果？
```

我们自己的 trace 至少要保存：

```json
{
  "task_id": "...",
  "model": "...",
  "steps": [
    {
      "thought": "...",
      "action": "...",
      "arguments": {},
      "observation": "...",
      "tool_success": true,
      "timestamp": "..."
    }
  ],
  "final_patch": "...",
  "test_result": "...",
  "reward": 1.0,
  "failure_type": null
}
```

为什么 trajectory 重要？

因为它是后续一切训练数据的来源：

```text
success trace → SFT
failed trace → DPO rejected
productive segment → Credit-SFT
rollout group → GRPO
success pattern → Skill-SD
```

---

## 13. SWE-agent 第五轮：学习评测

你要看 SWE-agent / SWE-bench 的评测逻辑：

```text
一个 patch 是否真的解决问题？
测试是否通过？
是否引入新错误？
环境是否可复现？
```

迁移到我们项目：

```text
pytest pass / fail
patch apply
target test pass
full test pass
tool format valid
max steps
timeout
```

不要只看最终成功率。  
要看多维指标：

```text
Task Success Rate
Test Pass Rate
Tool Valid Rate
Format Error Rate
Patch Apply Rate
Avg Steps
Loop Rate
Unrelated Edit Rate
```

---

## 14. mini-swe-agent 和 SWE-agent 的分工

| 学习内容 | mini-swe-agent | SWE-agent |
|---|---|---|
| 最小 loop | 重点学 | 了解 |
| 极简实现 | 重点学 | 不适合 |
| 工程结构 | 较少 | 重点学 |
| 任务组织 | 较少 | 重点学 |
| tool / ACI | 简单 | 重点学 |
| trajectory | 可参考 | 重点学 |
| benchmark/eval | 简单 | 重点学 |
| 是否直接 fork | 不建议 | 不建议 |
| 是否复刻核心思想 | 强烈建议 | 强烈建议 |

---

## 15. 迁移到 EvoCode-Orchard-Lite 的具体对应关系

### 从 mini-swe-agent 迁移

| mini-swe-agent 学到的 | 迁移到你的项目 |
|---|---|
| agent loop | harness/agent_loop.py |
| prompt construction | harness/prompt_builder.py |
| command execution | env_lite/command_executor.py |
| observation feedback | harness/controller.py |
| max step | configs/agent.yaml |
| simple CLI | run_agent.py |

### 从 SWE-agent 迁移

| SWE-agent 学到的 | 迁移到你的项目 |
|---|---|
| task format | benchmark/tasks/ |
| environment | env_lite/ |
| ACI / tools | tools/ |
| trajectory | trajectories/ |
| evaluation | eval/ |
| config system | configs/ |
| failure analysis | eval/failure_analysis.py |

### 从 Orchard 迁移

| Orchard 学到的 | 迁移到你的项目 |
|---|---|
| Env-first | env_lite/ 独立 |
| trajectory-centric | trajectories/ 统一格式 |
| training recipes | data_builder/ + training/ |
| credit-assignment SFT | build_credit_sft.py |
| Balanced Adaptive Rollout | build_grpo.py / rollout_groups |
| environment-grounded reward | env_lite/reward.py |

---

## 16. 具体阅读清单

### mini-swe-agent 阅读清单

优先看：

```text
README
installation / usage
main entrypoint
agent loop
model call
command execution
prompt template
CLI
```

你要回答：

```text
1. 用户任务怎么进入系统？
2. 模型每轮看到什么？
3. 模型输出什么？
4. 系统怎么执行输出？
5. 执行结果怎么反馈？
6. 什么时候停止？
7. 如何处理错误？
8. 如何复刻？
```

### SWE-agent 阅读清单

优先看：

```text
docs/getting_started
docs/configuration
docs/agent
docs/environment
docs/tools
docs/trajectories
docs/evaluation
GitHub README
examples
```

你要回答：

```text
1. SWE-agent 的任务输入是什么？
2. 它如何管理 repo？
3. 它的工具接口如何设计？
4. 它如何保存 trajectory？
5. 它如何评测 patch？
6. 它有哪些配置抽象？
7. 哪些部分对我们项目太重？
8. 哪些思想必须迁移？
```

---

## 17. 学习时不要陷入的坑

### 坑 1：一上来读所有源码

不要。

先跑通，再读最小链路。

### 坑 2：直接 fork SWE-agent 改

不建议。  
你的项目价值在训练闭环，不是套壳。

### 坑 3：被 OpenHands 吸走

OpenHands 很大，第一阶段不要深入。

### 坑 4：只关注 prompt

Coding Agent 不只是 prompt。  
重点是：

```text
environment
tools
trajectory
reward
evaluation
```

### 坑 5：读完不产出

读源码必须产出：

```text
流程图
模块表
可迁移点
不可迁移点
自己的实现计划
```

---

## 18. 第一轮学习后的产出模板

你应该写一个 `docs/open_source_learning_notes.md`：

```markdown
# Open Source Coding Agent Learning Notes

## 1. mini-swe-agent

### 1.1 核心定位

### 1.2 Agent Loop

### 1.3 Prompt

### 1.4 Action / Command

### 1.5 Observation

### 1.6 Stop Condition

### 1.7 优点

### 1.8 局限

### 1.9 我们项目如何借鉴

## 2. SWE-agent

### 2.1 核心定位

### 2.2 Agent-Computer Interface

### 2.3 Environment

### 2.4 Tools

### 2.5 Task Format

### 2.6 Trajectory

### 2.7 Evaluation

### 2.8 优点

### 2.9 局限

### 2.10 我们项目如何借鉴

## 3. 迁移方案

### 3.1 保留什么

### 3.2 改造什么

### 3.3 不做什么

### 3.4 我们自己的模块设计
```

---

## 19. 学习后立刻开始写的最小代码

你学完 mini-swe-agent 后，马上写：

```text
harness/agent_loop.py
harness/prompt_builder.py
harness/action_parser.py
env_lite/command_executor.py
tools/run_tests.py
trajectories/trace_logger.py
```

不要等读完所有 SWE-agent 再动手。

原因：

```text
边读边写，才能知道自己有没有真的理解。
```

---

## 20. 从学习到项目的具体执行顺序

### Step A：跑通 mini-swe-agent

```text
目标：知道最小 coding agent 怎么工作。
产出：运行截图 + 学习笔记。
```

### Step B：画 mini-swe-agent loop

```text
Task → Prompt → LLM → Action → Execute → Observation → History → Next
```

### Step C：自己实现结构化版本

```text
不要自由 bash，先用 JSON action。
```

### Step D：读 SWE-agent 文档

```text
重点看 ACI、environment、trajectory、eval。
```

### Step E：设计自己的 task format

```text
benchmark/tasks/bugfix_xxx/
```

### Step F：实现 trace logger

```text
为 SFT / DPO / RL 准备数据。
```

### Step G：跑 baseline

```text
拿到失败模式。
```

### Step H：构造 SFT / DPO 数据

```text
进入后训练。
```

---

## 21. 你应该怎么讲“我借鉴了开源项目”？

面试时不要说：

```text
我基于 SWE-agent 改了一个项目。
```

更好的说法：

```text
我先学习了 mini-swe-agent 的极简 agent loop，理解 coding agent 的 observe-action-observation 循环；然后参考 SWE-agent 的 Agent-Computer Interface、任务组织、trajectory 和 evaluation 设计，自己实现了一个更适合后训练的轻量 Coding Agent Harness。相比直接 fork 开源项目，我重点扩展了 trace logging、reward、Credit-SFT-lite、DPO 数据构造、BAR-lite rollout selection 和 Skill Self-Distillation 闭环。
```

这句话说明：

1. 你不是闭门造车。
2. 你不是套壳。
3. 你知道开源项目的价值。
4. 你有自己的改造重点。
5. 你的项目主线是后训练和自我进化。

---

## 22. 最终学习目标检查表

学习 mini-swe-agent 后，你应该能回答：

```text
[ ] agent loop 是什么？
[ ] prompt 怎么构造？
[ ] action 怎么执行？
[ ] observation 怎么回传？
[ ] max_steps 怎么控制？
[ ] 为什么极简 agent 有效？
[ ] 它哪里不适合后训练？
[ ] 我如何改成结构化 tool call？
```

学习 SWE-agent 后，你应该能回答：

```text
[ ] ACI 是什么？
[ ] coding agent 为什么需要专门工具接口？
[ ] task 如何组织？
[ ] repo 如何 reset？
[ ] trajectory 如何保存？
[ ] patch 如何评测？
[ ] SWE-agent 哪些部分太重？
[ ] 我项目应该迁移哪些思想？
```

迁移到自己项目后，你应该完成：

```text
[ ] Env-lite
[ ] Agent Harness
[ ] Tool Registry
[ ] Trace Logger
[ ] Toy Benchmark
[ ] Eval Metrics
[ ] SFT Data Builder
[ ] DPO Data Builder
```

---

## 23. 推荐参考链接

### mini-swe-agent

- GitHub: https://github.com/SWE-agent/mini-swe-agent
- Docs: https://mini-swe-agent.com/

### SWE-agent

- Docs: https://swe-agent.com/latest/
- GitHub: https://github.com/SWE-agent/SWE-agent
- SWE-agent organization: https://github.com/SWE-agent

### Orchard

- GitHub: https://github.com/microsoft/Orchard
- Paper: https://arxiv.org/abs/2605.15040
- HTML: https://arxiv.org/html/2605.15040v1

---

## 24. 最终结论

mini-swe-agent 和 SWE-agent 的学习目标不是“复制项目”，而是帮你建立 Coding Agent 的底层理解。

你应该：

```text
mini-swe-agent：学最小 loop
SWE-agent：学正式工程结构
Orchard：学 Env-first 和训练范式
自己的项目：实现 Env-lite + Harness + Trajectory + Training + Eval
```

最关键的判断是：

```text
开源项目提供参考；
你的项目提供后训练闭环。
```

如果你能讲清楚这点，这个项目就不会像“套壳开源框架”，而会像一个真正有设计、有实验、有工程深度的 AI Agent 项目。

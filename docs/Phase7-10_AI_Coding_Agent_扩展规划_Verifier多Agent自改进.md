# Phase7-10 AI Coding Agent 扩展规划：Verifier-Guided Repair、多 Agent 与自我改进闭环

> 适用项目：EvoCode-Orchard-Lite / M-code  
> 当前定位：从“代码修复后训练实验”升级为“轻量级 AI Coding Agent 应用框架”  
> 当前基础：已有 bugfix benchmark、轨迹数据、Step-SFT / Read-to-Edit / DPO 模型与自动化评测脚本  
> 规划目标：优先补齐 Agent 应用系统能力，而不是继续单纯堆 SFT/DPO/GRPO 训练实验

---

## 1. 总体判断

当前项目已经完成了较多模型后训练实验：

- trajectory-level SFT 已验证效果不稳定，容易学习噪声；
- Step-SFT / Read-to-Edit 是目前最有效的训练路线；
- Patch-Correctness DPO 已做多轮尝试，但收益有限；
- Skill 直接注入实验出现性能下降，不适合作为当前主线；
- 当前最有价值的模型资产是表现最稳的 3B Step-SFT / v2.1-clean 或其 DPO 变体。

因此，后续不要继续把主线写成：

```text
SFT -> DPO -> Skill -> GRPO
```

而应该调整为：

```text
AI Coding Agent Runtime
-> Verifier-Guided Repair
-> Multi-Agent Repair Workflow
-> Failure Memory / Skill Router
-> Self-Improvement Data Loop
-> 可选 GRPO-lite / Execution Reward
```

训练算法只是增强模块，项目主体应该是 AI 编程 Agent 应用系统。

---

## 2. 新项目主线

推荐项目定位：

> EvoCode-Orchard-Lite 是一个面向代码修复任务的轻量级 AI Coding Agent 框架，支持工具调用、自动测试验证、失败归因、多 Agent 修复协作、轨迹数据沉淀与后训练自我改进。

核心技术模块：

```text
1. Agent Runtime
2. Tool Protocol
3. Verifier-Guided Repair
4. Multi-Agent Repair Workflow
5. Failure Memory / Skill Router
6. Self-Improvement Data Loop
7. Optional Execution Reward / GRPO-lite
8. Evaluation Dashboard / Report
```

---

## 3. 为什么第一步只做 Verifier-Guided Repair

建议第一步不要直接做 Multi-Agent，也不要直接做 GRPO。

原因：

1. **Verifier-Guided Repair 与当前框架最兼容**
   - 当前项目已经有任务运行、轨迹保存、测试执行、失败分析基础。
   - 只需要在一次修复失败后，增加“读取失败信息 -> 构造二次修复提示 -> 再运行一次”的闭环。

2. **它最能体现 AI Coding Agent 应用能力**
   - 普通训练项目只关注模型输出。
   - Agent 项目应该关注执行、验证、反馈和再修复。
   - Verifier-Guided Repair 是从“模型训练”转向“Agent 系统”的关键一步。

3. **它能为后续 Multi-Agent 和自我改进提供数据**
   - 二次修复成功样本可以转成 SFT 数据；
   - 第一次失败 patch 与第二次成功 patch 可以转成 DPO pair；
   - 失败原因可以沉淀到 Failure Memory。

4. **成本低，风险低**
   - 不需要马上重新训练；
   - 不需要修改大模型推理服务；
   - 不需要上复杂 RL；
   - 可以先用现有 3B 模型验证系统收益。

---

## 4. Phase 7：Verifier-Guided Repair

### 4.1 阶段目标

在现有 single-agent 代码修复流程上增加一次自动二次修复能力：

```text
任务输入
-> Agent 第一次修复
-> run_tests
-> 如果成功：保存成功轨迹
-> 如果失败：Verifier 分析失败原因
-> 构造 repair prompt
-> Agent 第二次修复
-> run_tests
-> 保存 repair 轨迹与结果
```

核心对比：

```text
single-pass success rate
vs
repair-loop success rate
```

### 4.2 推荐使用模型

不要默认使用 DPO 后模型。需要先做一次模型选择。

候选：

```text
1. 3B Base
2. 3B Step-SFT / v2.1-clean
3. 3B DPO variant
4. 7B Base / 7B Instruct
```

选择原则：

- Coder / Repair Agent 使用当前 clean eval 上表现最稳的模型；
- 如果 DPO 模型低于 v2.1-clean，则默认使用 v2.1-clean；
- DPO 模型只作为实验候选，不作为必然主线；
- 7B 可以作为 Planner / Reviewer 候选，但 Phase 7 暂时不需要。

### 4.3 Verifier 不建议用 LLM

Verifier 第一版应该用规则和执行结果，不要依赖 LLM：

```text
run_tests
patch apply check
diff check
是否修改测试文件
是否无 edit
是否读过目标文件
是否仍然测试失败
traceback / assertion 提取
```

LLM 可以后续用于 Reviewer，但 Verifier 的基础判断应尽量确定性。

### 4.4 失败类型分类

建议统一失败类型枚举：

```text
SUCCESS
NO_EDIT
TOOL_ERROR
JSON_INVALID
PATCH_APPLY_FAIL
WRONG_FILE
NO_TARGET_READ
TEST_STILL_FAIL
OVER_EDIT
MODIFIED_TEST
TIMEOUT
UNKNOWN
```

每条失败轨迹至少保存：

```json
{
  "task_id": "bugfix_251",
  "run_id": "...",
  "model_id": "...",
  "stage": "first_attempt",
  "success": false,
  "failure_type": "TEST_STILL_FAIL",
  "test_output_excerpt": "...",
  "changed_files": ["..."],
  "target_files_read": true,
  "patch_applied": true
}
```

### 4.5 Repair Prompt 设计

二次修复 prompt 不要重新开始，而要包含执行反馈：

```text
You attempted to fix the bug, but tests still fail.

Task:
{task_prompt}

Changed files:
{changed_files}

Current diff:
{diff}

Test failure:
{test_output_excerpt}

Failure type:
{failure_type}

Repair instruction:
Focus only on fixing the remaining failure.
Do not modify tests.
Keep the patch minimal.
If the previous file is wrong, inspect the relevant source file before editing.
```

中文项目中也可以保留英文 prompt，因为模型训练与工具调用通常更适合英文结构化指令。

### 4.6 Phase 7 交付物

建议新增或改造以下模块：

```text
evocode_orchard_lite/repair/
  verifier.py
  failure_classifier.py
  repair_prompt.py
  repair_runner.py
  metrics.py

evocode_orchard_lite/runtime/
  agent_runner.py
  test_runner.py
  diff_inspector.py

evocode_orchard_lite/reports/
  repair_eval_report.py
```

如果当前项目已有相近目录，则优先复用，不要强行新建重复结构。

### 4.7 Phase 7 评测指标

必须统计：

```text
first_pass_success_rate
repair_success_rate
final_success_rate
repair_gain = final_success_rate - first_pass_success_rate
avg_steps_first_pass
avg_steps_with_repair
avg_runtime
failure_type_distribution_before_repair
failure_type_distribution_after_repair
```

重点不是只看最终成功率，而是看 repair loop 解决了哪些失败。

### 4.8 Phase 7 成功标准

建议最低成功标准：

```text
repair_gain >= +3%
且不显著增加 TOOL_ERROR / JSON_INVALID / MODIFIED_TEST
```

理想结果：

```text
repair_gain >= +5%
TEST_STILL_FAIL 明显下降
NO_EDIT / WRONG_FILE 不上升
平均运行成本可接受
```

如果 repair_gain 很低，也要保存结果，因为它能为下一阶段 Multi-Agent / Failure Memory 提供依据。

---

## 5. Phase 8：MCP-style Tool Protocol

### 5.1 阶段目标

把当前 Agent 工具层抽象成统一协议，便于后续多 Agent 复用。

不一定要立即接入真实 MCP server，但接口设计应该接近 MCP 思路：

```text
tool name
input schema
output schema
error schema
trace logging
permission boundary
```

### 5.2 推荐工具集合

```text
read_file(path, start_line?, end_line?)
search_code(query, path?)
list_files(path, pattern?)
apply_patch(patch)
edit_file(path, old, new)
run_tests(command, timeout?)
inspect_diff()
classify_failure(test_output, diff, trace)
save_trajectory(trace)
build_sft_sample(trace)
build_dpo_pair(chosen, rejected)
```

### 5.3 为什么要做这一层

简历和项目报告中，这一层可以写成：

> 设计 MCP-style 工具协议层，统一封装代码检索、文件编辑、测试执行、diff 检查与轨迹存储接口，支持多 Agent 复用同一执行环境。

这属于 AI Agent 应用开发能力，不是单纯算法实验。

---

## 6. Phase 9：Multi-Agent Repair Workflow

### 6.1 阶段目标

在 Phase 7 的 repair loop 稳定后，再扩展为轻量多 Agent。

不要一开始做复杂对话式群体协商，先做顺序式 pipeline：

```text
Planner -> Coder -> Verifier -> Reviewer -> Repair
```

### 6.2 角色设计

#### Planner Agent

职责：

```text
分析任务
预测相关文件
决定优先 read/search 的位置
生成简短修复计划
```

推荐模型：

```text
普通 7B Instruct / 更强 API 模型
```

原因：

```text
Planner 需要通用理解和高层推理，不一定适合用 SFT 后的 3B Coder。
```

#### Coder Agent

职责：

```text
读取文件
生成 patch
调用 edit/apply_patch 工具
```

推荐模型：

```text
当前表现最稳的 3B Step-SFT / v2.1-clean / DPO candidate
```

#### Verifier

职责：

```text
运行测试
检查 patch 是否应用
判断失败类型
提取错误摘要
```

推荐实现：

```text
规则 + pytest + diff parser
```

不建议第一版用 LLM。

#### Reviewer Agent

职责：

```text
检查是否修改测试
检查是否过度修改
检查 diff 是否明显偏离任务
判断是否需要 repair
```

推荐模型：

```text
规则优先；必要时使用普通 7B Instruct。
```

#### Repair Agent

职责：

```text
基于 Verifier / Reviewer 反馈做二次修复
```

推荐模型：

```text
与 Coder 相同，使用当前最稳的 3B 后训练模型。
```

### 6.3 实验对比

至少做三组：

```text
A. Single-Agent: 当前 3B best model
B. Single-Agent + Verifier-Guided Repair
C. Multi-Agent Hybrid: Planner/Reviewer 7B, Coder/Repair 3B, Verifier rules
```

如果 C 不提升，不能硬吹多 Agent。可以分析多 Agent 在小任务上的额外复杂度与错误传播问题。

---

## 7. Phase 10：Failure Memory / Skill Router

### 7.1 不再做全量 Skill 注入

之前 Skill 直接注入导致性能下降，说明：

```text
通用 skill prompt 可能干扰模型原有编辑策略
```

因此后续不要做：

```text
每个任务都塞一大段 skill 文本
```

改成：

```text
失败类型 -> 选择一个短 repair strategy -> 只在二次修复时注入
```

### 7.2 轻量 Skill Router

可以先做 JSON 规则库：

```json
{
  "TEST_STILL_FAIL": {
    "strategy": "Inspect the failing assertion and current diff. Do not rewrite unrelated logic.",
    "forbidden": "Do not modify tests. Do not make broad refactors."
  },
  "NO_EDIT": {
    "strategy": "You must edit the source file after reading the target context.",
    "forbidden": "Do not only explain the issue."
  },
  "WRONG_FILE": {
    "strategy": "Search for the function or symbol mentioned in the failure before editing.",
    "forbidden": "Do not keep editing the previously changed unrelated file."
  }
}
```

这可以称为：

```text
Failure Memory / Repair Skill Library
```

不要称为完整长期记忆系统，除非后续真的加入持久化检索、更新和版本管理。

---

## 8. Phase 11：Self-Improvement Data Loop

### 8.1 阶段目标

把 Agent 执行结果自动沉淀为下一轮训练数据。

闭环：

```text
run agent
-> verify result
-> classify failure
-> build SFT samples
-> build DPO pairs
-> train candidate model
-> eval candidate
-> promote or reject model
```

### 8.2 数据生成规则

成功轨迹：

```text
进入 SFT / Step-SFT 数据池
```

第一次失败、repair 成功：

```text
第二次成功 patch -> chosen
第一次失败 patch -> rejected
构造 DPO pair
```

失败但有有效编辑：

```text
可进入 rejected pool
用于 DPO / failure analysis
```

格式错误 / 工具错误：

```text
不进入 clean SFT
可进入格式修复或工具调用专项数据
```

### 8.3 模型晋级规则

不要训练完就默认使用新模型。

建议引入 promotion gate：

```text
candidate_success_rate >= baseline_success_rate + 2%
JSON/tool valid 不下降
MODIFIED_TEST 不上升
avg_runtime 不明显恶化
```

如果不满足，则模型进入 archive，不作为默认模型。

这一步可以体现“自我改进”不是口号，而是有自动评测门控。

---

## 9. Optional：Execution Reward / GRPO-lite

GRPO 不建议现在马上做主线。

更稳妥的顺序：

```text
1. 先做 Best-of-N reranking
2. 再做 reward model 或 rule reward
3. 最后尝试 GRPO-lite
```

### 9.1 Rule Reward

可以先定义执行奖励：

```text
JSON valid: +0.5
tool call valid: +0.5
target file read: +1
patch applies: +1
tests pass: +3
no edit: -2
wrong file: -1
modified tests: -3
test still fail: -1
over edit: -1
```

### 9.2 Best-of-N

同一任务采样多个候选 patch：

```text
candidate_1
candidate_2
candidate_3
candidate_4
```

分别运行 verifier，用 reward 选择最优。

这比直接 GRPO 简单，也能验证 reward 是否合理。

### 9.3 GRPO-lite

只有当 Best-of-N reward 与真实成功率相关时，才进入 GRPO-lite。

否则不要强行做。

---

## 10. 推荐执行顺序

### Step 1：冻结当前最佳模型

目标：

```text
明确默认 Coder/Repair 模型
```

需要对比：

```text
3B Base
3B v2.1-clean
3B DPO variants
7B Base if available
```

输出：

```text
docs/current_best_model_report.md
```

### Step 2：实现 Verifier-Guided Repair

目标：

```text
single-agent + one repair attempt
```

输出：

```text
repair_eval_single_agent.json
repair_eval_report.md
```

### Step 3：实现 Failure Classifier

目标：

```text
把每条失败归因到固定 failure_type
```

输出：

```text
failure_distribution.json
failure_examples/
```

### Step 4：实现 Tool Protocol 整理

目标：

```text
统一工具输入输出和轨迹 schema
```

输出：

```text
tool_schema.py
trajectory_schema.py
```

### Step 5：实现 Multi-Agent Pipeline

目标：

```text
Planner/Coder/Verifier/Reviewer/Repair 顺序执行
```

输出：

```text
multi_agent_eval_report.md
```

### Step 6：实现 Failure Memory / Skill Router

目标：

```text
失败类型驱动的短策略注入
```

输出：

```text
repair_skills.json
skill_router.py
```

### Step 7：实现 Self-Improvement Data Loop

目标：

```text
自动从新轨迹生成 SFT/DPO 数据
```

输出：

```text
self_improve_sft.jsonl
self_improve_dpo.jsonl
candidate_model_eval_report.md
```

### Step 8：可选 GRPO-lite

目标：

```text
验证 execution reward 是否能稳定提升
```

输出：

```text
best_of_n_report.md
grpo_lite_report.md
```

---

## 11. 简历可写方向

如果 Phase 7-11 做完，项目可以写成：

> 设计并实现面向代码修复任务的轻量级 AI Coding Agent 框架，支持 MCP-style 工具协议、多 Agent 修复协作、测试反馈驱动二次修复、失败类型归因、轨迹数据自举与 SFT/DPO 后训练优化。

可拆成简历 bullet：

```text
- 基于 mini-swe-agent 二次开发 AI Coding Agent Runtime，封装代码检索、文件编辑、测试执行、diff 检查与轨迹记录工具，形成 read-edit-test 自动修复闭环。
- 设计 Verifier-Guided Repair 机制，基于测试失败、patch diff 和工具调用日志自动归因失败类型，并驱动 Agent 进行二次修复。
- 构建 Planner-Coder-Verifier-Reviewer-Repair 多 Agent 协作流程，采用混合模型路由策略，将后训练 3B 模型用于代码编辑，将通用 Instruct 模型用于规划与审查。
- 构建 Failure Memory / Skill Router，将 NO_EDIT、WRONG_FILE、TEST_STILL_FAIL 等失败模式映射为可复用修复策略，仅在二次修复阶段按需注入。
- 搭建轨迹数据自举管线，将成功修复轨迹转化为 SFT 数据，将失败/成功 patch 转化为 DPO 偏好对，并通过自动化评测门控筛选候选模型。
```

---

## 12. 风险与边界

### 12.1 不要过早宣称完整自进化

当前只能说：

```text
具备自我改进数据闭环雏形
```

只有当系统能自动完成：

```text
运行 -> 归因 -> 生成数据 -> 训练 -> 评测 -> 晋级
```

才适合说：

```text
Verifier-Guided Self-Improvement
```

### 12.2 不要强行保留降性能 Skill

Skill 降性能不是失败，而是重要结论：

```text
全量静态 skill prompt 会干扰代码修复策略
```

后续应该改为：

```text
failure-specific short strategy
```

### 12.3 不要把 DPO 当主贡献

DPO 是偏好学习模块，不是系统主线。

主贡献应该是：

```text
Agent Runtime + Verifier Repair + Multi-Agent + Failure Memory + Self-Improvement
```

### 12.4 防止 eval 数据污染

所有后续阶段必须严格区分：

```text
训练任务
开发任务
独立评测任务
```

任何用于构造 SFT/DPO/Skill/Memory 的任务，都不能再作为 clean independent eval。

---

## 13. 最小可执行版本

如果只做一周，建议只做：

```text
1. 冻结当前最佳 3B Coder 模型
2. 增加一次 Verifier-Guided Repair
3. 统计 first-pass vs repair-loop 成功率
4. 输出 failure_type 分布
5. 从 repair 成功样本生成一版 self-improve DPO 数据
```

这个版本已经足够把项目从“训练实验”推进到“Agent 应用系统”。

---

## 14. 最终目标

最终项目不应描述为：

```text
我们做了 SFT 和 DPO
```

而应描述为：

```text
我们构建了一个轻量级 AI Coding Agent 平台，
通过工具协议、执行验证、多 Agent 协作、失败记忆和轨迹数据自举，
实现代码修复任务中的自动执行、自动评测与后训练自我改进。
```


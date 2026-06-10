# M-code Phase 6：Patch-Correctness DPO 与项目成果固化规划（更新版）

> 用途：交给开发 agent 执行。  
> 当前状态：M-code 已完成 step-level SFT、read-to-edit transition SFT、clean r2e 数据管线、New50 + New100 双 held-out 验证。  
> 当前主结果：3B v2.1-clean 在 New50 上达到 98%，在 New100 harder benchmark 上达到 66%，均超过 7B Base。  
> 本次更新重点：明确 **New100 失败任务产生的约 33 个 DPO pairs 只是 DPO-sanity seed，不是正式 DPO 主训练集**。正式 Patch-Correctness DPO 建议扩展到 **200-300 个高质量 pairs**，并新增独立 DPO-eval，避免用参与 DPO 构造的 New100 failures 直接证明泛化。

---

## 0. 本文档相对上一版的关键更正

上一版 Phase 6 方向是对的：当前瓶颈已经从 NO_EDIT 转向 patch correctness，因此下一步应该做 Patch-Correctness DPO，而不是继续堆 r2e 或立刻上 GRPO。

但上一版有一个容易被误解的地方：

```text
New100 v2.1-clean 大约失败 33-34 个任务；
每个失败任务构造一个 same-task chosen/rejected pair；
于是可能被误解成正式 DPO 只需要 33 个 pairs。
```

这个理解不够稳。

本版明确：

```text
1. 约 33 个 same-task pairs 只是 DPO-sanity seed set；
2. 这批 seed pairs 用于验证 DPO pipeline，不直接作为正式 DPO 主训练集；
3. 正式 Patch-Correctness DPO 建议扩展到 200-300 个高质量 pairs；
4. 如果使用 New100 failures 构造 DPO，则 New100 不再是完全干净的 DPO 后泛化评测集；
5. 建议新增 bugfix_351-400 作为 DPO-independent eval，或将 New100 拆成 DPO-train-failure subset 和 DPO-eval subset。
```

---

# 1. 当前阶段最终结果

| 模型 | New50 easy | New100 hard | 判断 |
|---|---:|---:|---|
| 3B Base | 46% | 21% | 原始 3B 基线 |
| 3B SFT v2 | 54% | 31% | step-level SFT 有效，但 NO_EDIT 仍多 |
| 7B Base | 82% | 58% | 更强基座参考 |
| **3B v2.1-clean** | **98%** | **66%** | 当前主结果，超过 7B Base |

当前可以形成以下阶段判断：

```text
M-code 已经完成一个可信的 Agentic Coding 后训练闭环。项目从 trajectory-level SFT 失败出发，通过 step-level SFT 修复工具调用和格式稳定性，再通过 failure analysis 定位 NO_EDIT/read-file loop，构造 train-only read-to-edit transition 数据继续训练，使 3B 模型在 New50 上达到 98%，在 New100 harder benchmark 上达到 66%，均超过 7B Base。当前主要瓶颈已从“不敢编辑”转变为 harder bugs 下的 patch correctness。
```

必须保留边界表述：

```text
该结论成立于当前自建 toy-code-repair / harder-code-repair benchmark，不应泛化成“3B 全面强于 7B Coder”。
```

---

# 2. 当前项目已经完成的关键闭环

当前项目已经形成一条完整的研究/工程链路：

```text
trajectory-level SFT 失败
→ step-level SFT v2 有效
→ failure analysis 定位 NO_EDIT/read_file loop
→ dirty v2.1 发现 read-to-edit 有效但数据管线污染
→ leakage audit 发现 old28/test/val 混入
→ clean r2e train-only 数据重建
→ 修复 r2e completion 缺失 bug
→ 修复 LoRA 继续训练问题
→ 修复 basic_tools.py 路径 bug
→ v2.1-clean 在 New50 / New100 双 held-out 上复验成功
```

这条链路非常适合写进项目报告和面试说明，因为它体现了：

```text
不是盲目刷分；
而是能发现失败、分析原因、审计数据、修复训练目标、验证泛化。
```

---

# 3. 当前主要问题已经变化

## 3.1 v2 的主要问题

v2 的主要问题是：

```text
NO_EDIT / read_file loop
```

表现为：

```text
反复 read_file
不进入 edit_file
任务到达 max steps 后失败
```

## 3.2 v2.1-clean 已经解决大部分 NO_EDIT

v2.1-clean 通过 read-to-edit transition 数据，使模型更倾向于：

```text
read_file → edit_file → run_tests → submit
```

因此 NO_EDIT 不再是第一瓶颈。

## 3.3 当前 New100 的主要问题

当前 New100 上 v2.1-clean 的主要失败已经转为：

```text
TEST_STILL_FAIL
WRONG_PATCH
PATCH_APPLY_ERROR
```

也就是说：

```text
模型已经敢编辑；
但 harder bugs 下 patch correctness 还不够。
```

因此 Phase 6 的技术目标应该从：

```text
read-to-edit
```

转向：

```text
patch correctness
test-feedback correction
wrong-patch preference optimization
```

---

# 4. Phase 6 总目标

Phase 6 包含两条主线：

```text
A. 项目成果固化线
B. Patch-Correctness DPO 技术推进线
```

优先级：

```text
1. 先更新 README 和最终报告，让 GitHub 一打开就能看到项目亮点。
2. 再对 New100 的失败任务做 patch-correctness failure analysis。
3. 先构造 30-50 个高质量 seed pairs 做 DPO-sanity。
4. 如果 sanity 通过，再扩展到 200-300 个正式 DPO pairs。
5. 新增独立 DPO-eval，避免训练/评测污染。
6. 训练 Patch-Correctness DPO。
7. 在 New50 / New100 reference / DPO-independent eval 上复验。
8. 暂缓 GRPO，除非 DPO 后仍有明显策略问题。
```

---

# Part A：项目成果固化线

## Step A1：更新 README

### 目标

当前 README 不能只保留早期 skeleton / milestone 描述。README 必须第一眼展示：

```text
这是一个完整的 Agentic Coding 后训练系统；
当前已经完成 v2.1-clean；
3B 模型在 New50/New100 上超过 7B Base；
项目有泄漏审计和 clean held-out 评测。
```

### 建议新增 README 结构

```text
# M-code / EvoCode-Agent

## 1. Project Overview
## 2. Why This Project
## 3. System Architecture
## 4. Training Pipeline
## 5. Key Results
## 6. What Went Wrong and How We Fixed It
## 7. Current Limitations
## 8. Next Steps
## 9. Repository Structure
## 10. Reproduction Guide
```

### README 中必须加入的核心结果表

```markdown
| Model | New50 easy | New100 hard |
|---|---:|---:|
| 3B Base | 46% | 21% |
| 3B Step-SFT v2 | 54% | 31% |
| 7B Base | 82% | 58% |
| **3B v2.1-clean** | **98%** | **66%** |
```

### README 中必须加入的项目故事线

```text
1. Trajectory-level SFT failed.
2. Step-level SFT v2 improved held-out success from 46% to 54%.
3. Failure analysis found NO_EDIT/read_file loop.
4. Read-to-edit transition SFT was introduced.
5. Data leakage audit detected dirty r2e pipeline.
6. Clean train-only r2e data was rebuilt.
7. v2.1-clean achieved 98% on New50 and 66% on New100.
8. Current bottleneck shifted from NO_EDIT to patch correctness.
```

### README 中必须加的边界

```text
This project does not claim that a 3B model is generally stronger than a 7B coder model.
The result is specific to the constructed coding-agent environment and held-out toy/harder code-repair benchmark.
```

---

## Step A2：整理最终结果文档

### 目标

当前 `docs/v21_clean_final_results.md` 是核心报告，需要进一步结构化，方便评审/面试阅读。

建议结构：

```text
docs/v21_clean_final_results.md

1. Executive Summary
2. Experimental Setup
3. Dataset and Splits
4. Leakage Audit
5. Training Pipeline
6. Bugs Fixed During Development
7. Main Results
8. Failure Mode Shift
9. Why v2.1-clean Works
10. Limitations
11. Next Steps
```

### 必须包含的图表/表格

#### 主结果表

```text
New50 / New100 四模型对比
```

#### full metrics 表

包括：

```text
Success Rate
JSON Parse
Tool Valid
Test Pass After Edit
Avg Steps
Loop Rate
NO_EDIT Rate
Patch Error Rate
Test Fail Rate
```

#### Failure mode shift 表

建议写成：

```text
v2：主要失败 = NO_EDIT
v2.1-clean：主要失败 = TEST_STILL_FAIL / WRONG_PATCH
```

这说明模型能力已经从“是否行动”推进到“是否改对”。

---

## Step A3：补充可复现实验说明

### 目标

即使权重和 outputs 不上传，仓库也要说明如何复现实验。

建议新增：

```text
docs/reproduction_guide.md
```

内容包括：

```text
1. 环境依赖
2. 数据构造流程
3. 训练 v2
4. 构造 clean r2e
5. 训练 v2.1-clean
6. 构造 New100
7. 评测四个模型
8. 生成最终报告
```

如果权重未上传，需要写明：

```text
LoRA adapter checkpoints are stored on the training server and are not included in the repository.
The repository contains the code, benchmark generation scripts, data construction scripts, evaluation scripts, and reports.
```

---

# Part B：Patch-Correctness DPO 技术推进线

## Step B1：New100 failure analysis

### 目标

当前 New100 上 v2.1-clean 成功率为 66%，失败约 34 个任务。主要失败应从 NO_EDIT 转向：

```text
TEST_STILL_FAIL
WRONG_PATCH
PATCH_APPLY_ERROR
```

需要先做系统化失败分析，不能直接训练 DPO。

### 输出文件

```text
outputs/reports/new100_v21_clean_failure_analysis.md
outputs/reports/new100_v21_clean_failure_analysis.json
```

### 分析维度

每个失败任务记录：

```json
{
  "task_id": "bugfix_281",
  "bug_type": "regex_parsing",
  "difficulty": "medium",
  "success": false,
  "failure_type": "TEST_STILL_FAIL",
  "action_sequence": ["read_file", "edit_file", "run_tests", "edit_file", "run_tests"],
  "edited_files": ["..."],
  "test_output_summary": "...",
  "patch_size": 4,
  "reason": "wrong condition for empty input",
  "is_no_edit": false,
  "is_wrong_patch": true,
  "is_patch_apply_error": false,
  "candidate_dpo_type": "wrong_patch"
}
```

### failure_type 分类

```text
NO_EDIT
TEST_STILL_FAIL
WRONG_PATCH
PATCH_APPLY_ERROR
OVER_EDIT
UNDER_EDIT
MISREAD_TEST_OUTPUT
PREMATURE_SUBMIT
FORMAT_ERROR
TOOL_INVALID
```

### 重点统计

```text
每种 failure_type 数量
每种 bug_type 成功率
每种 difficulty 成功率
v2.1-clean vs 7B Base 对比
哪些任务 7B 成功但 v2.1-clean 失败
哪些任务 v2.1-clean 成功但 7B 失败
```

---

## Step B2：构造 Patch-Correctness DPO seed pairs

### 目标

先不要直接构造正式 DPO 主训练集。  
第一步应该构造：

```text
DPO-sanity seed set
```

数量：

```text
30-50 pairs
```

来源：

```text
New100 中最干净、最明确的 same-task chosen/rejected pairs
```

### Same-task seed pair 定义

chosen：

```text
teacher / 7B / mimo 成功轨迹
```

rejected：

```text
v2.1-clean 在同一个 task 上的失败轨迹
```

这类 pair 的质量最高，但数量有限，大约 33-34 个。

### seed pairs 的用途

这批 pairs 只用于：

```text
验证 DPO 数据格式；
验证 DPO loss 是否正常下降；
验证 adapter 继续训练是否正常；
验证 JSON/tool 能力是否不崩；
验证 DPO 后没有灾难性退化。
```

不要把它作为正式 Patch-Correctness DPO 主结果。

---

## Step B2.5：DPO 数据规模与切分原则（重要）

### 1. 33 个 pairs 的定位

New100 上 v2.1-clean 大约失败 34 个任务，因此可以自然得到约 33-34 个 same-task pairs。

这批数据应该定位为：

```text
Patch-Correctness DPO seed set
```

不是：

```text
正式 DPO 主训练集
```

### 2. 为什么 33 个 pairs 不够正式训练

如果只用 33 个 pairs 做正式 DPO，风险包括：

```text
1. 数据量太少，容易过拟合；
2. 只修这 33 个失败任务，不一定泛化；
3. 训练波动大；
4. 可能破坏 v2.1-clean 已有 JSON/tool 能力；
5. 如果 DPO 后还用 New100 证明提升，会出现“用评测失败集训练，再评测同一集”的污染问题。
```

### 3. 正式 DPO 数据量建议

建议分三档：

| 阶段 | Pair 数量 | 用途 |
|---|---:|---|
| DPO-sanity | 30-50 | 验证脚本、格式、loss 和 adapter |
| DPO-small | 100-200 | 第一版有效训练 |
| DPO-main | 200-300 | 正式 Patch-Correctness DPO |

当前推荐路线：

```text
先做 30-50 pairs sanity；
通过后扩展到 200-300 pairs main。
```

### 4. 正式 DPO-main 推荐组成

| Pair 类型 | 数量建议 | 作用 |
|---|---:|---|
| same-task correct patch vs wrong patch | 30-40 | 最高质量 seed |
| failed-task multi-pair 拆分 | 50-80 | 从一个失败轨迹拆多个偏好点 |
| same bug_type patch-correctness pairs | 80-120 | 提升同类 bug 泛化 |
| test-feedback correction pairs | 30-60 | 学会根据测试失败修正 |
| residual NO_EDIT pairs | 20-30 | 少量防止 NO_EDIT 反弹 |

总量建议：

```text
200-300 pairs
```

不要一开始追求 1000+，质量优先。

### 5. New100 训练污染问题

如果使用 New100 failures 构造 DPO pairs，那么 New100 不再是完全干净的 DPO 后泛化评测集。

DPO 后 New100 只能作为：

```text
New100 reference eval
```

不能作为最强泛化结论。

### 6. 推荐新增独立 DPO-eval

最稳做法：

```text
新增 bugfix_351-400，共 50 个任务
作为 DPO-independent held-out eval
```

流程：

```text
1. 用 New100 failures 构造 DPO pairs；
2. 训练 DPO；
3. 在 New50 / New100 做参考评测；
4. 在 bugfix_351-400 上做主验证。
```

### 7. 备选方案：New100 内部切分

如果暂时不新增任务，可以把 New100 拆分为：

```text
DPO-train-failure subset
DPO-eval subset
```

但需要在报告中明确：

```text
这是 New100-DPO-split evaluation，不是全新 held-out。
```

---

## Step B3：扩展正式 Patch-Correctness DPO pairs

DPO 不再优先解决 NO_EDIT，而是解决：

```text
模型已经 edit 了，但 patch 不正确；
测试失败后没有正确修正；
修改过小或过大；
对 harder bug type 的修复逻辑不够。
```

### 数据来源优先级

```text
1. same-task pair：同一个 New100 task，chosen 是 teacher/7B/mimo 成功轨迹，rejected 是 v2.1-clean 失败轨迹。
2. same bug_type pair：同一 bug type 下，成功轨迹 vs 错误 patch 轨迹。
3. same failure_type pair：TEST_STILL_FAIL / WRONG_PATCH 类型下的 chosen/rejected。
```

不要优先 random pair。

### Pair 类型 1：correct patch vs wrong patch

chosen：

```text
read_file
→ edit_file with minimal correct patch
→ run_tests pass
→ submit
```

rejected：

```text
read_file
→ edit_file with plausible but wrong patch
→ run_tests fail
→ submit or loop
```

适用：

```text
TEST_STILL_FAIL
WRONG_PATCH
UNDER_EDIT
OVER_EDIT
```

### Pair 类型 2：test-feedback correction

chosen：

```text
edit_file
→ run_tests fail
→ read test output
→ revise patch
→ run_tests pass
→ submit
```

rejected：

```text
edit_file
→ run_tests fail
→ repeat same edit / ignore error / submit anyway
```

适用：

```text
MISREAD_TEST_OUTPUT
TEST_STILL_FAIL
```

### Pair 类型 3：minimal patch vs over-edit

chosen：

```text
只修改必要逻辑
patch 小
测试通过
```

rejected：

```text
修改无关逻辑
patch 大
测试失败或不稳定
```

适用：

```text
OVER_EDIT
PATCH_APPLY_ERROR
```

### Pair 类型 4：remaining NO_EDIT cleanup

chosen：

```text
read_file
→ edit_file
→ run_tests
```

rejected：

```text
read_file
→ read_file
→ max_steps
```

适用：

```text
NO_EDIT residual cases
```

该类型只作为少量补充，因为 NO_EDIT 已经不是主瓶颈。

---

## Step B4：实现 DPO 数据构造脚本

### 新增文件

```text
data_builder/build_patch_correctness_dpo.py
```

### 输入

```text
outputs/rollouts/v21_clean_new100/
outputs/rollouts/teacher_success_new100/
outputs/reports/new100_v21_clean_failure_analysis.json
```

### 输出

```text
outputs/data/dpo_patch_correctness_seed_pairs.jsonl
outputs/data/dpo_patch_correctness_pairs.jsonl
outputs/reports/dpo_patch_correctness_data_audit.md
outputs/reports/dpo_patch_correctness_data_audit.json
```

### 每条 DPO pair 字段

```json
{
  "pair_id": "bugfix_281_patch_correctness_001",
  "task_id": "bugfix_281",
  "bug_type": "regex_parsing",
  "difficulty": "medium",
  "pair_type": "correct_patch_vs_wrong_patch",
  "chosen_source": "teacher_success",
  "rejected_source": "v21_clean_failure",
  "chosen": "...",
  "rejected": "...",
  "failure_type": "TEST_STILL_FAIL",
  "split": "dpo_train",
  "source_trace_chosen": "...",
  "source_trace_rejected": "...",
  "heldout_eval_excluded": true
}
```

### 数据审计要求

必须检查：

```text
pair 数量
same-task pair 占比
same bug_type pair 占比
chosen success rate = 100%
rejected success rate = 0%
held-out leakage = 0
answer leakage = 0
chosen/rejected 格式 parse rate = 100%
New100 DPO-train 和 DPO-eval 是否隔离
DPO-independent eval 是否未出现在 pairs 中
```

---

## Step B5：DPO-sanity 训练

### 目的

先用 30-50 seed pairs 验证流程。

### 推荐模型基座

```text
3B v2.1-clean adapter
```

不要从 3B Base 或 v2 开始。

### 训练名称

```text
3B v2.1-clean-DPO-sanity
```

### 训练参数建议

```yaml
method: DPO + LoRA continuation
base_adapter: 3B v2.1-clean
pairs: 30-50 seed pairs
learning_rate: 1e-6
epochs: 1
beta: 0.1
max_length: 4096
max_prompt_length: 3072
warmup_ratio: 0.03
```

### 验收标准

DPO-sanity 不追求正式涨分，只看：

```text
DPO loss 正常下降；
adapter 正确加载；
训练不报错；
JSON Parse 不崩；
Tool Valid 不崩；
New50 不灾难性下降；
New100 不灾难性下降。
```

如果 sanity 后 New50 / New100 明显下降，禁止进入 DPO-main。

---

## Step B6：DPO-main 训练

### 前置条件

只有 DPO-sanity 通过后，才进入 DPO-main。

### 推荐数据量

```text
200-300 high-quality pairs
```

### 训练名称

```text
3B v2.1-clean-DPO-patch
```

### 训练参数建议

```yaml
method: DPO + LoRA continuation
base_adapter: 3B v2.1-clean
pairs: 200-300
learning_rate: 1e-6 to 5e-6
epochs: 1
beta: 0.1
max_length: 4096
max_prompt_length: 3072
warmup_ratio: 0.03
```

DPO 要保守。当前 v2.1-clean 已经很强，不要用大 lr 破坏 JSON/tool 能力。

### 禁止事项

```text
不要 get_peft_model 覆盖已有 adapter；
不要 init_lora_weights=true 重置 adapter；
不要把 DPO-independent eval tasks 混进训练；
不要为了提高 New100 分数污染 New100 eval subset。
```

### 输出

```text
training/train_dpo_patch_correctness.py
models/3b_v21_clean_dpo_sanity/
models/3b_v21_clean_dpo_patch/
outputs/reports/train_dpo_sanity_log.md
outputs/reports/train_dpo_patch_correctness_log.md
```

---

## Step B7：DPO 后评测

### 必评模型

```text
3B Base
3B SFT v2
3B v2.1-clean
3B v2.1-clean-DPO-sanity
3B v2.1-clean-DPO-patch
7B Base
```

### 必评 benchmark

```text
New50 easy
New100 reference
DPO-independent eval: bugfix_351-400
```

如果暂时没有 bugfix_351-400，则至少使用：

```text
New100-DPO-eval subset
```

但报告中必须注明它不是全新 held-out。

### 指标

```text
Success Rate
JSON Parse
Tool Valid
Test Pass After Edit
Avg Steps
Loop Rate
NO_EDIT Rate
TEST_STILL_FAIL Rate
WRONG_PATCH Rate
PATCH_APPLY_ERROR Rate
Per-bug-type Success
```

### 目标

合理目标：

```text
DPO-independent eval:
v2.1-clean-DPO-patch 相比 v2.1-clean 有正提升。

New100 reference:
66% → 70%-75% 只能作为参考，不是最终泛化证明。

TEST_STILL_FAIL:
明显下降。

NO_EDIT:
保持低位，不反弹。

JSON/Tool:
保持 >= 90%-95%。
```

---

# Part C：暂缓 GRPO / RL

## 为什么暂缓 GRPO

当前问题已经非常具体：

```text
harder bugs 下 patch correctness 不够
```

这更适合先用 DPO 解决。

GRPO/RL 现在的问题：

```text
成本高
波动大
reward 设计复杂
容易在 toy benchmark 上过拟合
会增加项目复杂度
```

因此暂缓。

## 什么时候再做 GRPO-lite

只有满足以下条件后再考虑：

```text
DPO 后 DPO-independent eval 仍无明显提升；
failure 类型仍然集中；
reward 可稳定定义为 test pass / patch apply / tool valid；
rollout 成本可控。
```

可以做：

```text
GRPO-lite / BAR-lite
每个 task 采样 4 条 rollout
只保留有成功有失败的 informative tasks
reward = test pass + patch apply + tool valid - loop penalty
```

但这不是当前阶段任务。

---

# Part D：最终报告与简历固化

## README / 报告推荐表达

英文版本：

```text
Built EvoCode-Agent, an Orchard-inspired coding-agent post-training framework with local sandbox, structured tool use, trajectory logging, leakage-audited data construction, and held-out evaluation. After trajectory-level SFT failed, I redesigned the training target as step-level SFT, improving a 3B Coder model from 46% to 54% on held-out tasks. Failure analysis identified NO_EDIT/read-file loops as the main bottleneck, so I introduced train-only read-to-edit transition tuning, improving the 3B model to 98% on New50 and 66% on a harder New100 benchmark, outperforming a 7B Base model under the same agent environment.
```

中文版本：

```text
构建 EvoCode-Agent 代码修复后训练框架，包含本地 sandbox、结构化工具调用、trajectory logging、数据泄漏审计和 held-out evaluation。针对 trajectory-level SFT 失败问题，重构为 step-level SFT，使 3B Coder 模型在 held-out 上从 46% 提升到 54%。进一步通过 failure analysis 定位 NO_EDIT/read-file loop，构造纯 train-split read-to-edit transition 数据继续训练，使 3B v2.1-clean 在 New50 上达到 98%，在 harder New100 上达到 66%，在相同 Agent 环境下超过 7B Base。
```

## 边界表达

必须加：

```text
当前结果基于自建 toy/harder code-repair benchmark，不等同于 SWE-bench 级通用软件工程能力。
```

这句话一定要有。

---

# Part E：给开发 agent 的执行指令

请开发 agent 按以下顺序执行：

```text
1. 更新 README，加入当前 v2.1-clean 主结果、项目故事线、系统结构和限制说明。
2. 整理 docs/v21_clean_final_results.md，使其成为最终阶段报告。
3. 输出 New100 v2.1-clean failure analysis，重点分析 TEST_STILL_FAIL / WRONG_PATCH / PATCH_APPLY_ERROR。
4. 先构造 30-50 个 same-task seed pairs，输出 dpo_patch_correctness_seed_pairs.jsonl。
5. 用 seed pairs 做 DPO-sanity，只验证流程，不作为正式结果。
6. 如果 sanity 通过，扩展到 200-300 个 high-quality DPO-main pairs。
7. 新增 bugfix_351-400 作为 DPO-independent eval，或者拆分 New100-DPO-eval subset。
8. 生成 DPO 数据审计报告，确认 chosen 成功、rejected 失败、无 held-out leakage、eval tasks 未进入 DPO pairs。
9. 基于 3B v2.1-clean adapter 训练 3B v2.1-clean-DPO-patch。
10. 在 New50、New100 reference、DPO-independent eval 上重新评测。
11. 如果 DPO-independent eval 有正提升，且 JSON/tool 不崩，记录为 Phase 6 成果。
12. 在 DPO-main 结果出来前，不要做 GRPO。
```

---

# 最终判断

当前 M-code 已经可以作为一个完整大项目写进简历。

它的价值不只是：

```text
SFT 提升了成功率。
```

而是：

```text
构建了一个可执行、可审计、可评测、可迭代的 Coding Agent 后训练系统。
```

下一阶段 Phase 6 的关键不是再解决 NO_EDIT，而是：

```text
Patch-Correctness DPO：
让模型在 harder bugs 下不仅敢改，而且改得对。
```

更正后的关键执行原则是：

```text
33 个 pairs 只做 DPO-sanity；
正式 DPO-main 需要 200-300 个高质量 pairs；
DPO 后必须用独立 eval 验证，不能只看参与 pair 构造的 New100。
```

如果 Phase 6 成功，项目主线会变成：

```text
SFT 学工具协议
→ read-to-edit SFT 学行动转换
→ DPO 学 patch correctness
→ 可选 RL 学搜索与修复策略
```

这条路线非常完整，也非常适合面向 AI Agent / LLM Application / Agentic Coding 岗位展示。

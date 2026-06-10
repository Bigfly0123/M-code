# M-code Phase 5：v2.1-clean 泛化验证与最终结果固化规划

> 用途：交给开发 agent 执行。  
> 当前状态：3B SFT v2.1-clean 在 new50 held-out 上达到 98.0%，并且 r2e 数据已修复为纯 train split、无 held-out 泄漏。  
> 当前重点：不要立刻进入 DPO / GRPO，而是把 v2.1-clean 的 98% 结果通过更严格的文档、指标、失败分析和 harder held-out 验证固化为可信最终阶段结果。  
> 阶段目标：从“当前 benchmark 上非常强”推进到“泛化验证更充分、报告可写、面试问不穿”。

---

## 1. 当前最终结果

| 模型 | Held-out 50 | 数据清洁度 | 判断 |
|---|---:|---|---|
| 3B Base | 42.0% | — | 基线 |
| 3B SFT v2 | 54.0% | 可信 | step-level SFT 有效 |
| 7B Base | 76.0% | — | 强基座参考 |
| **3B SFT v2.1-clean** | **98.0%** | 纯 train-split，无泄漏 | 当前最强阶段性结果 |

当前可以形成以下阶段判断：

```text
3B SFT v2.1-clean 在 clean new50 held-out 上达到 98.0%，显著超过 3B Base 的 42.0%、3B SFT v2 的 54.0% 和 7B Base 的 76.0%。该结果说明 read-to-edit transition SFT 对 NO_EDIT/read_file loop 问题具有显著效果。
```

但该结论必须加边界：

```text
该结果目前限定在当前 toy-code-repair held-out 50 benchmark 上。下一步需要通过 harder held-out、unseen bug type、full metrics 和失败分析验证泛化能力。
```

---

## 2. 本阶段之前已经解决的问题

### 2.1 trajectory-level SFT 失败

旧的 trajectory-level SFT 结果低于 3B Base。主要问题是训练目标与真实 agent inference 不对齐，整条轨迹监督导致模型学不到“当前状态 → 下一步 action”的映射，格式和工具调用也不稳定。

### 2.2 Step-SFT v2 取得可信提升

```text
3B Base: 42.0%
3B SFT v2: 54.0%
提升：+12.0%
```

说明 step-level prompt-completion SFT 有真实泛化收益。

### 2.3 Failure Analysis 定位 NO_EDIT

v2 在 new50 的失败中，主要问题是：

```text
NO_EDIT / read_file loop
```

即模型反复 read_file，不进入 edit_file。

### 2.4 v2.1 dirty 发现大幅提升但数据管线有污染

dirty v2.1 曾达到 90%，但审计发现 r2e 数据混入 old28 test / val / unknown tasks。虽然不污染 new50，但不能作为最终发布版。

### 2.5 v2.1-clean 修复数据管线

已经修复：

```text
只使用 train split 构造 r2e；
排除 test / val / held-out / unknown；
修复 completion 未进入 messages 的训练格式 bug；
修复 basic_tools.py 路径 bug；
从 v2 adapter 正确继续训练。
```

最终：

```text
3B SFT v2.1-clean new50 = 98.0%
```

---

## 3. 本阶段核心目标

Phase 5 的目标不是继续刷当前 new50 分数，而是完成：

```text
1. 正式记录 v2.1-clean 结果；
2. 补齐 full metrics；
3. 分析唯一失败任务；
4. 构造 harder new100 held-out；
5. 在 harder new100 上验证 v2.1-clean 泛化；
6. 再决定是否需要 DPO / GRPO。
```

---

# 4. Phase 5 执行路线总览

请开发 agent 按以下顺序执行：

```text
Step 1：新增 docs/v21_clean_final_results.md
Step 2：补齐 v2.1-clean full metrics
Step 3：分析 new50 唯一失败任务
Step 4：构造 harder new100 held-out tasks
Step 5：在 new100 上评测 3B Base / v2 / v2.1-clean / 7B Base
Step 6：做 per-bug-type 和 failure analysis
Step 7：根据 new100 结果决定下一阶段方向
Step 8：更新 README 和最终项目报告
```

---

# Step 1：新增 v2.1-clean 最终结果文档

## 1.1 新增文件

```text
docs/v21_clean_final_results.md
```

## 1.2 文档必须包含

### A. 实验背景

说明：

```text
v2.1-clean 是在可信 Step-SFT v2 adapter 基础上，使用纯 train-split read-to-edit transition 数据继续训练得到。
```

### B. 数据清洁度审计

必须写明：

```text
r2e task 与 bugfix_201-250 overlap = 0
original SFT 与 bugfix_201-250 overlap = 0
rollouts 与 bugfix_201-250 overlap = 0
test split samples = 0
val split samples = 0
unknown samples = 0
answer leakage = 0
source_trace_path / split / in_train_split 字段齐全
```

### C. Bug 修复记录

记录本轮修复的 3 个 bug：

```text
1. basic_tools.py 路径 bug：
   path.relative_to(task.workspace) 在 workspace 是相对路径时失败；
   改为 task.workspace.resolve()。

2. r2e 数据格式 bug：
   apply_chat_template(messages) 没有包含 completion；
   修复为将 edit_file action 作为最后一条 assistant message 加入 messages。

3. r2e 数据管线污染：
   原脚本从所有 rollouts 抽取 r2e；
   修复为 build_read_to_edit_sft_clean.py 只允许 train split。
```

### D. 结果表

至少包含：

| 模型 | New50 Success | 数据状态 |
|---|---:|---|
| 3B Base | 42.0% | clean eval |
| 3B SFT v2 | 54.0% | clean eval |
| 7B Base | 76.0% | clean eval |
| 3B SFT v2.1-clean | 98.0% | train-only r2e，无泄漏 |

### E. 当前结论和边界

写明：

```text
v2.1-clean 证明 read-to-edit transition SFT 能显著解决 NO_EDIT/read_file loop。
但该结论目前限定在当前 new50 toy-code-repair benchmark。
下一步需要 harder held-out / unseen bug type 验证泛化。
```

---

# Step 2：补齐 v2.1-clean full metrics

## 2.1 为什么必须补

当前只有 success rate 还不够。98% 很高，必须证明不是通过不健康行为获得的，比如疯狂 edit、忽略测试、JSON 格式下降、工具调用异常、路径 bug 假阳性、只适配简单任务。

## 2.2 必须补齐的指标

输出完整表格：

| 指标 | 3B Base | 3B SFT v2 | 3B SFT v2.1-clean | 7B Base |
|---|---:|---:|---:|---:|
| Success Rate | 42.0% | 54.0% | 98.0% | 76.0% |
| JSON Parse | 56.0% | 96.0% | TBD | 78.0% |
| Tool Valid | 56.0% | 96.0% | TBD | 78.0% |
| Test Pass After Edit | 44.0% | 52.0% | TBD | 80.0% |
| Avg Steps | 10.0 | 6.9 | TBD | 5.8 |
| Loop Rate | 56.0% | 46.0% | TBD | 18.0% |
| NO_EDIT Rate | 40.0% | 48.0% | TBD | 10.0% |
| Patch Error Rate | TBD | TBD | TBD | TBD |
| Test Fail Rate | TBD | TBD | TBD | TBD |
| Read-to-Edit Rate | TBD | TBD | TBD | TBD |
| Same-file Read Loop Rate | TBD | TBD | TBD | TBD |

## 2.3 输出文件

```text
outputs/reports/v21_clean_full_metrics_new50.md
outputs/reports/v21_clean_full_metrics_new50.json
```

## 2.4 验收标准

v2.1-clean 应尽量满足：

```text
JSON Parse >= 95%
Tool Valid >= 95%
NO_EDIT Rate 显著低于 v2
Loop Rate 显著低于 v2
Avg Steps 不异常膨胀
Test Pass After Edit 显著提升
```

如果出现以下情况，需要重新分析：

```text
Success 高，但 JSON/Tool 降低；
Success 高，但 Avg Steps 极高；
Success 高，但 Patch Error 高。
```

---

# Step 3：分析 new50 唯一失败任务

## 3.1 为什么必须分析

98% 意味着：

```text
49/50 成功
1/50 失败
```

唯一失败任务非常重要，因为它能说明当前模型还剩什么问题。

## 3.2 输出文件

```text
outputs/reports/v21_clean_single_failure_analysis.md
```

## 3.3 分析内容

必须包括：

```text
task_id
bug_type
issue 描述
模型 action sequence
是否 read_file
是否 edit_file
是否 run_tests
是否 submit
失败类型
失败原因
和 7B Base / v2 的表现对比
是否属于 harder case
是否需要加入 future training data
```

## 3.4 失败类型分类

从以下类型中选择：

```text
NO_EDIT
WRONG_PATCH
TEST_FAIL_AFTER_EDIT
PATCH_APPLY_ERROR
FORMAT_ERROR
TOOL_INVALID
PREMATURE_SUBMIT
OVER_EDIT
TASK_BUG_OR_TEST_BUG
```

## 3.5 判断标准

如果唯一失败是 WRONG_PATCH / harder bug type，说明模型已经基本解决 NO_EDIT，下一步应扩展 harder tasks。

如果唯一失败仍是 NO_EDIT，说明 read-to-edit 还有边界，需要保留 NO_EDIT DPO 方向。

---

# Step 4：构造 harder new100 held-out tasks

## 4.1 为什么需要 new100

new50 上 98% 非常强，但也可能说明：

```text
当前 held-out 50 对 v2.1-clean 太容易；
任务模板化较强；
read-to-edit 数据学到了当前 benchmark 的修复模式。
```

因此下一步必须做 harder held-out，而不是直接 DPO / GRPO。

## 4.2 新任务范围

建议新增：

```text
bugfix_251-350
```

共 100 个任务。

输出目录：

```text
benchmark/tasks/bugfix_251-350/
```

split 文件：

```text
benchmark/splits/new100_heldout_tasks.txt
```

## 4.3 任务设计原则

new100 必须比 new50 更难，避免模板化。覆盖以下 harder bug types：

```text
1. regex parsing bug
2. date/time parsing bug
3. path normalization bug
4. exception handling bug
5. nested condition bug
6. type conversion bug
7. list/dict mutation bug
8. off-by-one in loops
9. multi-branch return bug
10. default argument bug
11. stateful counter bug
12. multi-file interaction bug
13. config parsing bug
14. string normalization bug
15. boundary + empty input combined bug
```

## 4.4 难度分层

### Easy 30%

```text
单文件
单函数
1-3 行修改
测试明确
```

### Medium 50%

```text
单文件或双文件
需要理解条件分支
需要根据 test output 定位
3-8 行修改
```

### Hard 20%

```text
双文件或多函数
需要理解状态流
错误不在最表层
测试输出不直接告诉答案
可能需要先 run_tests 再 read_file
```

## 4.5 避免泄漏

new100 必须满足：

```text
不在 train_tasks.txt
不在 val_tasks.txt
不在 old28 test_tasks.txt
不在 new50 bugfix_201-250
不出现在任何 r2e clean 数据
不出现在任何 original SFT 数据
不出现在任何 teacher rollouts 训练数据
```

新增审计脚本：

```text
eval/audit_new100_leakage.py
```

输出：

```text
outputs/reports/new100_leakage_audit.md
```

---

# Step 5：在 new100 上重新评测

## 5.1 评测模型

必须评测：

```text
3B Base
3B SFT v2
3B SFT v2.1-clean
7B Base
```

可选：

```text
dirty v2.1
```

dirty v2.1 只作为参考，不作为主结论。

## 5.2 评测指标

必须输出：

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
Read-to-Edit Rate
Same-file Read Loop Rate
Per-bug-type success
```

## 5.3 输出文件

```text
outputs/reports/new100_eval_summary.md
outputs/reports/new100_eval_summary.json
outputs/reports/new100_per_bug_type.md
outputs/reports/new100_failure_analysis.md
```

---

# Step 6：结果解释规则

## 6.1 如果 v2.1-clean 在 new100 上 >= 80%

结论：

```text
v2.1-clean 具有较强泛化能力；
read-to-edit transition SFT 不只是适配 new50；
当前可以作为项目主结果。
```

下一步：

```text
更新 README；
写最终项目报告；
准备简历表达；
可选做 DPO，不是必须。
```

## 6.2 如果 v2.1-clean 在 new100 上 65%-79%

结论：

```text
v2.1-clean 仍显著有效，但 new50 确实偏容易；
模型在 harder bug types 上仍有短板。
```

下一步：

```text
基于 new100 failure analysis 补 train-only teacher traces；
构造 harder read-to-edit 数据；
考虑 NO_EDIT-specific DPO 或 wrong-patch DPO。
```

## 6.3 如果 v2.1-clean 在 new100 上 <= 64%

结论：

```text
v2.1-clean 对 new50 泛化好，但对 harder tasks 泛化不足；
当前主要成果仍是方法闭环，而不是强泛化模型。
```

下一步：

```text
扩充 train tasks；
重新设计 r2e 数据；
加入 more diverse teacher traces；
暂缓 DPO/GRPO。
```

---

# Step 7：暂缓 DPO / GRPO

## 7.1 为什么暂缓

当前 v2.1-clean new50 已经 98%，继续 DPO 可能只是在当前 benchmark 上过拟合，放大数据偏置，引入新的训练不稳定，并掩盖泛化问题。

## 7.2 什么时候做 DPO

只有在 new100 结果出来后再决定。

### 场景 A：new100 仍然很高

```text
v2.1-clean >= 80%
```

DPO 不是必须。可以只做少量 preference polishing。

### 场景 B：new100 中 NO_EDIT 仍多

做：

```text
NO_EDIT-specific DPO
```

### 场景 C：new100 中 WRONG_PATCH 多

做：

```text
correct patch vs wrong patch DPO
```

### 场景 D：test feedback 使用差

做：

```text
test-feedback correction DPO
```

---

# Step 8：更新 README 和项目报告

## 8.1 README 应加入的故事线

建议 README 中新增：

```text
Current Milestone: Step-SFT v2.1-clean
```

内容：

```text
1. Trajectory-level SFT failed.
2. Step-level SFT v2 improved held-out success from 42% to 54%.
3. Failure analysis found NO_EDIT/read_file loop.
4. Read-to-edit transition SFT was introduced.
5. Data leakage audit detected dirty r2e pipeline.
6. Clean train-only r2e data was rebuilt.
7. v2.1-clean achieved 98% on clean new50 held-out.
8. Next: harder new100 generalization verification.
```

## 8.2 项目报告应强调

不是单纯写：

```text
SFT 后达到 98%
```

而是写：

```text
通过 trajectory-level SFT 失败分析、step-level SFT 重构、NO_EDIT failure diagnosis、read-to-edit transition tuning、数据泄漏审计和 clean held-out 复验，构建了一个可审计的 Agentic Coding 后训练闭环。
```

---

# 9. 简历表达建议

如果 new100 还没完成，可以暂时写：

```text
构建 EvoCode-Agent 代码修复后训练框架，包含本地 sandbox、结构化工具调用、trajectory logging、held-out evaluation 与数据泄漏审计。针对 trajectory-level SFT 失败问题，重构为 step-level SFT，使 3B Coder 模型在 clean held-out 上从 42% 提升到 54%。进一步通过 failure analysis 定位 NO_EDIT/read-file loop，并构造 train-only read-to-edit transition 数据继续训练，使 clean v2.1 在 held-out 50 上达到 98%，显著超过 7B Base 的 76%。同时修复 adapter 继承、r2e 数据管线污染、训练格式缺失 completion 和路径处理 bug，保证评测无 train/eval overlap。
```

更稳版本：

```text
在当前 toy-code-repair held-out benchmark 上，clean v2.1 达到 98%；后续正在扩展 harder held-out 和 unseen bug type 以验证更强泛化。
```

---

# 10. 给开发 agent 的最终执行指令

请开发 agent 直接执行：

```text
1. 新增 docs/v21_clean_final_results.md，正式记录 v2.1-clean 98% 结果。
2. 补齐 v2.1-clean full metrics，包括 JSON Parse、Tool Valid、Test Pass After Edit、Avg Steps、Loop Rate、NO_EDIT Rate、Patch Error Rate。
3. 输出 outputs/reports/v21_clean_full_metrics_new50.md 和 json。
4. 分析 new50 唯一失败任务，输出 outputs/reports/v21_clean_single_failure_analysis.md。
5. 新增 bugfix_251-350 共 100 个 harder held-out tasks。
6. 生成 benchmark/splits/new100_heldout_tasks.txt。
7. 实现 eval/audit_new100_leakage.py，确认 new100 与所有训练数据、r2e 数据、rollouts 无重叠。
8. 在 new100 上评测 3B Base、3B SFT v2、3B SFT v2.1-clean、7B Base。
9. 输出 new100_eval_summary.md、new100_per_bug_type.md、new100_failure_analysis.md。
10. 在 new100 结果出来前，暂缓 DPO / GRPO。
11. 根据 new100 结果决定是否进入 DPO 或继续扩展 harder r2e 数据。
```

---

# 11. 最终判断

当前 M-code 已经进入一个很好的阶段：

```text
不是只有一个高分结果；
而是有完整的失败分析、数据修复、训练修复、泄漏审计和 clean held-out 复验链路。
```

当前最重要的不是继续堆训练，而是证明：

```text
98% 不只是当前 new50 的特例；
read-to-edit transition SFT 在 harder held-out 上仍然有效。
```

Phase 5 完成后，如果 new100 结果仍然强，项目就可以进入最终报告与简历固化阶段。  
如果 new100 下降明显，也不是失败，而是会自然引出下一阶段：

```text
harder teacher traces
NO_EDIT-specific DPO
wrong-patch DPO
test-feedback DPO
```

这样整个项目会非常完整。

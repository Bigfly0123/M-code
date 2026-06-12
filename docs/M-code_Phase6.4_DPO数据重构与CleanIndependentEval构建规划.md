# M-code Phase 6.4：DPO 数据重构与 Clean Independent Eval 构建专项规划

> 用途：交给开发 agent 执行。  
> 当前任务：本阶段**只做数据构建与数据审计**，不训练、不评测、不做 GRPO。  
> 背景：Phase 6.3 中构建了 `bugfix_351-400` independent tasks，但其中部分失败任务被用于生成 DPO pairs，导致该 independent eval 不再完全干净。因此当前需要重新规范数据构建流程：  
> 1. 构建真正干净的 DPO-independent eval：`bugfix_401-450`；  
> 2. 构建新的 DPO-main-v3 训练数据；  
> 3. 明确禁止把 `bugfix_401-450` 中任何任务用于训练数据；  
> 4. 对所有数据做 overlap / leakage audit；  
> 5. 本阶段完成后，再进入训练阶段。

---

## 0. 当前问题说明

### 0.1 之前 Phase 6.3 的主要问题

Phase 6.3 做了以下事情：

```text
1. 构建 bugfix_351-400 independent tasks；
2. v2.1-clean 在 independent 上约 40%；
3. 从 independent failures 中生成 12 个 DPO pairs；
4. 训练 DPO-main-v2；
5. 又把 bugfix_351-400 放入 200 tasks 中评测。
```

这一步的问题是：

```text
bugfix_351-400 已经参与 DPO pair 构造，因此它不再是 clean independent eval。
```

所以 `bugfix_351-400` 后续只能叫：

```text
DPO-source reference eval
```

不能继续作为：

```text
clean DPO-independent eval
```

---

### 0.2 当前必须纠正的原则

从现在开始，必须明确区分：

```text
训练数据来源
评测数据来源
reference eval
clean independent eval
```

尤其是：

```text
任何进入 DPO pairs 的 task，都不能再作为 clean independent eval。
```

因此当前需要构建新的 clean independent eval：

```text
bugfix_401-450
```

并且保证：

```text
bugfix_401-450 不进入 SFT；
不进入 r2e；
不进入 DPO-sanity；
不进入 DPO-main；
不进入 DPO-main-v2；
不进入 DPO-main-v3；
不进入 teacher/mimo pair 构造；
不进入任何训练数据。
```

---

# 1. 本阶段目标

本阶段名称：

```text
Phase 6.4: Data Reconstruction and Clean Independent Eval Construction
```

本阶段只做一件事：

```text
重新构建数据。
```

具体包括：

```text
1. 清理当前数据边界；
2. 标记已有数据集角色；
3. 构建 bugfix_401-450 作为真正 clean independent eval；
4. 构建 DPO-main-v3 训练数据；
5. DPO-main-v3 训练数据只能来自 train/new100/reference sources，不能来自 bugfix_401-450；
6. 生成完整数据审计报告；
7. 输出下一阶段训练可用的数据清单。
```

本阶段不做：

```text
1. 不训练 DPO-main-v3；
2. 不做 GRPO；
3. 不把 bugfix_401-450 失败样本用于 DPO pairs；
4. 不用 bugfix_401-450 生成 teacher/mimo chosen；
5. 不把 reference eval 误写成 clean eval；
6. 不为了凑数量引入低质量 pairs。
```

---

# 2. 数据集角色重新定义

## 2.1 已有数据集角色

请将现有数据集重新标记为：

| 数据集 | 角色 | 是否可用于训练 | 是否可作为 clean eval |
|---|---|---:|---:|
| old28 | legacy eval / reference | 否 | 否，历史用途 |
| New50 | easy held-out / reference | 否 | 可作为 reference，不作为唯一结论 |
| New100 | harder held-out / DPO source reference | 部分失败任务已用于 DPO | 否，DPO 后只能 reference |
| bugfix_351-400 | contaminated independent / reference | 已有 failure pair 被用于 DPO | 否 |
| bugfix_401-450 | clean DPO-independent eval | **绝对禁止** | **是** |

---

## 2.2 后续报告中的命名要求

后续报告中必须这样命名：

```text
New50: easy reference eval
New100: hard reference eval
bugfix_351-400: contaminated reference eval / DPO-source reference
bugfix_401-450: clean DPO-independent eval
```

禁止继续写：

```text
bugfix_351-400 independent eval
```

如果必须提到，也要写：

```text
bugfix_351-400 was originally intended as independent eval, but it was later used for DPO pair construction and is therefore no longer clean.
```

---

# 3. 构建 bugfix_401-450：Clean DPO-independent Eval

## 3.1 目标

构建 50 个全新任务：

```text
bugfix_401
...
bugfix_450
```

作为真正的：

```text
clean DPO-independent eval
```

该数据集只用于评测，不用于任何训练数据构建。

---

## 3.2 难度要求

`bugfix_401-450` 不能太简单。  
它应比 New50 难，接近或略高于 New100 / bugfix_351-400 的难度。

建议难度分布：

| 难度 | 数量 |
|---|---:|
| easy | 8 |
| medium | 27 |
| hard | 15 |

理由：

```text
New50 已经被 v2.1-clean 做到 98%，太简单；
clean independent eval 应该测试 harder patch correctness；
但也不能全 hard，否则结果过低，不利于分析。
```

---

## 3.3 bug 类型覆盖

建议覆盖 15-20 种 bug 类型。

必须包含：

```text
wrong_condition
off_by_one
none_handling
type_conversion
regex_parsing
date_time
dict_key
list_mutation
nested_condition
exception_handling
path_normalization
string_escape
multi_file
stateful_logic
boundary_case
test_feedback_required
indentation_sensitive
patch_apply_sensitive
```

推荐分布：

| Bug Type | 数量建议 |
|---|---:|
| wrong_condition / nested_condition | 5-7 |
| off_by_one / boundary_case | 5-6 |
| none_handling | 4-5 |
| type_conversion | 4-5 |
| regex_parsing | 4-5 |
| date_time | 3-4 |
| dict_key / list_mutation | 5-6 |
| exception_handling | 3-4 |
| path_normalization | 3-4 |
| string_escape | 2-3 |
| multi_file | 3-5 |
| stateful_logic | 3-5 |
| test_feedback_required | 4-6 |
| indentation_sensitive / patch_apply_sensitive | 4-6 |

---

## 3.4 任务设计原则

每个任务必须满足：

```text
1. 有明确 bug；
2. 有明确测试；
3. 修复不依赖外部网络；
4. 不需要大型依赖；
5. 单任务可在本地 sandbox 内运行；
6. 至少一个测试在原始代码上失败；
7. 正确修复后测试通过；
8. 不能与 bugfix_001-400 重复或高度相似；
9. 不能泄漏答案到 prompt；
10. prompt 不包含 new_text / solution / patch。
```

---

## 3.5 任务复杂度要求

### easy

```text
单文件；
单点修改；
bug 明确；
测试反馈直接。
```

### medium

```text
单文件或轻微多文件；
需要理解边界条件；
测试反馈需要推理；
可能涉及类型、None、regex、date、dict/list。
```

### hard

```text
多文件或状态逻辑；
需要根据测试输出定位问题；
可能需要二次 run_tests 后修正；
涉及 patch apply sensitive old_text；
不应该靠简单字符串替换解决。
```

---

## 3.6 文件结构

建议生成：

```text
benchmark/tasks/bugfix_401/
benchmark/tasks/bugfix_402/
...
benchmark/tasks/bugfix_450/
```

每个任务目录结构保持和现有任务一致，例如：

```text
bugfix_401/
  task.json
  workspace/
    ...
  tests/
    ...
```

如果项目当前格式不同，请保持与 `bugfix_001-350` 一致。

---

## 3.7 Split 文件

新增：

```text
benchmark/splits/dpo_independent_eval_401_450.txt
```

内容：

```text
bugfix_401
bugfix_402
...
bugfix_450
```

同时在总 split 说明中标记：

```text
bugfix_401-450: clean DPO-independent eval, never used for training.
```

---

# 4. 构建 DPO-main-v3 训练数据

## 4.1 数据来源原则

DPO-main-v3 训练数据可以来自：

```text
1. train split 任务；
2. New100 reference failures；
3. bugfix_351-400 reference failures；
4. teacher / 7B / mimo 成功轨迹；
5. DPO-main / v2.1-clean 失败轨迹；
6. 已有 non-independent DPO pairs。
```

但绝对禁止来自：

```text
bugfix_401-450
```

包括：

```text
不能用 bugfix_401-450 的失败生成 rejected；
不能用 bugfix_401-450 调 mimo 生成 chosen；
不能用 bugfix_401-450 做 same-task pair；
不能用 bugfix_401-450 做 same bug_type pair；
不能用 bugfix_401-450 做任何训练或偏好数据。
```

---

## 4.2 DPO-main-v3 数据目标

目标数据量：

```text
220-300 pairs
```

不要盲目追求 500+。

推荐组成：

| Pair 类型 | 数量目标 | 说明 |
|---|---:|---|
| WRONG_PATCH / TEST_STILL_FAIL | 90-120 | 主体 |
| TEST_FEEDBACK_CORRECTION | 35-50 | 关键 |
| PATCH_APPLY_STABILITY | 35-50 | 关键 |
| MINIMAL_PATCH vs OVER_EDIT | 15-25 | 辅助 |
| UNDER_EDIT / COMPLETE_FIX | 15-25 | 辅助 |
| PRESERVE_SUCCESS / anti-regression | 10-20 | 防止 DPO 改坏原成功任务 |
| residual NO_EDIT | 5-10 | 少量保持行动能力 |
| FORMAT_ERROR | <=10 | 不再重点扩 |

---

## 4.3 需要优先补的 pair 类型

### A. WRONG_PATCH / TEST_STILL_FAIL

目标：

```text
模型已经能 edit，但 tests 仍失败。
```

chosen：

```text
正确 patch
run_tests pass
submit
```

rejected：

```text
patch apply 成功
但 run_tests fail
或 submit 后失败
```

关键要求：

```text
rejected 最好 patch_apply=true；
这样模型学的是“改得对”，不是“格式对”。
```

---

### B. TEST_FEEDBACK_CORRECTION

目标：

```text
模型第一次 patch 不对，但应该根据 test output 修正。
```

chosen：

```text
edit_file
→ run_tests fail
→ read/parse test output
→ revise patch
→ run_tests pass
→ submit
```

rejected：

```text
edit_file
→ run_tests fail
→ ignore test output / repeat same patch / submit anyway
```

这类 pair 对 harder bugs 很关键。

---

### C. PATCH_APPLY_STABILITY

目标：

```text
降低 PATCH_APPLY_ERROR。
```

chosen：

```text
edit_file 使用短且精确的 old_text；
old_text 能唯一匹配；
new_text 保留缩进/换行；
patch apply 成功；
run_tests。
```

rejected：

```text
old_text_not_found；
indentation_mismatch；
wrong_file；
malformed_edit_json；
overlong_old_text；
quote_escape_error。
```

---

### D. MINIMAL_PATCH vs OVER_EDIT

目标：

```text
避免模型为了修一个小 bug 改大量无关代码。
```

chosen：

```text
最小必要修改；
测试通过。
```

rejected：

```text
大范围重写；
引入新错误；
测试失败或行为不稳定。
```

---

### E. PRESERVE_SUCCESS / anti-regression

目标：

```text
防止 DPO 把 v2.1-clean 原本成功的任务改坏。
```

chosen：

```text
v2.1-clean 成功轨迹；
或 teacher 成功轨迹。
```

rejected：

```text
DPO-main / DPO-main-v2 在同一任务上失败轨迹。
```

---

## 4.4 DPO-main-v3 输出文件

新增：

```text
data/dpo_patch_correctness_v3_pairs.jsonl
data/dpo_patch_correctness_v3_audit.json
docs/dpo_patch_correctness_v3_audit.md
```

---

## 4.5 每条 pair 字段

建议统一为：

```json
{
  "pair_id": "bugfix_xxx_wrong_patch_001",
  "task_id": "bugfix_xxx",
  "task_split_role": "train|new100_reference|bugfix_351_400_reference",
  "bug_type": "...",
  "difficulty": "easy|medium|hard",
  "pair_type": "wrong_patch",
  "failure_type": "TEST_STILL_FAIL",
  "chosen_source": "mimo|7b|teacher|v21_clean_success",
  "rejected_source": "v21_clean_failure|dpo_main_failure|base_failure",
  "chosen": "...",
  "rejected": "...",
  "chosen_success": true,
  "rejected_success": false,
  "chosen_patch_apply": true,
  "rejected_patch_apply": true,
  "source_trace_chosen": "...",
  "source_trace_rejected": "...",
  "excluded_from_clean_eval": true
}
```

---

# 5. Teacher / mimo 数据生成规范

## 5.1 我们之前的数据生成原则

之前 DPO 数据的合理来源是：

```text
chosen = mimo / 7B / teacher 成功轨迹
rejected = v2.1-clean / DPO-main / base 失败轨迹
```

这仍然是正确方向。

---

## 5.2 mimo 可以用于哪些任务？

mimo 可以用于：

```text
train split
New100 reference tasks
bugfix_351-400 reference tasks
已有 contaminated/reference tasks
```

mimo 不能用于：

```text
bugfix_401-450 clean independent eval
```

原因：

```text
一旦 bugfix_401-450 被用于生成 teacher/mimo chosen，它就不再是 clean independent eval。
```

---

## 5.3 mimo 轨迹质量要求

mimo / teacher 轨迹必须满足：

```text
1. patch_apply=true；
2. run_tests pass；
3. submit success；
4. action schema 与当前 harness 一致；
5. 不包含答案泄漏字段；
6. 不包含不可复现的外部依赖；
7. old_text/new_text 可在当前 workspace 中应用；
8. 轨迹可被 replay 或至少可通过静态审计。
```

---

## 5.4 生成 teacher trace 的建议流程

对每个可用于训练的 failed task：

```text
1. 读取 task prompt；
2. 运行 teacher/mimo 生成修复轨迹；
3. replay 轨迹或执行 patch；
4. run_tests；
5. 如果 pass，则保存为 chosen；
6. 如果 fail，则丢弃，不进入 chosen；
7. 与 v2.1-clean / DPO-main / base 的失败轨迹配成 rejected。
```

输出：

```text
outputs/teacher_traces/dpo_v3/
outputs/teacher_traces/dpo_v3_success_only/
```

---

# 6. 数据审计要求

## 6.1 Clean eval audit

新增：

```text
docs/clean_independent_eval_401_450_audit.md
data/clean_independent_eval_401_450_audit.json
```

必须检查：

```text
bugfix_401-450 不在 SFT；
bugfix_401-450 不在 r2e；
bugfix_401-450 不在 DPO-sanity；
bugfix_401-450 不在 DPO-main；
bugfix_401-450 不在 DPO-main-v2；
bugfix_401-450 不在 DPO-main-v3；
bugfix_401-450 不在 teacher/mimo trace generation；
bugfix_401-450 不在 old28；
bugfix_401-450 不在 New50；
bugfix_401-450 不在 New100；
bugfix_401-450 不在 bugfix_351-400；
prompt 不包含答案；
任务内容与 bugfix_001-400 不高度相似。
```

---

## 6.2 DPO-main-v3 audit

必须输出：

```text
total_pairs
pair_type_distribution
failure_type_distribution
bug_type_distribution
difficulty_distribution
source_distribution
chosen_source_distribution
rejected_source_distribution
chosen_success_rate
rejected_success_rate
chosen_patch_apply_rate
rejected_patch_apply_rate
format_parse_rate
tool_valid_rate
new50_overlap
new100_source_count
bugfix_351_400_source_count
bugfix_401_450_overlap
old28_overlap
unknown_task_count
```

硬性通过标准：

```text
bugfix_401_450_overlap = 0
chosen_success_rate >= 95%
rejected_success_rate <= 5%
chosen_patch_apply_rate >= 95%
format_parse_rate >= 95%
UNKNOWN pair_type <= 5%
FORMAT_ERROR <= 10
WRONG_PATCH + TEST_STILL_FAIL >= 90
TEST_FEEDBACK_CORRECTION >= 35
PATCH_APPLY_STABILITY >= 35
```

---

# 7. 本阶段最终产物

本阶段结束时，仓库中应新增或更新：

```text
benchmark/tasks/bugfix_401-450/
benchmark/splits/dpo_independent_eval_401_450.txt

data/dpo_patch_correctness_v3_pairs.jsonl
data/dpo_patch_correctness_v3_audit.json
data/clean_independent_eval_401_450_audit.json

docs/dpo_patch_correctness_v3_audit.md
docs/clean_independent_eval_401_450_audit.md
docs/phase6_4_data_construction_summary.md
```

可选：

```text
outputs/teacher_traces/dpo_v3_success_only/
docs/teacher_trace_generation_dpo_v3.md
```

---

# 8. 验收标准

本阶段完成的标准不是训练成功率，而是数据是否干净。

必须满足：

```text
1. bugfix_401-450 已构建完成，共 50 tasks；
2. bugfix_401-450 有独立 split 文件；
3. bugfix_401-450 没有进入任何训练数据；
4. DPO-main-v3 pairs 达到 220-300；
5. DPO-main-v3 中 bugfix_401_450_overlap = 0；
6. WRONG_PATCH / TEST_STILL_FAIL / TEST_FEEDBACK / PATCH_STABILITY 是主体；
7. FORMAT_ERROR 不再主导；
8. chosen 全部或几乎全部为成功轨迹；
9. audit 报告完整；
10. 下一阶段可以直接训练 DPO-main-v3。
```

---

# 9. 给开发 agent 的最终执行指令

请开发 agent 只做数据构建，不做训练：

```text
1. 将 bugfix_351-400 标记为 contaminated/reference eval，不再称为 clean independent eval。
2. 构建新的 bugfix_401-450，共 50 个任务，作为 clean DPO-independent eval。
3. 任务难度分布建议：easy 8、medium 27、hard 15。
4. 覆盖 wrong_patch、test_feedback、patch_apply_stability、multi_file、path_normalization、regex、type_conversion、none_handling、nested_condition 等 bug 类型。
5. 新建 benchmark/splits/dpo_independent_eval_401_450.txt。
6. 禁止 bugfix_401-450 进入任何 DPO pair、teacher/mimo trace、SFT/r2e 数据。
7. 使用 train split、New100 reference、bugfix_351-400 reference、mimo/7B/teacher 成功轨迹构建 DPO-main-v3 pairs。
8. 目标总量 220-300 pairs。
9. 重点补 WRONG_PATCH / TEST_STILL_FAIL、TEST_FEEDBACK_CORRECTION、PATCH_APPLY_STABILITY。
10. FORMAT_ERROR <= 10，NO_EDIT 只少量保留。
11. 输出 data/dpo_patch_correctness_v3_pairs.jsonl。
12. 输出 data/dpo_patch_correctness_v3_audit.json 和 docs/dpo_patch_correctness_v3_audit.md。
13. 输出 clean independent eval audit，确认 bugfix_401-450 没有任何训练重叠。
14. 本阶段不要训练 DPO-main-v3，不要评测，不要做 GRPO。
```

---

# 10. 最终判断

现在确实需要构建新的数据，但要分清两类：

```text
1. 新的 clean independent eval：bugfix_401-450；
2. 新的 DPO-main-v3 training pairs：220-300 pairs。
```

最关键的是：

```text
bugfix_401-450 只能评测，绝不能用于训练。
```

如果这个数据边界重新建立好，下一步 DPO-main-v3 才有可信结论。否则继续训练和评测都会混在一起，结果很难解释。

# M-code Phase 6.3：Patch-Correctness 数据补强、独立评测与 DPO-main-v2 规划

> 用途：交给开发 agent 执行。  
> 当前阶段：Phase 6.2 已完成，DPO-sanity / DPO-main 已证明 DPO 可以改变模型行为并带来小幅收益。  
> 当前结果：DPO-main 在 180 tasks 上从 v2.1-clean 的 73.9% 提升到 75.0%，TEST_STILL_FAIL 从 29 降到 26，PATCH_APPLY_ERROR 从 18 升到 19。  
> 当前判断：DPO-main 不是失败，但提升有限。现有 108 pairs 不足以真正解决 Patch-Correctness。下一步应进入 Phase 6.3：先做 DPO-main 失败/回归分析，再补 WRONG_PATCH / TEST_FEEDBACK / PATCH_APPLY_STABILITY pairs，同时构建 bugfix_351-400 独立评测集，最后从 v2.1-clean 重新训练 DPO-main-v2。

---

## 0. 当前项目技术路线回顾

当前 M-code / EvoCode-Agent 已经形成完整的 Agentic Coding 后训练路线：

```text
trajectory-level SFT 失败 (36%)
  → step-level SFT v2 (held-out 54%)
  → failure analysis: NO_EDIT/read-file loop
  → read-to-edit transition SFT v2.1
  → 数据泄漏审计 + 数据管线修复
  → v2.1-clean (New50: 98%, New100: 66%)
  → DPO-sanity 108 pairs (Combined: 78%, NO_EDIT 归零)
  → DPO-main 108 pairs (180 tasks: 75.0%)
```

当前最重要的项目价值不是单一指标，而是这条闭环：

```text
发现训练失败
→ 做失败分析
→ 修训练目标
→ 审计数据泄漏
→ 重构数据管线
→ 复验 held-out
→ 用 DPO 做偏好优化
→ 再分析 DPO 副作用
```

这条路线已经可以支撑一个完整的 Agentic Coding 后训练项目。

---

## 1. 当前结果与阶段判断

### 1.1 已有核心结果

#### New50 easy held-out

| 模型 | Success |
|---|---:|
| 3B Base | 46% |
| 3B SFT v2 | 54% |
| 7B Base | 82% |
| **3B v2.1-clean** | **98%** |

#### 180 tasks：New50 + New100 + independent

| 模型 | Success | TEST_STILL_FAIL | PATCH_APPLY_ERROR |
|---|---:|---:|---:|
| v2.1-clean | 73.9% | 29 | 18 |
| **DPO-main** | **75.0%** | 26 | 19 |

### 1.2 当前正确解读

DPO-main 结果应当这样定性：

```text
DPO-main 有正向效果，但还不是强结果。
```

正向点：

```text
1. Success +1.1%；
2. TEST_STILL_FAIL 从 29 降到 26；
3. DPO 没有造成明显整体退化；
4. 说明 preference learning 路线可继续推进。
```

不足点：

```text
1. Success 提升太小；
2. PATCH_APPLY_ERROR 没有下降，反而从 18 到 19；
3. 说明 patch apply stability 没有真正解决；
4. 现有 DPO pairs 中 WRONG_PATCH / TEST_FEEDBACK / PATCH_STABILITY 信号仍然不够。
```

因此当前结论不是：

```text
DPO 已经显著提升 patch correctness。
```

而是：

```text
DPO pipeline 已经验证可行，但需要更聚焦的 patch-correctness 数据补强。
```

---

## 2. 当前主要瓶颈

当前瓶颈已经非常明确：

```text
模型已经敢改，NO_EDIT 不再是主要问题；
但 harder bugs 下 patch correctness 不够；
且 patch apply stability 仍未明显改善。
```

可以拆成四个子问题：

```text
1. WRONG_PATCH / TEST_STILL_FAIL pairs 不够；
2. TEST_FEEDBACK_CORRECTION pairs 不够；
3. PATCH_APPLY_STABILITY pairs 不够；
4. 缺少完全独立的 DPO-independent eval 来验证 DPO 是否泛化。
```

当前不建议继续做：

```text
1. 继续堆 FORMAT_ERROR pairs；
2. 继续堆 NO_EDIT pairs；
3. 直接用当前 108 pairs 反复 DPO；
4. 直接上 GRPO-lite；
5. 把 DPO-main 的 +1.1% 写成显著提升。
```

---

# 3. Phase 6.3 总目标

本阶段名称：

```text
Phase 6.3: Patch-Correctness Data Expansion, Independent Evaluation and DPO-main-v2
```

核心目标：

```text
1. 分析 DPO-main 180 tasks 中的失败和回归；
2. 明确 DPO-main 到底修好了哪些任务、改坏了哪些任务；
3. 从失败中提取新的数据需求；
4. 补充 100-150 对高质量 Patch-Correctness DPO pairs；
5. 构建 bugfix_351-400 作为 DPO-independent eval；
6. 从 v2.1-clean 重新训练 DPO-main-v2；
7. 在 New50 / New100 reference / DPO-independent eval 上复验；
8. 判断 DPO 是否真正提升 patch correctness。
```

本阶段的重点不是再证明 DPO 能不能跑，而是证明：

```text
DPO 能否在独立评测集上提升 patch correctness，并且不恶化 patch apply stability。
```

---

# 4. 执行路线总览

请开发 agent 按以下顺序执行：

```text
Step 1：DPO-main 失败与回归分析
Step 2：将失败分析转化为数据需求
Step 3：补充 100-150 对高质量 Patch-Correctness pairs
Step 4：构建 bugfix_351-400 DPO-independent eval
Step 5：生成 dpo_patch_correctness_v2_pairs.jsonl
Step 6：从 v2.1-clean 重新训练 DPO-main-v2
Step 7：三套评测：New50 / New100 reference / DPO-independent eval
Step 8：结果解释与是否进入下一阶段
```

---

# Step 1：DPO-main 失败与回归分析

## 1.1 目标

当前 DPO-main 只提升了 +1.1%，必须先搞清楚：

```text
1. DPO-main 修好了哪些 v2.1-clean 失败任务？
2. DPO-main 改坏了哪些 v2.1-clean 成功任务？
3. DPO-main 仍然失败的任务主要是什么类型？
4. TEST_STILL_FAIL 下降的 3 个任务有什么共性？
5. PATCH_APPLY_ERROR 为什么没有下降？
```

不要在没有失败分析的情况下继续扩数据。

## 1.2 输入

根据项目实际路径读取：

```text
outputs/rollouts/v21_clean_180/
outputs/rollouts/dpo_main_180/
outputs/reports/v21_clean_180_eval_summary.json
outputs/reports/dpo_main_180_eval_summary.json
outputs/reports/dpo_main_failure_analysis.json
```

如果当前路径不同，请按实际 outputs 命名调整。

## 1.3 输出

新增：

```text
docs/dpo_main_failure_and_regression_analysis.md
data/dpo_main_failure_and_regression_analysis.json
```

## 1.4 必须统计的四类任务

按 v2.1-clean 与 DPO-main 的结果，将 180 tasks 分成四组：

| 类别 | 说明 | 作用 |
|---|---|---|
| both_success | v2.1-clean 成功，DPO-main 也成功 | 稳定能力 |
| fixed_by_dpo | v2.1-clean 失败，DPO-main 成功 | DPO 有效样本 |
| regressed_by_dpo | v2.1-clean 成功，DPO-main 失败 | DPO 副作用 |
| both_fail | v2.1-clean 失败，DPO-main 也失败 | 下一步数据来源 |

必须输出：

```text
both_success count
fixed_by_dpo count
regressed_by_dpo count
both_fail count
```

尤其要关注：

```text
fixed_by_dpo 的共同点；
regressed_by_dpo 的共同点；
both_fail 里的主要 failure type。
```

## 1.5 每个失败样本记录字段

```json
{
  "task_id": "bugfix_xxx",
  "benchmark": "new50|new100|independent",
  "bug_type": "regex|type_conversion|...",
  "difficulty": "easy|medium|hard",
  "v21_clean_success": false,
  "dpo_main_success": false,
  "transition_type": "both_fail",
  "failure_type": "TEST_STILL_FAIL",
  "action_sequence": ["read_file", "edit_file", "run_tests"],
  "patch_apply_success": true,
  "test_output_summary": "...",
  "patch_size": 4,
  "edited_files": ["..."],
  "suspected_reason": "under_edit|wrong_condition|missed_edge_case|test_feedback_ignored|wrong_file|patch_apply_instability",
  "recommended_pair_type": "test_feedback_correction"
}
```

---

# Step 2：将失败分析转化为数据需求

## 2.1 输出数据需求表

根据 Step 1 的分析，输出：

```text
docs/dpo_main_data_gap_report.md
data/dpo_main_data_gap_report.json
```

报告中必须包含类似表格：

| 失败类型 | 数量 | 典型原因 | 需要补的数据 |
|---|---:|---|---|
| TEST_STILL_FAIL | N | patch 逻辑不完整 | correct patch vs wrong patch |
| WRONG_PATCH | N | 条件/边界错 | wrong patch pair |
| PATCH_APPLY_ERROR | N | old_text 不匹配 | patch apply stability |
| UNDER_EDIT | N | 只改一部分 | complete fix vs partial fix |
| OVER_EDIT | N | 改太多 | minimal patch vs over-edit |
| TEST_FEEDBACK_IGNORED | N | 没根据测试修 | test-feedback correction |
| REGRESSION | N | DPO 改坏原成功任务 | preserve-success pair |

## 2.2 推荐 pair_type

本阶段重点补以下 pair_type：

```text
wrong_patch
test_still_fail
test_feedback_correction
patch_apply_stability
minimal_patch
under_edit
over_edit
preserve_success
```

其中最重要的是：

```text
wrong_patch
test_feedback_correction
patch_apply_stability
```

## 2.3 不再重点补的数据

不要继续大量补：

```text
FORMAT_ERROR
NO_EDIT
generic tool valid
```

原因：

```text
当前主要问题不是不行动，也不是格式不合法；
而是行动之后 patch 不够正确或不够稳定。
```

---

# Step 3：补充 100-150 对高质量 Patch-Correctness pairs

## 3.1 总体目标

新增：

```text
100-150 high-quality Patch-Correctness pairs
```

使 DPO-main-v2 数据总量达到：

```text
220-280 pairs
```

不要盲目追 500 或 1000。

## 3.2 推荐新增数据组成

| Pair 类型 | 新增数量目标 | 说明 |
|---|---:|---|
| WRONG_PATCH / TEST_STILL_FAIL | 50-70 | 主体 |
| TEST_FEEDBACK_CORRECTION | 20-30 | 学会根据测试失败修正 |
| PATCH_APPLY_STABILITY | 20-30 | 降低 patch apply error |
| MINIMAL_PATCH vs OVER_EDIT | 10-20 | 控制 patch size 和副作用 |
| PRESERVE_SUCCESS | 5-10 | 防止 DPO 改坏原成功任务 |
| residual NO_EDIT | 0-5 | 只少量保留 |
| FORMAT_ERROR | 0-5 | 不再重点扩 |

## 3.3 数据来源优先级

优先级 1：same-task teacher pair

```text
chosen = teacher / 7B / mimo 成功轨迹
rejected = v2.1-clean / DPO-main 失败轨迹
```

优先级 2：fixed_by_dpo / regressed_by_dpo 对比

```text
fixed_by_dpo：可提取 DPO 有效模式；
regressed_by_dpo：可构造 preserve_success / anti-regression pair。
```

优先级 3：same bug_type pair

```text
同 bug_type 下，成功轨迹 vs 错误 patch 轨迹。
```

优先级 4：test-feedback trajectory

```text
run_tests fail 后，teacher 成功修正的轨迹。
```

优先级 5：人工修复 PATCH_APPLY_ERROR

```text
把 patch apply error 的 rejected action 手动或脚本修正为可应用 chosen action。
```

## 3.4 pair 字段格式

每条 pair 建议包含：

```json
{
  "pair_id": "bugfix_xxx_wrong_patch_001",
  "task_id": "bugfix_xxx",
  "bug_type": "...",
  "difficulty": "...",
  "pair_type": "wrong_patch",
  "source": "teacher_vs_dpo_main_failure",
  "chosen": "...",
  "rejected": "...",
  "chosen_success": true,
  "rejected_success": false,
  "chosen_patch_apply": true,
  "rejected_patch_apply": true,
  "failure_type": "TEST_STILL_FAIL",
  "source_trace_chosen": "...",
  "source_trace_rejected": "...",
  "eval_excluded": true
}
```

## 3.5 数据质量要求

必须满足：

```text
chosen success = true
rejected success = false
chosen/rejected 格式可 parse
chosen/rejected 使用同一套 prompt/action schema
chosen patch_apply = true
rejected 不一定 patch_apply=false；WRONG_PATCH 通常 patch_apply=true 但 tests fail
pair_type 明确，不能大量 UNKNOWN
```

---

# Step 4：构建 bugfix_351-400 DPO-independent eval

## 4.1 为什么必须做

当前 DPO 数据已经使用 New100 failure pairs。  
因此 DPO 后的 New100 只能作为：

```text
reference eval
```

不能作为完全干净的泛化证明。

Phase 6.3 必须构建独立评测集：

```text
bugfix_351-400
```

## 4.2 任务数量

建议：

```text
50 tasks
```

命名：

```text
bugfix_351
...
bugfix_400
```

## 4.3 任务类型设计

任务应重点覆盖当前 DPO 相关失败类型：

```text
wrong patch
test feedback correction
patch apply stability
indentation-sensitive edit
multi-file path
path normalization
regex parsing
date/time parsing
type conversion
none handling
nested condition
stateful logic
edge case handling
exception handling
list/dict mutation
```

## 4.4 难度分布

建议：

| 难度 | 数量 |
|---|---:|
| easy | 10 |
| medium | 25 |
| hard | 15 |

不要让 independent eval 过于简单，否则无法体现 DPO-main-v2 的价值。

## 4.5 泄漏审计

新增：

```text
eval/audit_dpo_independent_eval.py
docs/dpo_independent_eval_leakage_audit.md
data/dpo_independent_eval_leakage_audit.json
```

必须确认：

```text
不在 SFT train；
不在 r2e clean；
不在 DPO-sanity；
不在 DPO-main；
不在 dpo_patch_correctness_v2_pairs；
不在 New50；
不在 New100；
不在 old28；
不在 teacher training traces；
不与已有 task prompt/solution 高相似。
```

---

# Step 5：生成 DPO-main-v2 数据集

## 5.1 输出文件

```text
data/dpo_patch_correctness_v2_pairs.jsonl
data/dpo_patch_correctness_v2_audit.json
docs/dpo_patch_correctness_v2_audit.md
```

## 5.2 数据量

目标：

```text
220-280 pairs
```

不要为了数量硬塞低质量 pairs。

## 5.3 推荐最终组成

| Pair 类型 | 数量目标 | 占比 |
|---|---:|---:|
| WRONG_PATCH / TEST_STILL_FAIL | 80-100 | 主体 |
| TEST_FEEDBACK_CORRECTION | 30-40 | 关键 |
| PATCH_APPLY_STABILITY | 30-50 | 关键 |
| MINIMAL_PATCH / OVER_EDIT | 15-25 | 辅助 |
| PRESERVE_SUCCESS / anti-regression | 10-20 | 防回归 |
| residual NO_EDIT | 5-10 | 少量 |
| FORMAT_ERROR | <=10 | 少量 |

## 5.4 审计指标

audit 必须包含：

```text
total_pairs
pair_type_distribution
failure_type_distribution
bug_type_distribution
difficulty_distribution
chosen_success_rate
rejected_success_rate
chosen_patch_apply_rate
rejected_patch_apply_rate
format_parse_rate
tool_valid_rate
eval_overlap
new50_overlap
new100_source_count
independent_eval_overlap
old28_overlap
train_split_source_count
unknown_pair_count
```

## 5.5 通过标准

只有满足以下条件才进入训练：

```text
total_pairs >= 220
WRONG_PATCH + TEST_STILL_FAIL >= 80
TEST_FEEDBACK_CORRECTION >= 30
PATCH_APPLY_STABILITY >= 30
FORMAT_ERROR <= 10
UNKNOWN <= 5%
independent_eval_overlap = 0
chosen_success_rate >= 95%
rejected_success_rate <= 5%
chosen_patch_apply_rate >= 95%
format_parse_rate >= 95%
```

---

# Step 6：训练 DPO-main-v2

## 6.1 从哪个模型开始

推荐：

```text
从 v2.1-clean adapter 重新训练。
```

不要从当前 DPO-main 继续训练。

原因：

```text
当前 DPO-main 提升有限；
可能已经引入一些偏移；
DPO-main-v2 数据会重新平衡，应从干净 v2.1-clean adapter 开始。
```

## 6.2 训练脚本

建议新增或复用：

```text
training/train_dpo_patch_correctness_v2.py
```

输出：

```text
models/3b_v21_clean_dpo_patch_v2/
outputs/reports/train_dpo_patch_correctness_v2_log.md
```

## 6.3 训练参数

第一组推荐：

```yaml
method: DPO + LoRA continuation
base_adapter: 3B v2.1-clean
data: data/dpo_patch_correctness_v2_pairs.jsonl
learning_rate: 1e-6
epochs: 1
beta: 0.1
max_length: 4096
max_prompt_length: 3072
warmup_ratio: 0.03
```

如果第一组效果太弱，再做第二组：

```yaml
learning_rate: 2e-6
epochs: 1
beta: 0.1
```

不要一开始使用：

```text
5e-6
多 epoch
从 DPO-main 继续训
```

## 6.4 训练监控

必须记录：

```text
DPO loss
chosen reward
rejected reward
reward margin
grad norm
KL-like drift proxy
format parse rate on sample generations
tool valid rate on sample generations
```

---

# Step 7：DPO-main-v2 评测

## 7.1 必评模型

```text
3B Base
3B v2.1-clean
3B DPO-sanity
3B DPO-main
3B DPO-main-v2
7B Base
```

## 7.2 必评集合

```text
New50 easy
New100 reference
bugfix_351-400 independent eval
180 combined
```

如果 180 combined 包含 independent eval，需要在报告里明确组成。

## 7.3 必评指标

```text
Success
JSON Parse
Tool Valid
NO_EDIT
TEST_STILL_FAIL
PATCH_APPLY_ERROR
NO_TEST_AFTER_EDIT
PREMATURE_SUBMIT
Avg Steps
Patch size
Per bug type success
Per difficulty success
Regression count
Fixed-by-DPO count
```

## 7.4 输出报告

```text
docs/dpo_patch_correctness_v2_results.md
data/dpo_patch_correctness_v2_results.json
```

报告必须包含：

```text
主结果表
failure type 变化表
fixed/regressed 任务表
independent eval 结果
New50 不退化检查
New100 reference 结果
是否达到 Phase 6.3 成功标准
```

---

# Step 8：成功标准

## 8.1 New50

目标：

```text
保持 >= 96%
```

因为 v2.1-clean 已经 New50 98%，这里主要检查不退化。

## 8.2 New100 reference

目标：

```text
当前 DPO-main 75.0% reference/combined 水平
DPO-main-v2 应达到 77%-80% 左右
```

注意：如果 New100 参与 DPO 数据构造，则 New100 只能作为 reference。

## 8.3 bugfix_351-400 independent eval

这是最重要的判断。

目标：

```text
DPO-main-v2 > v2.1-clean
```

哪怕只提升：

```text
+3% 到 +5%
```

也比 New100 reference 提升更有价值。

## 8.4 Failure 指标

目标：

```text
TEST_STILL_FAIL 下降；
PATCH_APPLY_ERROR 不高于 v2.1-clean，最好下降；
NO_EDIT 不反弹；
FORMAT_ERROR 不反弹；
regression count 不增加。
```

## 8.5 最终成功定义

Phase 6.3 成功需要满足：

```text
1. independent eval 上 DPO-main-v2 优于 v2.1-clean；
2. New50 不明显退化；
3. TEST_STILL_FAIL 明显下降；
4. PATCH_APPLY_ERROR 不恶化；
5. NO_EDIT 不反弹；
6. 数据审计无 independent eval leakage。
```

---

# Step 9：结果解释规则

## 9.1 强成功

如果：

```text
independent eval +5% 以上；
New100 reference 提升；
TEST_STILL_FAIL 下降；
PATCH_APPLY_ERROR 下降或持平；
New50 >=96%；
```

结论：

```text
Patch-Correctness DPO-main-v2 有效，并且具备一定泛化能力。
```

## 9.2 中等成功

如果：

```text
independent eval +2% 到 +5%；
patch apply 不恶化；
NO_EDIT 不反弹；
```

结论：

```text
DPO-main-v2 有轻微但可信收益，后续可继续补数据或做 Skill Self-Distillation。
```

## 9.3 中性

如果：

```text
independent eval 不变；
但 PATCH_APPLY_ERROR 下降；
TEST_STILL_FAIL 下降；
```

也不算失败，因为模型行为更健康。下一步继续补 WRONG_PATCH / TEST_FEEDBACK。

## 9.4 失败

如果：

```text
independent eval 下降；
New50 下降；
PATCH_APPLY_ERROR 上升；
NO_EDIT 反弹；
```

不要继续 DPO。回查：

```text
pair 构造质量；
chosen/rejected 是否反；
LR 是否过高；
prompt/action schema 是否一致；
数据是否引入 FORMAT_ERROR/NO_EDIT 偏置；
是否应该做 Skill Self-Distillation 而不是继续 DPO。
```

---

# 10. GRPO-lite 与 Skill Self-Distillation 的位置

## 10.1 GRPO-lite 暂缓

当前不建议直接进入 GRPO-lite。

原因：

```text
1. 当前 patch correctness 数据仍然不足；
2. DPO-main-v2 还没验证；
3. RL 会放大 reward 设计问题；
4. 当前 benchmark 规模仍小，GRPO 容易过拟合。
```

只有当满足以下条件再考虑：

```text
DPO-main-v2 在 independent eval 上提升有限；
failure 类型仍集中；
reward 可稳定定义；
rollout 成本可控；
有足够 hard tasks 支撑。
```

## 10.2 Skill Self-Distillation 作为后备路线

如果 DPO-main-v2 提升有限，可以做 Skill Self-Distillation：

```text
从成功轨迹总结 reusable skills：
- regex 修复模式
- type conversion 修复模式
- none handling 修复模式
- off-by-one 修复模式
- patch apply stability skill
- test feedback correction skill
```

用途：

```text
1. 作为报告中的能力解释；
2. 作为 prompt-side skill library；
3. 作为后续 SFT/DPO 数据增强来源；
4. 作为 GRPO 前的结构化先验。
```

但它不是当前第一优先级。

---

# 11. 给开发 agent 的最终执行指令

请开发 agent 按以下步骤执行：

```text
1. 对 DPO-main 在 180 tasks 上的结果做 failure/regression analysis。
2. 输出 docs/dpo_main_failure_and_regression_analysis.md 和 data/dpo_main_failure_and_regression_analysis.json。
3. 将任务分成 both_success、fixed_by_dpo、regressed_by_dpo、both_fail 四类。
4. 分析 TEST_STILL_FAIL、PATCH_APPLY_ERROR、UNDER_EDIT、OVER_EDIT、TEST_FEEDBACK_IGNORED、REGRESSION。
5. 输出 docs/dpo_main_data_gap_report.md，明确下一步缺哪些 pair。
6. 补充 100-150 对高质量 Patch-Correctness pairs，重点是 WRONG_PATCH、TEST_FEEDBACK_CORRECTION、PATCH_APPLY_STABILITY。
7. 构建 bugfix_351-400 作为 DPO-independent eval，完成泄漏审计。
8. 生成 data/dpo_patch_correctness_v2_pairs.jsonl，总量目标 220-280。
9. 生成 docs/dpo_patch_correctness_v2_audit.md，确认 independent_eval_overlap=0。
10. 从 v2.1-clean adapter 重新训练 DPO-main-v2，不从当前 DPO-main 继续训练。
11. 训练参数先用 lr=1e-6、epoch=1、beta=0.1。
12. 评测 New50、New100 reference、bugfix_351-400 independent、180 combined。
13. 输出 docs/dpo_patch_correctness_v2_results.md。
14. 若 independent eval 有提升、patch apply 不恶化、NO_EDIT 不反弹，则记录为 Phase 6.3 成果。
15. 在 DPO-main-v2 结果出来前，不要做 GRPO-lite。
```

---

# 12. 最终判断

当前项目已经进入比较成熟的阶段。

DPO-main 当前结果：

```text
75.0% vs 73.9%，+1.1%
TEST_STILL_FAIL 下降 3
PATCH_APPLY_ERROR 基本持平
```

说明：

```text
DPO 有用，但当前数据还不够强。
```

下一步不应该急着换大方向，而是把 DPO 做扎实：

```text
DPO-main failure analysis
→ 数据缺口定位
→ 补 WRONG_PATCH / TEST_FEEDBACK / PATCH_STABILITY
→ independent eval
→ DPO-main-v2
```

如果 Phase 6.3 能在 independent eval 上取得正提升，并且不恶化 PATCH_APPLY_ERROR，那么 M-code 的第三阶段训练闭环就非常完整：

```text
SFT 学工具协议
→ read-to-edit SFT 学行动转换
→ DPO 学 patch correctness
→ independent eval 验证泛化
```

这条路线比现在立刻上 GRPO 更稳，也更适合写进项目总结和简历。

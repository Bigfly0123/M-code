# M-code Phase 6.2：DPO-sanity 副作用分析与 Patch-Apply 稳定性修复规划

> 用途：交给开发 agent 执行。  
> 当前阶段：DPO-sanity 已完成，108 pairs 训练后 Combined Success 从 115/150 提升到 117/150，NO_EDIT 从 11 降到 0。  
> 当前问题：DPO-sanity 证明 DPO 能改变模型行为，但带来明显副作用：PATCH_APPLY_ERROR 从 0 增加到 14。  
> 本阶段目标：不要立刻扩大 DPO-main，也不要马上上 GRPO。先分析 PATCH_APPLY_ERROR 来源，构造 Patch-Apply Stability pairs，修复“更敢 edit 但 patch 不稳定”的问题，再进入正式 DPO-main。

---

## 1. 当前阶段结果回顾

### 1.1 DPO-sanity 前后对比

| 指标 | v2.1-clean | DPO-sanity | 变化 | 判断 |
|---|---:|---:|---:|---|
| Success | 115/150 | 117/150 | +2 | 小幅提升 |
| NO_EDIT | 11 | 0 | -11 | 明显改善 |
| PREMATURE_SUBMIT | 2 | 0 | -2 | 改善 |
| TEST_STILL_FAIL | 22 | 19 | -3 | 小幅改善 |
| PATCH_APPLY_ERROR | 0 | 14 | +14 | 明显副作用 |

### 1.2 当前正确结论

DPO-sanity 不是失败。它完成了 sanity 阶段的核心任务：

```text
1. 证明 DPO pipeline 可以跑通；
2. 证明 DPO 能明显改变模型行为；
3. 证明模型更愿意 edit，NO_EDIT 归零；
4. 证明 premature submit 问题得到缓解；
5. 暴露了新的副作用：PATCH_APPLY_ERROR 暴涨。
```

当前应该这样定性：

```text
DPO-sanity 成功验证了偏好优化方向，但当前 DPO 信号把模型推向“更敢编辑”，尚未充分约束“edit_file 必须可应用、old_text 必须稳定匹配、patch 必须最小且正确”。因此下一步应先修复 Patch-Apply Stability，而不是直接扩大 DPO-main。
```

---

## 2. 当前主要瓶颈变化

### 2.1 v2.1-clean 之前的瓶颈

v2.1-clean 之前最大问题是：

```text
NO_EDIT / read_file loop
```

模型读到了目标文件，但不敢或不会进入 edit_file。

### 2.2 DPO-sanity 后的瓶颈

DPO-sanity 后 NO_EDIT 已经归零，说明模型“敢改”了。  
但新的问题是：

```text
PATCH_APPLY_ERROR 增加到 14
```

这说明模型现在更倾向于 edit，但 edit_file action 的稳定性下降。

当前瓶颈已经从：

```text
是否行动
```

变成：

```text
如何稳定、正确、可应用地行动
```

也就是：

```text
Patch-Apply Stability
Patch Correctness
Test Feedback Correction
```

---

## 3. 为什么 PATCH_APPLY_ERROR 会暴涨

### 3.1 DPO 信号可能强化了“赶快 edit”

sanity pairs 中包含 NO_EDIT、FORMAT_ERROR、NO_TEST_AFTER_EDIT 等类型，这会强化：

```text
不要犹豫，尽快 edit
```

但如果没有足够强化：

```text
old_text 必须精确匹配；
patch 必须最小；
路径必须正确；
缩进和换行必须保持；
edit 后必须 run_tests；
```

模型就可能从“不改”变成“乱改”。

### 3.2 WRONG_PATCH / PATCH_STABILITY pairs 不足

当前 WRONG_PATCH 类 pair 数量偏少。  
DPO-sanity 主要学习了“chosen 行动优于 rejected 不行动/格式错误”，但没有充分学习：

```text
可应用 patch 优于不可应用 patch；
正确 old_text 优于错误 old_text；
最小 edit 优于过长 edit；
根据 test output 修正优于重复错误。
```

### 3.3 edit_file 工具约束没有被偏好数据显式建模

PATCH_APPLY_ERROR 常见原因包括：

```text
old_text_not_found
indentation_mismatch
wrong_file
malformed_edit_json
overlong_old_text
quote_escape_error
line_context_mismatch
multi_file_path_error
```

这些需要专门的 Patch-Apply Stability 数据，而不是普通 correct-vs-wrong patch pair 就能解决。

---

# 4. Phase 6.2 核心目标

本阶段名称：

```text
Phase 6.2: DPO-sanity Side-effect Analysis and Patch-Apply Stability Repair
```

核心目标：

```text
1. 分析 DPO-sanity 产生的 14 个 PATCH_APPLY_ERROR；
2. 找出 patch apply 失败的具体原因；
3. 对比 v2.1-clean 与 DPO-sanity 在同一任务上的 action 差异；
4. 构造 Patch-Apply Stability DPO pairs；
5. 补充 WRONG_PATCH / TEST_STILL_FAIL pairs；
6. 重新平衡 DPO-main 数据；
7. 构建 DPO-independent eval；
8. 再训练 DPO-main。
```

本阶段不要做：

```text
1. 不要直接扩大 DPO-main；
2. 不要继续扩 FORMAT_ERROR；
3. 不要继续大量扩 NO_EDIT；
4. 不要立即上 GRPO；
5. 不要只看 Success，不看 PATCH_APPLY_ERROR。
```


---

# 5. 执行路线总览

请开发 agent 按以下顺序执行：

```text
Step 1：提取 DPO-sanity 的 14 个 PATCH_APPLY_ERROR 案例
Step 2：分类 PATCH_APPLY_ERROR 原因
Step 3：对比 v2.1-clean 与 DPO-sanity action 差异
Step 4：构造 PATCH_APPLY_STABILITY pairs
Step 5：补充 WRONG_PATCH / TEST_STILL_FAIL pairs
Step 6：重建 DPO-main 数据集
Step 7：构建 bugfix_351-400 DPO-independent eval
Step 8：训练 DPO-main
Step 9：三套评测：New50 / New100 reference / independent eval
Step 10：根据结果决定是否进入 DPO v2 或 GRPO-lite
```

---

# Step 1：提取 DPO-sanity 的 PATCH_APPLY_ERROR 案例

## 1.1 输入

需要从以下内容中读取：

```text
outputs/rollouts/dpo_sanity_combined/
outputs/reports/dpo_sanity_eval_summary.json
outputs/reports/dpo_sanity_failure_analysis.json
```

如果路径不同，请根据项目实际命名调整。

## 1.2 输出

新增：

```text
docs/dpo_sanity_patch_apply_error_analysis.md
data/dpo_sanity_patch_apply_error_analysis.json
```

## 1.3 每个案例记录字段

每个 PATCH_APPLY_ERROR 任务记录：

```json
{
  "task_id": "bugfix_xxx",
  "benchmark": "new50_or_new100",
  "bug_type": "...",
  "difficulty": "easy|medium|hard",
  "file_path": "...",
  "action_step": 3,
  "dpo_action": {
    "tool": "edit_file",
    "path": "...",
    "old_text": "...",
    "new_text": "..."
  },
  "error_message": "...",
  "error_type": "old_text_not_found",
  "was_success_before_dpo": true,
  "v21_clean_result": "success|fail",
  "v21_clean_action_sequence": ["read_file", "edit_file", "run_tests", "submit"],
  "dpo_sanity_action_sequence": ["read_file", "edit_file"],
  "initial_hypothesis": "DPO used overlong old_text not matching current file"
}
```

---

# Step 2：分类 PATCH_APPLY_ERROR 原因

## 2.1 error_type 分类

必须将 14 个 PATCH_APPLY_ERROR 归类为以下类型：

```text
old_text_not_found
indentation_mismatch
wrong_file
malformed_edit_json
overlong_old_text
quote_escape_error
line_context_mismatch
multi_file_path_error
duplicate_edit_on_changed_file
unknown
```

## 2.2 分类说明

### old_text_not_found

```text
edit_file 的 old_text 在目标文件中找不到。
```

常见原因：

```text
old_text 太长；
old_text 包含不稳定上下文；
模型改写了原代码；
读的是一个版本，edit 时假设另一个版本。
```

### indentation_mismatch

```text
old_text 内容基本对，但缩进、空格、换行不完全匹配。
```

### wrong_file

```text
模型 edit 的文件不是目标文件。
```

### malformed_edit_json

```text
edit_file 参数本身 JSON 不合法或字段缺失。
```

### overlong_old_text

```text
old_text 包含过多上下文，导致匹配失败。
```

### quote_escape_error

```text
字符串引号、反斜杠、换行转义错误导致 patch 无法应用。
```

### line_context_mismatch

```text
old_text 包含附近上下文，但上下文与文件实际内容不完全一致。
```

### duplicate_edit_on_changed_file

```text
模型已 edit 一次，后续又用旧 old_text 再 edit，导致匹配失败。
```

## 2.3 输出统计

在报告中输出：

| Error Type | Count | Typical Cause | Fix Direction |
|---|---:|---|---|
| old_text_not_found | N | old_text 不匹配 | use short exact old_text |
| indentation_mismatch | N | 缩进不一致 | preserve exact indentation |
| wrong_file | N | 文件定位错 | verify target path |
| malformed_edit_json | N | 工具格式错 | schema stability |
| overlong_old_text | N | old_text 太长 | minimal old_text |
| quote_escape_error | N | 转义错误 | robust string encoding |
| unknown | N | 未知 | manual review |


---

# Step 3：对比 v2.1-clean 与 DPO-sanity 的 action 差异

## 3.1 目的

如果某个任务：

```text
v2.1-clean 成功；
DPO-sanity PATCH_APPLY_ERROR；
```

这类样本非常重要。

它说明 DPO 改坏了原本成功的策略。

## 3.2 必须对比

对每个 PATCH_APPLY_ERROR 任务，比较：

```text
v2.1-clean action sequence
DPO-sanity action sequence
v2.1-clean edit_file old_text/new_text
DPO-sanity edit_file old_text/new_text
v2.1-clean 是否 run_tests
DPO-sanity 是否 run_tests
v2.1-clean patch size
DPO-sanity patch size
```

## 3.3 输出字段

```json
{
  "task_id": "bugfix_xxx",
  "v21_clean_success": true,
  "dpo_sanity_success": false,
  "regression": true,
  "v21_edit_style": "short_exact_old_text",
  "dpo_edit_style": "overlong_old_text",
  "difference_summary": "DPO used a longer old_text block with mismatched indentation."
}
```

## 3.4 目标

找出 DPO 产生 PATCH_APPLY_ERROR 的行为模式，例如：

```text
DPO old_text 更长；
DPO 更早 edit，缺少 read context；
DPO 修改了错误文件；
DPO edit 后没有 run_tests；
DPO 生成的 old_text 是 paraphrase，不是原文复制；
DPO 重复 edit 已改变的区域。
```

---

# Step 4：构造 PATCH_APPLY_STABILITY pairs

## 4.1 新 pair 类型

新增 pair_type：

```text
patch_apply_stability
```

## 4.2 pair 目标

让模型学会：

```text
edit_file 不是越早越好；
old_text 必须短、精确、可匹配；
new_text 必须保留缩进和格式；
文件路径必须正确；
如果已 edit，后续 edit 不能使用旧文件内容；
patch apply 成功后再 run_tests。
```

## 4.3 chosen / rejected 定义

### chosen

```text
read_file
→ edit_file with short exact old_text
→ patch applies successfully
→ run_tests
→ submit if pass
```

### rejected

```text
read_file
→ edit_file with old_text_not_found / indentation mismatch / wrong file / malformed edit
→ PATCH_APPLY_ERROR
```

## 4.4 数据来源

优先来源：

```text
1. v2.1-clean 成功但 DPO-sanity patch_apply_error 的同 task 对比；
2. teacher / 7B / mimo 成功轨迹 vs DPO-sanity patch_apply_error；
3. 人工修复 patch_apply_error 后构造 chosen；
4. 同 bug_type 下可应用 patch vs 不可应用 patch。
```

## 4.5 数量建议

构造：

```text
30-50 pairs
```

不要机械凑数，优先保证质量。

## 4.6 输出文件

```text
data/dpo_patch_apply_stability_pairs.jsonl
docs/dpo_patch_apply_stability_data_audit.md
```

## 4.7 每条样本字段

```json
{
  "pair_id": "bugfix_xxx_patch_apply_stability_001",
  "task_id": "bugfix_xxx",
  "bug_type": "...",
  "difficulty": "...",
  "pair_type": "patch_apply_stability",
  "error_type": "old_text_not_found",
  "chosen_source": "v21_clean_success",
  "rejected_source": "dpo_sanity_patch_apply_error",
  "chosen": "...",
  "rejected": "...",
  "chosen_patch_apply": true,
  "rejected_patch_apply": false,
  "source_trace_chosen": "...",
  "source_trace_rejected": "..."
}
```

---

# Step 5：补充 WRONG_PATCH / TEST_STILL_FAIL pairs

## 5.1 当前问题

DPO-sanity 降低了 NO_EDIT，但 TEST_STILL_FAIL 只从 22 降到 19，说明 patch correctness 信号仍然不够。

## 5.2 重点扩充类型

新增或补充：

```text
wrong_patch
test_still_fail
test_feedback_correction
under_edit
over_edit
```

## 5.3 数量建议

目标：

```text
TEST_STILL_FAIL / WRONG_PATCH pairs: 60-80
```

如果现有不足，则从以下来源补：

```text
1. New100 中 v2.1-clean 失败、7B/mimo 成功的同任务；
2. train split 中 teacher 成功、base/v2/v2.1 失败的任务；
3. 同 bug_type 的成功/失败轨迹；
4. run_tests fail 后 teacher 修正成功的轨迹。
```

## 5.4 test-feedback correction pair

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
→ repeat same edit / ignore test output / submit anyway
```

这类数据对 TEST_STILL_FAIL 很重要。


---

# Step 6：重建 DPO-main 数据集

## 6.1 新数据集名称

输出：

```text
data/dpo_main_patch_stable.jsonl
```

可保留旧数据：

```text
data/dpo_sanity_108.jsonl
data/dpo_main_pairs_expanded.jsonl
data/dpo_all_mixed_190.jsonl
```

## 6.2 推荐组成

| Pair 类型 | 数量建议 | 目的 |
|---|---:|---|
| TEST_STILL_FAIL / WRONG_PATCH | 60-80 | 提升 patch correctness |
| PATCH_APPLY_STABILITY | 30-50 | 降低 patch apply error |
| NO_TEST_AFTER_EDIT / test-feedback | 15-25 | 学会测试反馈修正 |
| residual NO_EDIT | 10-15 | 防止 NO_EDIT 反弹 |
| FORMAT_ERROR | 10-15 | 少量保留格式稳定 |
| 其他 | 少量 | 不主导 |

总量：

```text
150-220 pairs
```

不要为了数量硬塞低质量 FORMAT_ERROR。

## 6.3 目标分布

建议：

```text
FORMAT_ERROR <= 10%-12%
NO_EDIT <= 10%-15%
PATCH_APPLY_STABILITY >= 20%
TEST_STILL_FAIL / WRONG_PATCH >= 35%
OTHER/UNKNOWN <= 5%
```

---

# Step 7：构建 DPO-independent eval

## 7.1 为什么必须做

如果 DPO-main 使用 New100 failure pairs，那么 New100 不再是完全 clean 的 DPO 后泛化评测。

New100 可以继续作为：

```text
reference eval
```

但不能作为唯一结论。

## 7.2 新增任务

构建：

```text
bugfix_351-400
```

共 50 个任务。

输出：

```text
benchmark/tasks/bugfix_351-400/
benchmark/splits/dpo_independent_eval_tasks.txt
```

## 7.3 任务设计重点

重点覆盖 DPO 当前相关失败：

```text
patch apply stability
wrong patch
test feedback correction
multi-file path
indentation-sensitive edit
regex/date/type conversion
stateful logic
nested condition
```

## 7.4 审计

新增：

```text
eval/audit_dpo_independent_eval.py
docs/dpo_independent_eval_leakage_audit.md
```

必须确认：

```text
不在 SFT train；
不在 r2e clean；
不在 DPO-sanity；
不在 DPO-main；
不在 New50/New100；
不在 old28；
不在 teacher training traces。
```

---

# Step 8：DPO-main 训练

## 8.1 前置条件

只有满足以下条件才训练 DPO-main：

```text
14 个 PATCH_APPLY_ERROR 已分析；
PATCH_APPLY_STABILITY pairs >= 30；
TEST_STILL_FAIL / WRONG_PATCH pairs >= 60；
FORMAT_ERROR <= 12%-15%；
OTHER/UNKNOWN <= 5%-8%；
DPO-independent eval 已构建或至少已规划并排除污染；
```

## 8.2 训练输入

```text
data/dpo_main_patch_stable.jsonl
```

## 8.3 模型

推荐：

```text
从 v2.1-clean 重新开始训练 DPO-main。
```

不要从 DPO-sanity 继续训练。

原因：

```text
DPO-sanity 已经暴露 PATCH_APPLY_ERROR 副作用；
main 数据已修正，应该从干净 v2.1-clean adapter 开始。
```

## 8.4 训练参数

```yaml
method: DPO + LoRA continuation
base_adapter: 3B v2.1-clean
learning_rate: 1e-6 to 3e-6
epochs: 1
beta: 0.1
max_length: 4096
max_prompt_length: 3072
warmup_ratio: 0.03
```

优先用：

```text
learning_rate = 1e-6
```

如果效果太弱，再尝试：

```text
2e-6 或 3e-6
```

不要一开始用 5e-6。

---

# Step 9：DPO-main 评测

## 9.1 必评集合

```text
New50 easy
New100 reference
DPO-independent eval bugfix_351-400
```

## 9.2 必评模型

```text
3B Base
3B v2.1-clean
3B DPO-sanity
3B DPO-main-patch-stable
7B Base
```

## 9.3 必评指标

```text
Success
NO_EDIT
TEST_STILL_FAIL
PATCH_APPLY_ERROR
PREMATURE_SUBMIT
NO_TEST_AFTER_EDIT
JSON Parse
Tool Valid
Avg Steps
Patch size
Per bug type success
```

## 9.4 成功标准

### New50

```text
保持 >= 96%
```

不能牺牲 easy set。

### New100 reference

```text
66% → 70%-75%
```

但 New100 只是 reference。

### DPO-independent eval

核心指标：

```text
DPO-main > v2.1-clean
PATCH_APPLY_ERROR 不高于 v2.1-clean
NO_EDIT 不明显反弹
TEST_STILL_FAIL 下降
```

### Patch apply stability

最关键：

```text
PATCH_APPLY_ERROR <= 5
```

如果 combined 上仍有很多 patch apply error，说明 DPO-main 仍不稳。


---

# Step 10：结果解释规则

## 10.1 好结果

如果：

```text
Success 提升；
NO_EDIT 保持低；
TEST_STILL_FAIL 降低；
PATCH_APPLY_ERROR 降到 <=5；
DPO-independent eval 有正提升；
```

结论：

```text
Patch-Correctness DPO 有效，且 Patch-Apply Stability pairs 成功抑制了 sanity 阶段副作用。
```

## 10.2 中性结果

如果：

```text
Success 没明显提升；
但 PATCH_APPLY_ERROR 从 14 降到 <=5；
NO_EDIT 仍低；
```

也算阶段有效，因为 DPO-main 修复了 DPO-sanity 副作用。

下一步再补 WRONG_PATCH / TEST_FEEDBACK。

## 10.3 坏结果

如果：

```text
NO_EDIT 反弹；
PATCH_APPLY_ERROR 仍高；
JSON/tool 下降；
New50 明显退化；
```

不要继续 DPO。回查：

```text
chosen/rejected 是否反了；
patch_apply_stability pairs 是否质量不够；
LR 是否太高；
FORMAT_ERROR 是否仍过多；
prompt 格式是否不一致；
edit_file action 是否和 runtime tool schema 对齐。
```

---

# 11. 给开发 agent 的最终执行指令

请开发 agent 按以下步骤执行：

```text
1. 提取 DPO-sanity 的 14 个 PATCH_APPLY_ERROR 案例。
2. 输出 docs/dpo_sanity_patch_apply_error_analysis.md 和 data/dpo_sanity_patch_apply_error_analysis.json。
3. 将 patch apply errors 分类为 old_text_not_found、indentation_mismatch、wrong_file、malformed_edit_json、overlong_old_text、quote_escape_error、line_context_mismatch、duplicate_edit_on_changed_file 等。
4. 对比 v2.1-clean 与 DPO-sanity 在这些任务上的 action 差异，找出 DPO 为什么把原本稳定的 edit 变成不可应用 patch。
5. 构造 30-50 对 PATCH_APPLY_STABILITY pairs，chosen 是可应用的短 old_text/minimal edit，rejected 是 patch apply error edit_file。
6. 补充 TEST_STILL_FAIL / WRONG_PATCH / test-feedback correction pairs，使其达到 60-80 对。
7. 重建 data/dpo_main_patch_stable.jsonl，总量 150-220 对，FORMAT_ERROR <= 10%-12%，NO_EDIT <= 10%-15%，OTHER/UNKNOWN <= 5%-8%。
8. 构建 bugfix_351-400 作为 DPO-independent eval，并完成泄漏审计。
9. 从 v2.1-clean adapter 重新训练 DPO-main，不从 DPO-sanity 继续训练。
10. 训练参数保守：lr=1e-6，epoch=1，beta=0.1。
11. 在 New50、New100 reference、DPO-independent eval 上评测。
12. 成功标准不是只看 success，而是同时要求 PATCH_APPLY_ERROR 降到 <=5、NO_EDIT 不反弹、TEST_STILL_FAIL 下降。
13. 在 DPO-main 结果出来前，不要做 GRPO。
```

---

# 12. 最终判断

当前 DPO-sanity 是一个好结果：

```text
Success +2；
NO_EDIT 归零；
PREMATURE_SUBMIT 归零；
TEST_STILL_FAIL 小降。
```

但它暴露了下一阶段必须解决的问题：

```text
PATCH_APPLY_ERROR +14。
```

因此 Phase 6.2 的正确目标不是“继续扩大 DPO 训练”，而是：

```text
修复 DPO 带来的 patch apply stability 副作用。
```

下一步主线应该是：

```text
分析 PATCH_APPLY_ERROR
→ 构造 PATCH_APPLY_STABILITY pairs
→ 补 WRONG_PATCH / TEST_STILL_FAIL pairs
→ 构建 independent eval
→ 从 v2.1-clean 重新训练 DPO-main
```

这样做，Phase 6 的结果才会稳，也更容易写进最终项目报告。

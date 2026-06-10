# M-code Phase 6.1：DPO 数据重审计、重分类与重平衡规划

> 用途：交给开发 agent 执行。  
> 当前状态：已构造 `dpo_main_pairs_expanded.jsonl`，共 190 对 DPO pairs，接近正式 DPO-main 的最低目标。  
> 当前判断：**暂时不需要继续大规模扩充数据**。现阶段目标不是继续堆数据，而是把现有 190 对重新审计、重分类、重平衡，拆成 DPO-sanity 和 DPO-main 两套可用数据。  
> 核心原则：**33 对/190 对都不能直接盲训。先审计，再重平衡，再 sanity，再 main。**

---

## 1. 当前 DPO 数据状态

### 1.1 已有数据

当前已生成：

```text
data/dpo_main_pairs_expanded.jsonl
```

共：

```text
190 pairs
```

来源分布：

| 来源 | 数量 | 说明 |
|---|---:|---|
| mimo same-task | 45 | mimo 成功 vs 失败，train-only |
| patch correctness | 33 | 7B 成功 vs v2.1-clean 失败，new100 |
| v2.1-clean vs 3B Base | 49 | v2.1 成功 vs base 失败，new100 |
| v2.1-clean vs v2 | 4 | v2.1 成功 vs v2 失败，new100 |
| rejected errors vs success | 59 | 训练任务失败轨迹配对，train-only |
| **合计** | **190** | 接近 200 目标 |

失败类型分布：

| Failure Type | 数量 | 占比 | 判断 |
|---|---:|---:|---|
| FORMAT_ERROR | 68 | 36% | 偏高，不应主导 Patch-Correctness DPO |
| TEST_STILL_FAIL | 45 | 24% | 关键目标类型 |
| NO_EDIT | 35 | 18% | 需要少量保留，防止反弹 |
| OTHER | 29 | 15% | 需要重新分类 |
| NO_TEST_AFTER_EDIT | 12 | 6% | 有价值，保留 |
| PATCH_APPLY_ERROR | 1 | 1% | 太少，保留但不作为主体 |

覆盖：

```text
29 种 bug 类型
```

Top 5：

```text
regex: 19
type_conversion: 18
none_handling: 15
off_by_one: 15
dict_key: 11
```

---

## 2. 当前核心判断

### 2.1 数量基本够，但结构还不够好

190 对已经接近 DPO-main 的数据量下限，不需要马上继续扩到 500 或 1000。  
当前更重要的问题是：

```text
数据目标是否对齐 Patch-Correctness DPO？
```

Phase 6 的目标是：

```text
让模型在 harder bugs 下不仅敢改，而且改得对。
```

也就是重点解决：

```text
TEST_STILL_FAIL
WRONG_PATCH
NO_TEST_AFTER_EDIT
PATCH_APPLY_ERROR
MISREAD_TEST_OUTPUT
UNDER_EDIT / OVER_EDIT
```

但当前数据中：

```text
FORMAT_ERROR = 36%
OTHER = 15%
```

这说明现有 190 对更像 mixed DPO dataset，而不是纯 Patch-Correctness DPO dataset。

---

### 2.2 暂时不需要扩数据

当前不建议继续扩数据，原因：

```text
1. 190 对已经接近正式 DPO-main 下限；
2. 当前瓶颈不是数量，而是 failure_type 分布不够聚焦；
3. FORMAT_ERROR 太多，会稀释 patch correctness 信号；
4. OTHER 过多，说明失败分类还不清晰；
5. 未完成重审计前继续扩，可能把数据污染和目标混乱放大。
```

当前最稳路线是：

```text
重审计 190
→ 重分类 OTHER
→ 降低 FORMAT_ERROR 占比
→ 生成 sanity / balanced main / all mixed 三套数据
→ 先做 DPO-sanity
→ sanity 通过后再做 DPO-main
```

---

## 3. 本阶段目标

本阶段名称：

```text
Phase 6.1: DPO Data Audit, Reclassification and Balancing
```

核心目标：

```text
1. 重新生成 190 对版本的 audit；
2. 拆分 overlap 字段，明确 New50 / New100 / old28 / independent eval 的关系；
3. 将 OTHER 尽量重新分类；
4. 控制 FORMAT_ERROR 占比；
5. 生成 DPO-sanity 数据集；
6. 生成 balanced Patch-Correctness DPO-main 数据集；
7. 保留 all-mixed-190 作为 ablation；
8. 暂不训练正式 DPO-main，先准备好数据与 sanity 方案。
```

---

# 4. 执行路线总览

请开发 agent 按以下顺序执行：

```text
Step 1：重新生成 190 对版本 audit
Step 2：拆分 heldout_leakage 字段
Step 3：重新分类 OTHER
Step 4：分析 FORMAT_ERROR 质量，限制其占比
Step 5：生成 dpo_sanity_pairs.jsonl
Step 6：生成 dpo_patch_main_balanced.jsonl
Step 7：保留 dpo_all_mixed_190.jsonl
Step 8：生成数据审计报告
Step 9：给出是否需要扩数据的判断
Step 10：准备 DPO-sanity 训练配置
```

---

# Step 1：重新生成 190 对版本 audit

## 1.1 当前问题

当前仓库中的 audit 文件需要确认是否已经对应最新 190 对。  
如果 `dpo_main_audit.json` 仍显示：

```text
total_pairs = 131
```

说明 audit 文件没有同步到最新 190 对。

## 1.2 必须重新生成

输入：

```text
data/dpo_main_pairs_expanded.jsonl
```

输出：

```text
data/dpo_main_audit.json
docs/dpo_main_audit.md
```

必须确认：

```text
total_pairs = 190
```

---

# Step 2：拆分 heldout leakage 字段

## 2.1 为什么要拆

不能只写：

```json
"heldout_leakage": 86
```

这个字段太粗糙。  
DPO 阶段必须区分：

```text
New50 是否污染？
New100 是否被用于 DPO 构造？
未来 DPO-independent eval 是否污染？
old28 是否污染？
train/val/test split 是否污染？
```

## 2.2 新 audit 字段

建议改成：

```json
{
  "total_pairs": 190,
  "new50_overlap": 0,
  "new100_overlap": 0,
  "new100_dpo_source_pairs": 86,
  "dpo_independent_eval_overlap": "not_created_yet",
  "old28_overlap": 0,
  "train_split_pairs": 0,
  "val_split_overlap": 0,
  "test_split_overlap": 0,
  "unknown_task_pairs": 0
}
```

注意：

```text
如果某些 pairs 是从 New100 failures 构造出来的，不要简单写成 leakage。
应写成 new100_dpo_source_pairs。
```

因为它的含义是：

```text
New100 被用作 DPO 数据来源，因此 DPO 后 New100 只能作为 reference eval，不能作为完全 clean 泛化评测。
```

---

# Step 3：重新分类 OTHER

## 3.1 当前问题

当前：

```text
OTHER = 29 pairs，占 15%
```

偏高。

OTHER 不利于训练和报告，因为它无法说明模型到底在学什么。

## 3.2 重新分类目标

尽量把 OTHER 重新归入：

```text
WRONG_PATCH
OVER_EDIT
UNDER_EDIT
MISREAD_TEST_OUTPUT
PREMATURE_SUBMIT
TOOL_VALID_BUT_BAD_ARGS
TEST_STILL_FAIL
PATCH_APPLY_ERROR
UNKNOWN
```

最终目标：

```text
OTHER <= 5%-8%
```

如果部分样本确实无法判断，保留为 UNKNOWN，但不要混在 OTHER 里。

## 3.3 输出报告

输出：

```text
docs/dpo_other_reclassification_report.md
data/dpo_other_reclassification.json
```

内容包括：

```text
原 OTHER 数量
重新分类后各类数量
保留 UNKNOWN 数量
人工/规则判断依据
```

---

# Step 4：控制 FORMAT_ERROR 占比

## 4.1 当前问题

当前：

```text
FORMAT_ERROR = 68 pairs，占 36%
```

这对 Patch-Correctness DPO 来说太高。

FORMAT_ERROR 有价值，但它主要训练：

```text
格式合法性
JSON/tool schema
action structure
```

而不是：

```text
patch correctness
test feedback correction
wrong patch correction
```

v2.1-clean 当前已经不是格式问题为主，因此 FORMAT_ERROR 不应该主导 DPO-main。

## 4.2 DPO-main 中的目标占比

在 `dpo_patch_main_balanced.jsonl` 中，FORMAT_ERROR 建议控制为：

```text
10%-15%
```

如果 DPO-main 是 150 对：

```text
FORMAT_ERROR 最多 15-22 对
```

## 4.3 哪些 FORMAT_ERROR 可以保留

优先保留这类 FORMAT_ERROR：

```text
chosen 是完整且正确的 edit/run_tests/submit 流程；
rejected 是格式错导致工具无法执行；
同 task 或同 bug_type 下 chosen/rejected 对比明确；
rejected 不只是 trivial parse error，而是影响修复流程。
```

删除或降权：

```text
纯 JSON 格式错误；
和 patch correctness 无关；
只有 rejected 错误，没有有效 chosen 修复逻辑；
过短或信息不足样本。
```

---

# Step 5：生成 DPO-sanity 数据集

## 5.1 文件

输出：

```text
data/dpo_sanity_pairs.jsonl
```

## 5.2 数量

```text
40-50 pairs
```

## 5.3 推荐组成

| 类型 | 数量 |
|---|---:|
| patch_correctness / TEST_STILL_FAIL | 20-25 |
| same-task 7B/mimo success vs v2.1 fail | 10-15 |
| NO_TEST_AFTER_EDIT | 5 |
| NO_EDIT | 5 |
| FORMAT_ERROR | 最多 5 |

## 5.4 用途

这不是正式 DPO 主训练集，只用于：

```text
验证 DPO 数据格式；
验证 DPO loss 是否正常下降；
验证 adapter 继续训练是否正常；
验证 JSON/tool 能力是否不崩；
验证 New50/New100 不出现灾难性退化。
```

---

# Step 6：生成 balanced Patch-Correctness DPO-main 数据集

## 6.1 文件

输出：

```text
data/dpo_patch_main_balanced.jsonl
```

## 6.2 数量

建议：

```text
120-160 pairs
```

如果重平衡后高质量 pair 足够，也可以接近：

```text
180-190 pairs
```

但不要为了数量硬塞低质量 FORMAT_ERROR / OTHER。

## 6.3 推荐组成

| Pair 类型 | 数量建议 | 占比 |
|---|---:|---:|
| TEST_STILL_FAIL / WRONG_PATCH | 45-60 | 主体 |
| patch correctness same-task | 30-40 | 核心高质量 |
| NO_TEST_AFTER_EDIT | 10-15 | 学会 edit 后测试 |
| NO_EDIT | 15-25 | 防止 NO_EDIT 反弹 |
| FORMAT_ERROR | 10-20 | 辅助，最多 15% |
| OTHER/UNKNOWN | 尽量少于 10 | 不应主导 |

## 6.4 目标

这版数据的目标是训练：

```text
正确 patch 优于错误 patch；
根据 test feedback 修正优于重复错误；
最小有效修改优于 over-edit；
edit 后 run_tests 优于不测试；
少量保持 read-to-edit 能力，防止 NO_EDIT 反弹。
```

---

# Step 7：保留 all-mixed-190 数据集

## 7.1 文件

输出：

```text
data/dpo_all_mixed_190.jsonl
```

这个文件就是原始 190 对全量集合，可以从：

```text
data/dpo_main_pairs_expanded.jsonl
```

复制或标准化得到。

## 7.2 用途

只用于：

```text
ablation；
备份；
后续比较 balanced vs all-mixed。
```

不建议第一轮直接用于正式 DPO-main。

---

# Step 8：生成最终数据审计报告

输出：

```text
docs/dpo_phase6_1_data_audit.md
data/dpo_phase6_1_data_audit.json
```

必须包括：

## 8.1 总体统计

```text
原始 pairs: 190
sanity pairs: 40-50
balanced main pairs: 120-160
all mixed pairs: 190
```

## 8.2 来源分布

按 source 统计：

```text
mimo same-task
patch correctness
v2.1-clean vs 3B Base
v2.1-clean vs v2
rejected errors vs success
```

## 8.3 failure type 分布

分别统计：

```text
原始 190
sanity set
balanced main set
```

## 8.4 bug type 分布

统计：

```text
覆盖 bug type 数量
top bug types
是否有单一 bug_type 占比过高
```

## 8.5 overlap / leakage

必须写清楚：

```text
New50 overlap
New100 as DPO source count
DPO-independent eval overlap
old28 overlap
train/val/test overlap
unknown task count
```

## 8.6 结论

明确写：

```text
当前是否可以进入 DPO-sanity；
是否可以进入 DPO-main；
是否需要继续扩充数据。
```

---

# Step 9：是否需要扩数据的判断标准

## 9.1 暂时不扩的条件

如果满足：

```text
balanced main >= 120 pairs；
FORMAT_ERROR <= 15%；
OTHER/UNKNOWN <= 8%；
TEST_STILL_FAIL / WRONG_PATCH / patch_correctness 占主体；
bug type 覆盖 >= 20；
chosen/rejected 格式正确；
```

则：

```text
不需要继续扩充数据，直接进入 DPO-sanity。
```

## 9.2 需要扩的条件

如果重平衡后出现：

```text
balanced main < 120 pairs；
TEST_STILL_FAIL / WRONG_PATCH pair 不足 40；
OTHER/UNKNOWN 仍高于 10%；
FORMAT_ERROR 无法压到 15% 以下；
bug type 覆盖明显不足；
```

则需要扩充。

扩充目标：

```text
先补到 150 pairs；
再补到 200 pairs；
最多先不要超过 300 pairs。
```

## 9.3 扩充方向

如果需要扩，只补：

```text
TEST_STILL_FAIL
WRONG_PATCH
test-feedback correction
same bug_type correction
NO_TEST_AFTER_EDIT
少量 NO_EDIT
```

不要继续补大量 FORMAT_ERROR。

---

# Step 10：DPO-sanity 训练配置准备

虽然本阶段主要是数据整理，但可以同时准备 sanity 训练配置。

## 10.1 训练输入

```text
data/dpo_sanity_pairs.jsonl
```

## 10.2 模型

```text
base_adapter: 3B v2.1-clean
```

## 10.3 参数

```yaml
method: DPO + LoRA continuation
learning_rate: 1e-6
epochs: 1
beta: 0.1
max_length: 4096
max_prompt_length: 3072
warmup_ratio: 0.03
```

## 10.4 禁止事项

```text
不要 get_peft_model 覆盖已有 adapter；
不要 init_lora_weights=true 重置 adapter；
不要直接使用 all-mixed-190 做第一轮训练；
不要在 audit 未更新前训练；
不要用 New100 训练来源再声称 New100 是 clean DPO eval。
```

---

# 11. 给开发 agent 的最终执行指令

请开发 agent 直接执行：

```text
1. 读取 data/dpo_main_pairs_expanded.jsonl，确认 total_pairs=190。
2. 重新生成 data/dpo_main_audit.json 和 docs/dpo_main_audit.md，确保 audit 对应 190 对。
3. 将 heldout_leakage 拆分为 new50_overlap、new100_dpo_source_pairs、dpo_independent_eval_overlap、old28_overlap、val/test overlap。
4. 对 29 个 OTHER 进行重新分类，尽量拆为 WRONG_PATCH、OVER_EDIT、UNDER_EDIT、MISREAD_TEST_OUTPUT、PREMATURE_SUBMIT、TOOL_VALID_BUT_BAD_ARGS、UNKNOWN。
5. 生成 data/dpo_sanity_pairs.jsonl，数量 40-50，对应 DPO-sanity。
6. 生成 data/dpo_patch_main_balanced.jsonl，数量 120-160，FORMAT_ERROR 控制在 10%-15%，OTHER/UNKNOWN 控制在 8% 以下。
7. 生成 data/dpo_all_mixed_190.jsonl，保留原始全集做 ablation。
8. 输出 docs/dpo_phase6_1_data_audit.md 和 data/dpo_phase6_1_data_audit.json。
9. 在报告中判断是否需要继续扩数据。如果 balanced main >=120 且分布合理，则不要扩，直接进入 DPO-sanity。
10. 准备 DPO-sanity 训练配置，但不要直接启动 DPO-main。
```

---

# 12. 最终判断

当前 190 对数据已经接近 Phase 6 DPO-main 的数量目标，但现阶段不应继续盲目扩充，也不应直接训练。

当前阶段最重要的是：

```text
把 190 对整理成真正适合 Patch-Correctness DPO 的高质量数据。
```

也就是：

```text
重审计
→ 重分类
→ 重平衡
→ sanity set
→ balanced main set
→ 再训练
```

如果这个阶段完成得好，后续 DPO 实验才有说服力。否则即使 DPO 后分数上涨，也可能说不清楚到底是 patch correctness 提升，还是 format correction / 数据污染 / benchmark 记忆。

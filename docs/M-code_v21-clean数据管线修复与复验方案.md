# M-code v2.1-clean 数据管线修复与复验方案

> 用途：给后续开发 agent 执行。  
> 当前问题：v2.1 在 new50 held-out 上达到 90%，且审计显示 new50 没有 task overlap，因此该结果可以作为高可信候选结果；但 read-to-edit 数据构造管线混入了 old28 test / val / unknown 任务，不能作为最终发布版。  
> 核心目标：修复 `build_read_to_edit_sft.py`，只使用 train split 构造 clean r2e 数据，重训 `v2.1-clean`，并在 new50 上复验结果是否稳定。

---

## 1. 当前审计结论

### 1.1 可以暂时保留的结论

当前 v2.1 在 new50 held-out 上的 90% 结果具备较高可信度，因为审计显示：

| 检查项 | 结果 | 判断 |
|---|---:|---|
| R2e tasks 与 held-out bugfix_201-250 重叠 | 0 | PASS |
| Original SFT tasks 与 held-out 重叠 | 0 | PASS |
| Rollouts 与 held-out 重叠 | 0 | PASS |
| Test task r2e samples 中答案泄漏 | 0 | PASS |

因此：

```text
v2.1 在 new50 held-out 上的 90% 不是因为直接训练过 bugfix_201-250。
```

可以暂时写为：

```text
v2.1 is a high-confidence candidate result on the new50 held-out split.
```

但注意：它还不是最终发布版结果。

---

### 1.2 发现的问题

审计发现当前 r2e 数据构造不规范：

| 问题 | 详情 | 影响 |
|---|---|---|
| R2e 与 old28 test split 重叠 | 27/28 个 test tasks，162 条样本 | old28 不再可作为 v2.1 对比评测 |
| R2e 混入 val split | 27 个 val tasks | val split 不干净 |
| R2e 含 unknown/unlabeled tasks | 17 个任务 | 数据来源不可控 |
| source provenance 缺失 | 无 `source_trace_path` / `source_run_id` / `in_train_split` | 后续审计困难 |
| 少量疑似 answer leakage | 7-13 条，约 0.6%-1.1% | 建议删除，避免报告争议 |

当前 r2e 数据来源分布：

```text
Train split: 803 samples, 68.8%
Test split: 162 samples, 13.9%
Other/unknown: 203 samples, 17.4%
```

这说明：

```text
build_read_to_edit_sft.py 当前是从 rollouts 里全局抽取 success traces，没有严格按 train/eval split 过滤。
```

---

## 2. 当前阶段定性

当前结果不能简单判定为失败，也不能直接当最终版。

推荐定性：

```text
v2 是当前完全可信的主基线结果：
new50 上 54%，相比 3B Base 的 42% 提升 12 个点。

v2.1 是高可信候选结果：
new50 上 90%，且与 bugfix_201-250 无 task overlap。

但 v2.1 当前训练数据混入 old28 test/val/unknown tasks，因此不能作为最终发布版。下一步必须重建 train-only read-to-edit 数据并重训 v2.1-clean。
```

---

## 3. 下一阶段目标

下一阶段名称建议：

```text
Phase 4: v2.1-clean Data Pipeline Repair and Re-evaluation
```

核心目标：

```text
1. 修复 r2e 数据构造管线；
2. 删除所有非 train split 样本；
3. 删除疑似 answer leakage 样本；
4. 添加数据溯源字段；
5. 重建 clean r2e 数据；
6. 从可信 v2 adapter 继续训练 v2.1-clean；
7. 在 new50 上复验 90% 是否稳定。
```

最终目标不是继续追分，而是让结果变成：

```text
clean
可复现
可审计
可写进报告
面试问不穿
```

---

# 4. 执行总路线

请后续 agent 按以下顺序执行：

```text
Step 1：修复 build_read_to_edit_sft.py 的 split filtering
Step 2：给 r2e 样本补充 provenance 字段
Step 3：删除疑似 answer leakage 样本
Step 4：重新生成 read_to_edit_step_sft_clean_train_only.jsonl
Step 5：生成 clean r2e audit report
Step 6：从 v2 adapter 继续训练 v2.1-clean
Step 7：在 new50 上评测 v2.1-clean
Step 8：根据 v2.1-clean 结果决定是否继续 DPO
```

---

# Step 1：修复 `build_read_to_edit_sft.py`

## 1.1 必须加入 split filtering

当前问题是 r2e 构造时从所有 success rollouts 中抽样，没有限制 train split。

必须修改为：

```python
train_tasks = load_task_ids("benchmark/splits/train_tasks.txt")
val_tasks = load_task_ids("benchmark/splits/val_tasks.txt")
test_tasks = load_task_ids("benchmark/splits/test_tasks.txt")
heldout_tasks = {f"bugfix_{i}" for i in range(201, 251)}

for trace_path in all_success_traces:
    task_id = extract_task_id(trace_path)

    if task_id not in train_tasks:
        continue

    if task_id in val_tasks:
        continue

    if task_id in test_tasks:
        continue

    if task_id in heldout_tasks:
        continue

    # only then extract read_file -> edit_file samples
```

更严格的写法：

```python
if task_id not in train_tasks:
    skipped_by_split[task_id] += 1
    continue
```

原则：

```text
只允许 train split；
禁止 val；
禁止 old28 test；
禁止 new50 held-out；
禁止 unknown/unlabeled。
```

---

## 1.2 不允许 unknown tasks 进入训练数据

如果某个 task_id 不在任何 split 文件中：

```text
不要默认当 train；
必须跳过。
```

因为当前已经发现有 17 个 unlabeled / unknown tasks 混入。

建议：

```python
if task_id not in train_tasks and task_id not in val_tasks and task_id not in test_tasks and task_id not in heldout_tasks:
    skipped_unknown.append(task_id)
    continue
```

---

## 1.3 输出 split filtering 统计

构造完成后必须输出：

```text
total_traces_seen
traces_used
skipped_not_train
skipped_val
skipped_test
skipped_heldout
skipped_unknown
samples_generated
```

输出文件：

```text
outputs/reports/read_to_edit_split_filter_stats.json
```

---

# Step 2：给每条 r2e 样本添加 provenance 字段

## 2.1 必须新增字段

每条样本至少包含：

```json
{
  "sample_id": "bugfix_123_r2e_0001",
  "task_id": "bugfix_123",
  "split": "train",
  "in_train_split": true,
  "source_trace_path": "outputs/rollouts/xxx/success/bugfix_123.trace.json",
  "source_run_id": "xxx",
  "source_model": "mimo-v2.5-pro",
  "transition_type": "read_to_edit",
  "history_step_idx": 3,
  "completion_action": "edit_file",
  "bug_type": "boundary_condition"
}
```

如果暂时拿不到 `source_model`，也要先写：

```json
"source_model": "unknown"
```

但 `source_trace_path`、`split`、`in_train_split` 必须有。

---

## 2.2 provenance 的目的

这样后续可以直接审计：

```text
这个样本来自哪个 trace？
哪个模型生成？
属于哪个 split？
是否来自 train？
是否可能污染 eval？
```

以后 DPO 数据也必须遵循这个规范。

---

# Step 3：删除疑似 answer leakage 样本

## 3.1 过滤规则

对每条 r2e 样本，检查：

```text
completion 中的 edit_file new_text 是否完整出现在 prompt/messages 中；
completion 中的 edit_file action 是否出现在 prompt/messages 中；
final_patch / diff 是否出现在 prompt/messages 中；
未来 edit_file action 是否出现在 history 中。
```

如果命中，则删除。

---

## 3.2 短代码片段的处理

审计中发现的 `end = start + chunk_size` 这类短片段可能只是 read_file observation 中原始代码恰好包含，不一定是真泄漏。

但为了简单和严谨：

```text
全部删除，不解释，不保留。
```

原因：

```text
清理成本低；
保留会让报告变复杂；
别人看到 answer leakage 会直接质疑结果。
```

---

## 3.3 输出泄漏过滤统计

输出：

```text
samples_before_leakage_filter
samples_removed_by_new_text
samples_removed_by_future_action
samples_removed_by_final_patch
samples_after_leakage_filter
```

输出文件：

```text
outputs/reports/read_to_edit_leakage_filter_stats.json
```

---

# Step 4：重新生成 clean r2e 数据

## 4.1 输出文件命名

不要覆盖旧数据。

新数据命名：

```text
outputs/data/read_to_edit_step_sft_clean_train_only.jsonl
```

旧数据保留：

```text
outputs/data/read_to_edit_step_sft.jsonl
```

旧数据可作为 dirty v2.1 的审计记录。

---

## 4.2 clean 数据验收标准

clean r2e 数据必须满足：

```text
所有样本 task_id in train_tasks
test split 样本数 = 0
val split 样本数 = 0
held-out bugfix_201-250 样本数 = 0
unknown split 样本数 = 0
answer leakage 样本数 = 0
source_trace_path 缺失数 = 0
in_train_split=false 样本数 = 0
completion action 全部为 edit_file
old_text/new_text 非空
```

---

# Step 5：生成 clean r2e 审计报告

生成：

```text
outputs/reports/read_to_edit_clean_audit.md
outputs/reports/read_to_edit_clean_audit.json
```

报告内容必须包括：

## 5.1 Split overlap

| 检查项 | 结果 | 状态 |
|---|---:|---|
| Train split samples | N | PASS |
| Test split samples | 0 | PASS |
| Val split samples | 0 | PASS |
| New50 held-out samples | 0 | PASS |
| Unknown samples | 0 | PASS |

## 5.2 Answer leakage

| 检查项 | 结果 | 状态 |
|---|---:|---|
| new_text in prompt/messages | 0 | PASS |
| future edit action in prompt/messages | 0 | PASS |
| final_patch/diff in prompt/messages | 0 | PASS |

## 5.3 Provenance completeness

| 字段 | 缺失数 | 状态 |
|---|---:|---|
| source_trace_path | 0 | PASS |
| source_run_id | 0 或记录 unknown | PASS/WARN |
| split | 0 | PASS |
| in_train_split | 0 | PASS |
| source_model | 0 或记录 unknown | PASS/WARN |

## 5.4 数据分布

统计：

```text
样本总数
task 数
每个 task 平均样本数
bug_type 分布
source_model 分布
old_text 平均长度
new_text 平均长度
```

---

# Step 6：重训 v2.1-clean

## 6.1 训练基座

必须从可信 v2 adapter 继续训练：

```text
base model + v2 adapter
```

不要从 base 重新训。

---

## 6.2 正确加载方式

继续训练必须用：

```python
base_model = AutoModelForCausalLM.from_pretrained(...)

base_model = prepare_model_for_kbit_training(base_model)

model = PeftModel.from_pretrained(
    base_model,
    v2_adapter_path,
    is_trainable=True,
)
```

禁止：

```python
get_peft_model(...)
LoraConfig(...)
init_lora_weights=True
```

如果训练 v2.1-clean 的脚本里出现这些，说明又变成重新初始化 LoRA，不是继续训练 v2。

---

## 6.3 训练前 sanity check

在训练前必须先 eval 一次：

```text
base + v2 adapter on new50
```

预期结果应接近：

```text
Success: 54%
JSON Parse: 96%
Tool Valid: 96%
```

如果加载后接近 3B Base：

```text
Success: 42%
JSON Parse: 56%
Tool Valid: 56%
```

说明 v2 adapter 没加载成功，禁止继续训练。

---

## 6.4 数据混合比例

如果 clean r2e 样本数仍有 700-900 条：

```text
70% original step_sft_v2_clean
30% read_to_edit_clean_train_only
```

如果 clean r2e 样本数明显减少，比如低于 500 条：

```text
80% original step_sft_v2_clean
20% read_to_edit_clean_train_only
```

原则：

```text
不要让 read-to-edit 数据比例过高；
避免模型过度 edit_file；
保留 v2 的 JSON/tool 能力。
```

---

## 6.5 训练参数建议

```yaml
base_checkpoint: 3B Step-SFT v2 adapter
method: LoRA continuation / QLoRA continuation
learning_rate: 1e-5 to 2e-5
epochs: 1
warmup_ratio: 0.03
max_seq_length: 4096
save_strategy: final
```

保存方式：

```python
trainer.model.save_pretrained(output_dir, safe_serialization=True)
tokenizer.save_pretrained(output_dir)
```

输出目录：

```text
models/3b_step_sft_v21_clean/
```

训练报告：

```text
outputs/reports/train_v21_clean_log.md
```

---

# Step 7：训练后 adapter 校验

训练完成后必须运行 adapter 校验脚本。

新增或复用：

```text
debug/verify_adapter_loading.py
```

校验：

```text
adapter_config.json 存在
adapter_model.safetensors 存在
lora_A/lora_B 权重存在
LoRA 权重 norm 非 0
active_adapter 正确
base+adapter 输出与 base 不同
is_trainable=True 时 trainable_lora > 0
```

输出：

```text
outputs/reports/v21_clean_adapter_verify.md
```

---

# Step 8：v2.1-clean 评测

## 8.1 主评测集

优先评测：

```text
New50 held-out = bugfix_201-250
```

因为 new50 是当前最干净的主评测集。

---

## 8.2 不要把 old28 作为主评测

由于 dirty v2.1 已经污染 old28，后续 old28 最多作为历史参考。

报告中写：

```text
Old28 was used in early-stage diagnostics and is no longer used as the primary evaluation split after leakage audit.
```

主结论基于：

```text
new50 held-out
future new100 held-out
unseen bug type held-out
```

---

## 8.3 评测模型

至少评测：

```text
3B Base
3B Step-SFT v2
3B Step-SFT v2.1-dirty
3B Step-SFT v2.1-clean
7B Base
```

其中 dirty v2.1 只作为参考，不作为最终结果。

---

## 8.4 评测指标

必须包含：

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
```

输出文件：

```text
outputs/reports/v21_clean_eval_new50.md
outputs/reports/v21_clean_eval_new50.json
```

---

# Step 9：结果解释规则

## 9.1 如果 v2.1-clean 仍然达到 80%-90%

结论：

```text
read-to-edit transition SFT 真实有效；
v2.1 clean 可以作为当前主结果；
下一步应扩展 harder held-out / unseen bug type，而不是急着 DPO。
```

下一步：

```text
扩展 new100 held-out；
做 unseen bug type；
做 metadata ablation；
做 exact patch match；
再考虑 DPO。
```

---

## 9.2 如果 v2.1-clean 回落到 65%-75%

结论：

```text
read-to-edit 仍然有效，但 dirty v2.1 的 90% 含有分布污染增益；
v2.1-clean 依然比 v2 的 54% 明显提升。
```

下一步：

```text
继续补 train-only r2e 数据；
做 NO_EDIT-specific DPO；
增加 high-quality teacher success traces。
```

---

## 9.3 如果 v2.1-clean 回落到 54%-60%

结论：

```text
dirty v2.1 的提升主要来自非 train split r2e 数据；
当前 train-only r2e 数据不足或质量不够；
需要重新设计 r2e 数据来源。
```

下一步：

```text
从 train tasks 重新跑 teacher rollouts；
增加 train-only success traces；
重新构造 r2e；
暂缓 DPO/GRPO。
```

---

# Step 10：暂缓 DPO / GRPO

在 v2.1-clean 结果出来之前，不要继续 DPO 或 GRPO。

原因：

```text
DPO 依赖 chosen/rejected 数据；
当前 r2e 已经暴露 split filtering 问题；
DPO 构造脚本也可能存在类似污染；
必须先修好数据管线。
```

等 v2.1-clean 出来后：

```text
如果 v2.1-clean >= 80%：
    优先扩展 harder eval，不急着 DPO。
如果 v2.1-clean = 65%-75%：
    可以做 NO_EDIT-specific DPO。
如果 v2.1-clean <= 60%：
    先补 teacher data，不做 DPO。
```

---

# 11. 最终报告建议写法

当前可以先写：

```text
The first v2.1 result achieved 90% success on the new50 held-out split, and leakage audit confirmed no task overlap between the read-to-edit training data and bugfix_201-250. However, the audit also found that the read-to-edit data construction pipeline included samples from the old28 test split and validation split. Although this does not affect the new50 result, it makes the current v2.1 data pipeline unsuitable for final reporting. We therefore rebuild a train-only read-to-edit dataset with explicit split filtering and provenance tracking, and retrain v2.1-clean for final evaluation.
```

中文：

```text
第一版 v2.1 在 new50 held-out 上达到 90%，审计确认 read-to-edit 训练数据与 bugfix_201-250 没有 task overlap，因此 new50 结果具备较高可信度。但审计也发现 read-to-edit 数据构造管线混入了 old28 test split 和 val split 样本。虽然这不影响 new50 结果，但说明当前 v2.1 数据管线不适合作为最终发布版。因此下一步将重建只包含 train split 的 read-to-edit 数据，并加入显式 split filtering 与 provenance tracking，重新训练 v2.1-clean 后再进行最终评测。
```

---

# 12. 给开发 agent 的最终执行指令

请后续开发 agent 直接执行：

```text
1. 修改 data_builder/build_read_to_edit_sft.py。
2. 只允许 task_id in train_tasks.txt 的 traces 进入 r2e 数据。
3. 显式排除 val_tasks、test_tasks、bugfix_201-250、unknown tasks。
4. 删除 completion new_text / future edit action / final_patch 出现在 prompt/messages 中的样本。
5. 每条样本添加 source_trace_path、source_run_id、split、in_train_split、source_model、transition_type。
6. 输出 outputs/data/read_to_edit_step_sft_clean_train_only.jsonl。
7. 输出 outputs/reports/read_to_edit_clean_audit.md 和 json，确认 test/val/heldout/unknown overlap 全为 0。
8. 用 PeftModel.from_pretrained(base_model, v2_adapter, is_trainable=True) 从 v2 继续训练 v2.1-clean。
9. 禁止 get_peft_model、禁止 LoraConfig、禁止 init_lora_weights=True。
10. 训练前先 eval base+v2 adapter，确认结果接近 v2 的 new50 54%。
11. 训练后运行 adapter 校验。
12. 在 new50 上评测 v2.1-clean。
13. 在 v2.1-clean 结果出来前，暂停 DPO / GRPO。
```

---

# 13. 最终判断

当前不是严重翻车，而是一次正常且必要的数据管线审计。

当前最稳判断：

```text
new50 的 90% v2.1 是高可信候选结果；
但当前 r2e 数据构造管线污染 old28/val，不适合作为最终版；
必须重建 train-only r2e 并重训 v2.1-clean。
```

这个阶段完成后，项目会形成更强的闭环：

```text
trajectory-level SFT 失败
→ step-level SFT v2 可信提升
→ failure analysis 定位 NO_EDIT
→ read-to-edit v2.1 大幅提升
→ leakage audit 发现 r2e 管线污染
→ train-only v2.1-clean 复验
```

这条线非常适合写进项目报告和面试说明，因为它体现的是：

```text
不是盲目刷分；
而是能发现异常、审计泄漏、修复数据管线、重新验证结果。
```

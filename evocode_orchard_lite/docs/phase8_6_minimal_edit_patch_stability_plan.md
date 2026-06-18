# Phase 8.6：Minimal-Edit / Patch-Stability Alignment 计划

> 前置结果：7B Workflow Alignment + Repair 在 Independent50 上达到 46%，首次超过 3B v2.1-clean + Repair 的 44%。  
> 当前瓶颈：7B 已经学会 `edit -> test` 工作流，但失败任务中出现过度编辑和 patch apply instability。

---

## 1. 问题定义

Phase 8.5 的动作层统计显示：

```text
3B 首轮失败样本：
平均 edit 1.13 次
平均 test 1.33 次

7B workflow 首轮失败样本：
平均 edit 7.57 次
平均 test 4.70 次
```

结论：

```text
7B 当前不是不编辑，而是过度编辑。
Workflow Alignment 修复了“不测试”，但没有修复“反复盲改”和 patch 不稳定。
```

Phase 8.6 目标：

```text
让 7B 保留 workflow discipline，同时学习 minimal edit / patch stability。
```

---

## 2. 本阶段新增内容

### 2.1 Runtime：Edit Budget Guard

`AgentLoop` 新增可选参数：

```python
max_successful_edits: int | None = None
max_total_edit_attempts: int | None = None
```

默认关闭，不影响已有实验。

作用：

```text
限制 7B 在失败任务中连续 edit_file 的次数，
防止 edit-test-edit-test 循环失控。
```

评测脚本 `eval_7b_workflow_alignment.py` 新增参数：

```bash
--max_successful_edits 2
--max_total_edit_attempts 4
```

### 2.2 Data：Minimal-Edit Alignment 数据

新增脚本：

```text
evocode_orchard_lite/data_builder/build_7b_minimal_edit_alignment.py
```

默认输出：

```text
outputs/data/7b_minimal_edit_alignment.jsonl
outputs/data/7b_minimal_edit_alignment.stats.json
```

数据来源：

```text
outputs/data/high_quality_success_traces.jsonl
outputs/rollouts/*/success/*/*.trace.json
```

过滤规则：

```text
只使用 bugfix_001-200 训练任务
trace 必须成功
总步数 <= 5
edit_file 次数 <= 2
必须包含 edit_file、run_tests、submit_patch
edit 后必须 run_tests
```

这样避免把 Independent50 任务拿来训练。

### 2.3 Training：继续训练 7B Workflow Adapter

`train_7b_workflow_alignment.py` 已支持：

```bash
--adapter_path outputs/models/7b_workflow_alignment
```

也就是从已训练好的 workflow adapter 继续训练 minimal-edit 数据，而不是从 7B base 重新训。

---

## 3. 推荐执行顺序

### Step 1：先跑 Edit Budget Guard 消融

不训练，直接评测 runtime guard 是否能减少 7B 过度编辑。

#### 方案 A：成功 edit 最多 2 次

```bash
cd /mnt/disk/mxf/projects/monesy/mini-swe-agent-main

PYTHONPATH=. python -B evocode_orchard_lite/eval/eval_7b_workflow_alignment.py \
  --adapter_path outputs/models/7b_workflow_alignment \
  --output_dir outputs/reports/eval_7b_workflow_alignment_edit_budget_s2 \
  --max_successful_edits 2 \
  2>&1 | tee outputs/reports/eval_7b_workflow_alignment_edit_budget_s2.log
```

#### 方案 B：总 edit 尝试最多 4 次

```bash
PYTHONPATH=. python -B evocode_orchard_lite/eval/eval_7b_workflow_alignment.py \
  --adapter_path outputs/models/7b_workflow_alignment \
  --output_dir outputs/reports/eval_7b_workflow_alignment_edit_budget_t4 \
  --max_total_edit_attempts 4 \
  2>&1 | tee outputs/reports/eval_7b_workflow_alignment_edit_budget_t4.log
```

#### 方案 C：两者同时启用

```bash
PYTHONPATH=. python -B evocode_orchard_lite/eval/eval_7b_workflow_alignment.py \
  --adapter_path outputs/models/7b_workflow_alignment \
  --output_dir outputs/reports/eval_7b_workflow_alignment_edit_budget_s2_t4 \
  --max_successful_edits 2 \
  --max_total_edit_attempts 4 \
  2>&1 | tee outputs/reports/eval_7b_workflow_alignment_edit_budget_s2_t4.log
```

观察指标：

```text
final_success 是否超过 46%
EDIT_BUDGET_EXCEEDED 是否过多
PATCH_APPLY_ERROR / OTHER 是否下降
TEST_STILL_FAIL 是否上升
```

如果 edit budget 提升或持平但步数明显下降，说明 runtime guard 值得保留。

---

### Step 2：构建 minimal-edit 数据

```bash
PYTHONPATH=. python -B evocode_orchard_lite/data_builder/build_7b_minimal_edit_alignment.py

cat outputs/data/7b_minimal_edit_alignment.stats.json
```

---

### Step 3：从 workflow adapter 继续训练 minimal-edit adapter

建议使用更低学习率：

```bash
PYTHONPATH=. python -B evocode_orchard_lite/training/train_7b_workflow_alignment.py \
  --adapter_path outputs/models/7b_workflow_alignment \
  --data outputs/data/7b_minimal_edit_alignment.jsonl \
  --output_dir outputs/models/7b_minimal_edit_alignment \
  --lr 3e-6 \
  --epochs 1 \
  --max_length 2048 \
  2>&1 | tee outputs/models/7b_minimal_edit_alignment_train.log
```

---

### Step 4：评测 minimal-edit adapter

先不加 edit budget：

```bash
PYTHONPATH=. python -B evocode_orchard_lite/eval/eval_7b_workflow_alignment.py \
  --adapter_path outputs/models/7b_minimal_edit_alignment \
  --output_dir outputs/reports/eval_7b_minimal_edit_alignment_independent50 \
  2>&1 | tee outputs/reports/eval_7b_minimal_edit_alignment_independent50.log
```

再加 edit budget 最优方案，例如：

```bash
PYTHONPATH=. python -B evocode_orchard_lite/eval/eval_7b_workflow_alignment.py \
  --adapter_path outputs/models/7b_minimal_edit_alignment \
  --output_dir outputs/reports/eval_7b_minimal_edit_alignment_budget_s2_t4 \
  --max_successful_edits 2 \
  --max_total_edit_attempts 4 \
  2>&1 | tee outputs/reports/eval_7b_minimal_edit_alignment_budget_s2_t4.log
```

---

## 4. 成功标准

最低成功：

```text
final_success >= 46%
平均 edit 次数下降
PATCH_APPLY_ERROR / OTHER 不上升
```

理想成功：

```text
final_success >= 48%
7B-only success 不减少
3B-only success 中追回 2 个以上
```

如果 minimal-edit adapter 降低成功率：

```text
说明当前数据过度压制 7B 的探索性编辑能力；
应保留 workflow adapter，并只使用 edit budget guard 或 apply_patch 工具改造。
```

---

## 5. 后续方向

如果 Phase 8.6 仍卡在 46% 左右，下一步优先不是继续 SFT，而是：

```text
Phase 8.7: apply_patch tool
```

原因：

```text
7B 更适合生成 unified diff 或函数级 patch，
当前 edit_file(old/new) 对大范围修改不友好，容易造成 PATCH_APPLY_ERROR。
```


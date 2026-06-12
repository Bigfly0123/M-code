# M-code：DPO 数据来源混乱问题说明与 Teacher Rollout 补齐规划

> 用途：交给开发 agent 执行。  
> 当前任务：**只说明并处理 DPO 数据来源问题**，暂不训练、不评测、不做 GRPO。  
> 核心问题：当前项目任务数量已经很多，但 DPO pairs 仍然少，尤其 WRONG_PATCH / TEST_FEEDBACK / PATCH_APPLY_STABILITY 类型不足。根因不是任务不够，而是后续新任务大多没有 teacher/mimo 成功轨迹，无法直接构造高质量 chosen/rejected preference pairs。

---

## 1. 当前问题一句话说明

现在不是“任务太少”，而是：

```text
有任务，但没有足够的 teacher success trajectory；
有失败结果，但没有和成功轨迹配成高质量 DPO pairs；
clean eval 任务不能被拿来训练；
所以 DPO 数据仍然少。
```

DPO 需要的是：

```text
chosen = 成功、可执行、patch 正确的轨迹
rejected = 失败、有训练价值的错误轨迹
```

不是只要有 task，就能自动生成 DPO pair。

---

## 2. 最初 DPO 数据是怎么来的

### 2.1 早期数据来源

最初的 DPO 数据主要来自前面约 200 个任务。

当时做过：

```text
mimo v2.5 pro rollout
不同 temperature rollout
成功轨迹 / 失败轨迹收集
基于成功与失败轨迹构造 DPO pairs
```

也就是说，早期 DPO 数据不是直接从 task 文件生成的，而是来自：

```text
teacher rollout pool
```

大致形式是：

```text
同一个任务上：
chosen = mimo v2.5 pro / teacher 成功轨迹
rejected = mimo 失败轨迹 / 其他模型失败轨迹 / 其他温度失败轨迹
```

或者：

```text
chosen = 成功 patch + run_tests pass + submit
rejected = 错误 patch / test fail / patch apply error / no edit
```

这批数据之所以能做 DPO，是因为同时具备：

```text
成功轨迹
失败轨迹
同任务或同类任务对齐关系
```

---

### 2.2 多温度 rollout 的价值

早期用不同 temperature 跑 mimo v2.5 pro 是有价值的，因为同一个任务可能产生：

```text
低温成功轨迹
高温错误 patch
高温格式错误
中温 partial fix
```

这样一个任务就可能产生多个 DPO pairs：

```text
success vs wrong_patch
success vs test_still_fail
success vs patch_apply_error
success vs no_test_after_edit
```

这就是为什么早期前 200 个任务能构造出一批 DPO 数据。

---

## 3. 后续新任务为什么没有自然变成 DPO 数据

后续为了 SFT、held-out、泛化验证、DPO-independent eval，又构建了很多新任务：

```text
New50: bugfix_201-250
New100: bugfix_251-350
reference/contaminated eval: bugfix_351-400
clean independent eval: bugfix_401-450
```

这些任务大多只有：

```text
task definition
workspace
tests
模型评测结果
失败类型统计
```

但不一定有：

```text
mimo v2.5 pro 成功轨迹
7B 成功轨迹
teacher 成功轨迹
多温度成功/失败轨迹池
可 replay 的 chosen trajectory
```

所以它们虽然是任务，但还不是 DPO 数据。

没有成功 chosen，就不能构造高质量 DPO pair。

---

## 4. 当前任务角色重新整理

| 任务范围 | 当前角色 | 可否用于 DPO pair | 是否应补 teacher/mimo | 是否可作为 clean eval |
|---|---|---:|---:|---:|
| 早期约 bugfix_001-200 | train / early rollout pool | 可以 | 已部分跑过 mimo，多温度 | 否 |
| New50 bugfix_201-250 | easy reference eval | 不建议继续用于训练 | 不优先 | 只作 reference |
| New100 bugfix_251-350 | hard reference / DPO source | 可以 | 可以补 | 否，只能 reference |
| bugfix_351-400 | contaminated/reference eval | 可以 | 可以补 | 否 |
| bugfix_401-450 | clean DPO-independent eval | 绝对不能用 | 不允许用于训练 | 是 |

---

## 5. 关键边界：401-450 不能碰

`bugfix_401-450` 的唯一作用是：

```text
clean DPO-independent eval
```

因此它不能用于：

```text
DPO pair 构造
teacher/mimo chosen 生成
失败轨迹 rejected 生成
same-task pair
same bug_type pair
SFT/r2e 数据
训练数据审计之外的任何训练用途
```

否则它也会被污染，后续又必须继续构建：

```text
bugfix_451-500
```

这会造成无限循环。

所以从现在开始必须固定：

```text
bugfix_401-450 只评测，不训练，不造 pair，不跑 teacher 用于训练。
```

---

## 6. 当前 DPO 数据少的根因

### 6.1 根因一：后续新任务缺少 teacher success trajectory

大量后续任务只有任务和评测结果，没有：

```text
mimo v2.5 pro success rollout
7B success rollout
teacher success trajectory
```

没有 chosen，就无法构造 DPO pair。

---

### 6.2 根因二：失败轨迹不一定有训练价值

不是所有失败都适合做 rejected。

低价值失败包括：

```text
纯 FORMAT_ERROR
完全无效 JSON
无意义输出
没有 read_file
没有 edit_file
工具参数缺失
```

高价值失败包括：

```text
TEST_STILL_FAIL
WRONG_PATCH
PATCH_APPLY_ERROR
TEST_FEEDBACK_IGNORED
UNDER_EDIT
OVER_EDIT
NO_TEST_AFTER_EDIT
```

Phase 6 需要重点补的是 patch correctness 类失败，而不是继续补 format correction。

---

### 6.3 根因三：chosen/rejected 没有成对保存

DPO 不是收集成功轨迹或失败轨迹就够。

它需要明确配对：

```text
same-task pair 最好
same bug_type pair 次之
same failure_type pair 再次
```

如果只有零散 rollouts，还需要做：

```text
DPO pair mining
```

---

### 6.4 根因四：clean eval 不能用于训练

一些任务虽然失败多、很适合造 DPO，但如果它们被定义为 clean eval，就不能动。

例如：

```text
bugfix_401-450
```

即使 v2.1-clean 在这些任务上失败很多，也不能拿它们来构造 DPO pairs。

---

## 7. 当前正确的数据边界

### 7.1 DPO source pool

允许用于 DPO pair mining：

```text
早期 train split
前约 200 个已跑 mimo/多温度的任务
New100 reference: bugfix_251-350
bugfix_351-400 reference / contaminated eval
已有 teacher/mimo/7B 成功轨迹的任务
已有 base/v2/v2.1-clean/DPO-main/DPO-main-v2 失败轨迹的任务
```

### 7.2 Clean eval pool

禁止用于训练，只用于评测：

```text
bugfix_401-450
```

### 7.3 不再盲目造新任务

当前优先级不是继续造任务，而是：

```text
对可用 source pool 补 teacher rollouts 和 pair mining。
```

---

# 8. 下一步专项任务：Teacher Rollout 补齐 + DPO Pair Mining

本阶段只做数据，不训练。

核心目标：

```text
1. 盘点哪些任务已有 teacher/mimo success trajectory；
2. 对允许的 source pool 补 mimo v2.5 pro / teacher rollouts；
3. 收集 model failure trajectories；
4. 建立 success/failure trajectory pool；
5. 从 trajectory pool 中挖高质量 DPO pairs；
6. 审计确认 bugfix_401-450 overlap = 0。
```

---

## Step 1：盘点已有 teacher/mimo rollout 覆盖

### 目标

弄清楚哪些任务已经有 mimo / teacher 成功轨迹，哪些没有。

### 输入路径

检查以下可能路径，按项目实际命名调整：

```text
outputs/rollouts/
outputs/teacher_traces/
outputs/mimo_rollouts/
data/dpo_pairs*.jsonl
data/dpo_main_pairs*.jsonl
data/dpo_patch_correctness*.jsonl
```

### 输出

```text
data/teacher_rollout_coverage.json
docs/teacher_rollout_coverage_report.md
```

### 每个 task 记录字段

```json
{
  "task_id": "bugfix_123",
  "split_role": "train|new100_reference|351_400_reference|clean_eval",
  "has_mimo_v25_rollout": true,
  "has_mimo_success": true,
  "has_7b_success": false,
  "has_teacher_success": true,
  "has_base_failure": true,
  "has_v21_clean_failure": false,
  "has_dpo_main_failure": true,
  "usable_for_dpo": true,
  "reason": "has teacher success and model failure"
}
```

### 报告必须包含

```text
总任务数
有 teacher/mimo 成功轨迹的任务数
只有失败没有成功 chosen 的任务数
可以直接构造 DPO pair 的任务数
需要补 teacher rollout 的任务数
禁止使用的 clean eval 任务数
```

---

## Step 2：确定允许补 teacher 的任务范围

### 允许补 teacher 的任务

只允许对以下任务跑 mimo v2.5 pro / teacher：

```text
train split
bugfix_251-350 New100 reference
bugfix_351-400 reference
早期未覆盖但不属于 clean eval 的任务
```

### 禁止补 teacher 的任务

禁止对以下任务生成训练用途 teacher 轨迹：

```text
bugfix_401-450
```

如果为了单纯评估 teacher 上限而跑，也必须另存为：

```text
teacher_eval_only
```

并且绝不能进入 DPO 数据。当前不建议这样做，避免混乱。

---

## Step 3：补跑 teacher / mimo v2.5 pro rollouts

### 目标

对 DPO source pool 中缺少 chosen 的任务补成功轨迹。

### 推荐采样策略

对每个允许任务：

```text
mimo v2.5 pro
temperature: 0.2, 0.5, 0.8
每个温度 1-2 条
最多 3-6 条 rollout
```

如果成本高，可先只跑：

```text
temperature 0.2 和 0.5
每个任务 1 条
```

### 保存路径

```text
outputs/teacher_traces/dpo_v3_raw/
outputs/teacher_traces/dpo_v3_success_only/
outputs/teacher_traces/dpo_v3_failed/
```

### chosen 过滤标准

只有满足以下条件的 teacher rollout 可以作为 chosen：

```text
patch_apply = true
run_tests = pass
submit = success
action schema valid
tool valid
可 replay 或至少可审计
```

失败 teacher rollout 不作为 chosen，但可以作为分析材料。

---

## Step 4：收集 rejected 失败轨迹

### 来源模型

从以下模型/阶段收集失败轨迹：

```text
3B Base
SFT v2
v2.1-clean
DPO-sanity
DPO-main
DPO-main-v2
```

### 优先保留的 rejected 类型

```text
TEST_STILL_FAIL
WRONG_PATCH
PATCH_APPLY_ERROR
TEST_FEEDBACK_IGNORED
UNDER_EDIT
OVER_EDIT
NO_TEST_AFTER_EDIT
```

### 降权或少量保留

```text
NO_EDIT
FORMAT_ERROR
TOOL_INVALID
```

这些不是当前主目标，不能主导 DPO 数据。

---

## Step 5：构建 success/failure trajectory pool

输出：

```text
data/trajectory_pool_dpo_v3.json
docs/trajectory_pool_dpo_v3_report.md
```

每个任务应聚合：

```json
{
  "task_id": "bugfix_281",
  "split_role": "new100_reference",
  "bug_type": "regex_parsing",
  "success_traces": [
    {
      "source": "mimo_v25",
      "temperature": 0.2,
      "trace_path": "...",
      "patch_apply": true,
      "tests_pass": true
    }
  ],
  "failure_traces": [
    {
      "source": "v21_clean",
      "failure_type": "TEST_STILL_FAIL",
      "trace_path": "...",
      "patch_apply": true,
      "tests_pass": false
    }
  ],
  "can_make_same_task_pair": true,
  "recommended_pair_types": ["wrong_patch", "test_feedback_correction"]
}
```

---

# 9. DPO Pair Mining 规则

## 9.1 Pair 优先级

### Priority 1：same-task teacher success vs model failure

最强数据：

```text
chosen = mimo/teacher/7B success
rejected = v2.1-clean/DPO-main/base failure
same task
```

优先构造：

```text
wrong_patch
test_still_fail
patch_apply_stability
test_feedback_correction
```

---

### Priority 2：same-task v2.1-clean success vs DPO regression

用于防止 DPO 改坏原能力：

```text
chosen = v2.1-clean success
rejected = DPO-main/DPO-main-v2 failure
same task
```

pair_type：

```text
preserve_success
anti_regression
```

---

### Priority 3：same bug_type success vs failure

如果没有 same-task chosen，可用同 bug_type pair：

```text
chosen = 同 bug_type 成功轨迹
rejected = 同 bug_type 失败轨迹
```

这类 pair 稍弱，但可用于扩充。

---

### Priority 4：test-feedback correction pair

chosen：

```text
edit_file
→ run_tests fail
→ 根据 test output 修正
→ run_tests pass
→ submit
```

rejected：

```text
edit_file
→ run_tests fail
→ 忽略测试输出 / 重复错误 / 直接 submit
```

---

## 9.2 每个任务最多生成多少 pair

避免一个任务过度占比。

建议：

```text
每个 task 最多 3-5 pairs
same-task pair 优先
same bug_type pair 少量补充
```

---

## 9.3 DPO-main-v3 目标数据量

建议目标：

```text
220-300 pairs
```

推荐组成：

| Pair 类型 | 数量目标 |
|---|---:|
| WRONG_PATCH / TEST_STILL_FAIL | 90-120 |
| TEST_FEEDBACK_CORRECTION | 35-50 |
| PATCH_APPLY_STABILITY | 35-50 |
| MINIMAL_PATCH / OVER_EDIT | 15-25 |
| PRESERVE_SUCCESS / anti-regression | 10-20 |
| residual NO_EDIT | 5-10 |
| FORMAT_ERROR | <=10 |

---

# 10. 输出文件

本阶段最终输出：

```text
data/teacher_rollout_coverage.json
docs/teacher_rollout_coverage_report.md

outputs/teacher_traces/dpo_v3_raw/
outputs/teacher_traces/dpo_v3_success_only/
outputs/teacher_traces/dpo_v3_failed/

data/trajectory_pool_dpo_v3.json
docs/trajectory_pool_dpo_v3_report.md

data/dpo_patch_correctness_v3_pairs.jsonl
data/dpo_patch_correctness_v3_audit.json
docs/dpo_patch_correctness_v3_audit.md
```

---

# 11. DPO 数据审计要求

`dpo_patch_correctness_v3_audit.json` 必须包含：

```text
total_pairs
pair_type_distribution
failure_type_distribution
bug_type_distribution
task_source_distribution
chosen_source_distribution
rejected_source_distribution
mimo_temperature_distribution
chosen_success_rate
rejected_success_rate
chosen_patch_apply_rate
rejected_patch_apply_rate
format_parse_rate
tool_valid_rate
bugfix_401_450_overlap
new50_overlap
new100_source_count
bugfix_351_400_source_count
old28_overlap
unknown_task_count
```

硬性要求：

```text
bugfix_401_450_overlap = 0
chosen_success_rate >= 95%
chosen_patch_apply_rate >= 95%
format_parse_rate >= 95%
WRONG_PATCH + TEST_STILL_FAIL >= 90
TEST_FEEDBACK_CORRECTION >= 35
PATCH_APPLY_STABILITY >= 35
FORMAT_ERROR <= 10
UNKNOWN pair_type <= 5%
```

---

# 12. 禁止事项

本阶段禁止：

```text
1. 使用 bugfix_401-450 构造任何 DPO pair；
2. 对 bugfix_401-450 跑 mimo 后保存为训练 teacher trace；
3. 把 bugfix_401-450 的失败用于 rejected；
4. 继续把 bugfix_351-400 称为 clean independent eval；
5. 用只有失败没有 chosen 的任务硬造 DPO；
6. 用纯 FORMAT_ERROR 凑数量；
7. 没有 audit 就训练；
8. 继续新增更多 clean eval 任务来掩盖数据边界问题。
```

---

# 13. 给开发 agent 的最终执行指令

请开发 agent 按以下流程执行：

```text
1. 先盘点所有已有任务的 teacher/mimo/7B rollout 覆盖情况。
2. 输出 teacher_rollout_coverage_report，说明哪些任务已有成功 chosen，哪些任务缺 teacher。
3. 明确 DPO source pool：train split、bugfix_251-350、bugfix_351-400、早期已跑 mimo 的任务。
4. 明确 clean eval pool：bugfix_401-450，禁止用于任何训练和 teacher trace。
5. 对 DPO source pool 中缺少成功 chosen 的任务补跑 mimo v2.5 pro / teacher rollouts。
6. 只保留 patch_apply=true、run_tests pass、submit success 的 teacher 轨迹作为 chosen。
7. 收集 base/v2/v2.1-clean/DPO-main/DPO-main-v2 的失败轨迹作为 rejected。
8. 构建 trajectory_pool_dpo_v3.json。
9. 按 same-task 优先、same bug_type 辅助的原则挖 DPO pairs。
10. 重点补 WRONG_PATCH、TEST_FEEDBACK_CORRECTION、PATCH_APPLY_STABILITY。
11. 生成 dpo_patch_correctness_v3_pairs.jsonl，目标 220-300 pairs。
12. 生成完整 audit，必须确认 bugfix_401_450_overlap=0。
13. 本阶段只构建数据，不训练。
```

---

# 14. 最终结论

现在 DPO 数据少，不是因为任务少，而是因为：

```text
后续新任务没有 teacher/mimo 成功轨迹；
失败轨迹没有和成功轨迹成对；
clean eval 不能用于训练；
真正高质量 WRONG_PATCH / TEST_FEEDBACK / PATCH_STABILITY pair 需要从 rollout pool 中挖。
```

因此下一步不是继续盲目造任务，而是：

```text
补 teacher rollouts
→ 建 trajectory pool
→ 挖 DPO pairs
→ 审计数据边界
```

这一步做好后，再训练 DPO-main-v3，结果才有可信度。
